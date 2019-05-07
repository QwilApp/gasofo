from example.domains.coffee_orders.orders_service import Orders
from example.shared.datatypes import (
    OrderDetails,
    OrderSummary, OrderItem
)
from example.shared.exceptions import InvalidAction
from gasofo.testing import GasofoTestCase


class OrdersServiceOpenForOrdersTest(GasofoTestCase):

    SERVICE_CLASS = Orders

    def test_new_order_created_and_summary_returned(self):
        def mock_create_order(room, buyer):
            return OrderSummary(order_id='id999', buyer=buyer, room=room)

        self.GIVEN(needs_port='db_create_order', has_side_effect=mock_create_order)
        self.GIVEN(needs_port='db_get_active_order', returns=None)  # no active orders

        self.WHEN(port_called='open_for_orders', requester='Nicolas', room='Le trou des chouettes')

        self.THEN(expected_output=OrderSummary(order_id='id999', buyer='Nicolas', room='Le trou des chouettes'))

    def test_raises_if_is_already_an_open_order_for_room(self):
        active_order_for_room = OrderSummary(order_id='id001', buyer='Nicolas', room='Le trou des chouettes')
        self.GIVEN(needs_port='db_get_active_order', returns=active_order_for_room)

        with self.assertRaisesRegexp(InvalidAction, 'There is already an offer to by coffee by Nicolas'):
            self.WHEN(port_called='open_for_orders', requester='Shawn', room='Le trou des chouettes')

    def test_raises_if_is_already_an_open_order_for_room_by_same_buyer(self):
        active_order_for_room = OrderSummary(order_id='id001', buyer='Nicolas', room='Le trou des chouettes')
        self.GIVEN(needs_port='db_get_active_order', returns=active_order_for_room)

        with self.assertRaisesRegexp(InvalidAction, 'You already have an open offer to buy coffee'):
            self.WHEN(port_called='open_for_orders', requester='Nicolas', room='Le trou des chouettes')


class OrdersServiceCloseOrdersTest(GasofoTestCase):

    SERVICE_CLASS = Orders

    def test_order_is_closed_and_archived(self):
        order_details = OrderDetails(
            order_id='id001',
            buyer='Nicolas',
            room='Le trou des chouettes',
            orders=[],
            open_ts=100001,
            close_ts=100005,
        )
        active_order_for_room = OrderSummary(order_id='id001', buyer='Nicolas', room='Le trou des chouettes')

        self.GIVEN(needs_port='db_get_active_order', returns=active_order_for_room)  # there is an active order
        self.GIVEN(needs_port='db_close_order', returns=order_details)  # when called returns details of closed order
        self.GIVEN(needs_port='archive_order')  # this port can be called

        self.WHEN(port_called='close_orders', requester='Nicolas', room='Le trou des chouettes')

        self.THEN(expected_output=order_details)

        self.assert_ports_called(calls=[
            GasofoTestCase.PortCalled(port='db_get_active_order', kwargs={'room': 'Le trou des chouettes'}),
            GasofoTestCase.PortCalled(port='db_close_order', kwargs={'room': 'Le trou des chouettes'}),
            GasofoTestCase.PortCalled(port='archive_order', kwargs={'order_details': order_details}),
        ])

    def test_raises_if_no_active_order(self):
        self.GIVEN(needs_port='db_get_active_order', returns=None)  # no active orders

        with self.assertRaisesRegexp(InvalidAction, 'There are no open offers in this room'):
            self.WHEN(port_called='close_orders', requester='Nicolas', room='Le trou des chouettes')

    def test_raises_if_requester_attempts_to_closes_someone_elses_order(self):
        active_order_for_room = OrderSummary(order_id='id001', buyer='Nicolas', room='Le trou des chouettes')
        self.GIVEN(needs_port='db_get_active_order', returns=active_order_for_room)  # there is an active order

        with self.assertRaisesRegexp(InvalidAction, "You cannot close someone else's order"):
            self.WHEN(port_called='close_orders', requester='Shawn', room='Le trou des chouettes')


class OrderServicesMakeOrderTest(GasofoTestCase):

    SERVICE_CLASS = Orders

    def test_making_an_order(self):
        active_order_for_room = OrderSummary(order_id='id001', buyer='Nicolas', room='Le trou des chouettes')
        self.GIVEN(needs_port='db_get_active_order', returns=active_order_for_room)  # there is an open order
        self.GIVEN(needs_port='is_valid_menu_item', returns=True)  # item is valid
        self.GIVEN(needs_port='db_add_order_item',
                   has_side_effect=lambda room, item, recipient: OrderItem(item=item, recipient=recipient, order_ts=10))

        self.WHEN(port_called='make_order', requester='Shawn', room='Le trou des chouettes', order_item='Flat White')

        self.THEN(expected_output=OrderItem(item='Flat White', recipient='Shawn', order_ts=10))

        self.assert_ports_called(calls=[
            GasofoTestCase.PortCalled(port='db_get_active_order', kwargs={'room': 'Le trou des chouettes'}),
            GasofoTestCase.PortCalled(port='is_valid_menu_item', kwargs={'item_name': 'Flat White'}),
            GasofoTestCase.PortCalled(port='db_add_order_item', kwargs={
                'room': 'Le trou des chouettes',
                'item': 'Flat White',
                'recipient': 'Shawn',
            }),
        ])

    def test_raises_if_no_open_orders_in_room(self):
        self.GIVEN(needs_port='db_get_active_order', returns=None)  # no open orders

        with self.assertRaisesRegexp(InvalidAction, 'There are no open offers in this room'):
            self.WHEN(port_called='make_order', requester='Shawn', room='Le trou des chouettes', order_item='Latte')

    def test_raises_if_ordered_item_is_not_on_the_menu(self):
        active_order_for_room = OrderSummary(order_id='id001', buyer='Nicolas', room='Le trou des chouettes')
        self.GIVEN(needs_port='db_get_active_order', returns=active_order_for_room)  # there is an open order
        self.GIVEN(needs_port='is_valid_menu_item', returns=False)  # requested item is not valid

        with self.assertRaisesRegexp(InvalidAction, 'Latte is not a valid menu item'):
            self.WHEN(port_called='make_order', requester='Shawn', room='Le trou des chouettes', order_item='Latte')

        self.assert_ports_called(calls=[
            GasofoTestCase.PortCalled(port='db_get_active_order', kwargs={'room': 'Le trou des chouettes'}),
            GasofoTestCase.PortCalled(port='is_valid_menu_item', kwargs={'item_name': 'Latte'}),
        ])


class OrderServicesShowOrdersTest(GasofoTestCase):

    SERVICE_CLASS = Orders

    def test_order_details_returned(self):
        order_details = OrderDetails(
            order_id='id001',
            buyer='Nicolas',
            room='Le trou des chouettes',
            orders=[OrderItem(item='Latte', recipient='Shawn', order_ts=100004)],
            open_ts=100001,
            close_ts=100005,
        )
        self.GIVEN(needs_port='db_get_order_details', returns=order_details)  # there is an open order

        self.WHEN(port_called='show_orders', room='Le trou des chouettes')

        self.THEN(expected_output=order_details)
        self.assert_port_called_once_with(needs_port='db_get_order_details', room='Le trou des chouettes')

    def test_raises_when_no_open_offer(self):
        self.GIVEN(needs_port='db_get_order_details', returns=None)  # no active orders

        with self.assertRaisesRegexp(InvalidAction, 'There are no open offers in this room'):
            self.WHEN(port_called='show_orders', room='Le trou des chouettes')
