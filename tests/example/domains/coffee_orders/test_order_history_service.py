from unittest import TestCase

from example.domains.coffee_orders.order_history_service import OrderHistory
from example.shared.datatypes import OrderDetails
from example.shared.exceptions import InvalidAction
from gasofo.testing import (
    GasofoTestCase,
    attach_mock_provider,
)


def make_order_details(order_id, is_open_order=False, **kwargs):
    order = OrderDetails(
        order_id=order_id,
        buyer='John Buyer',
        room='Awesome Chatroom',
        orders=[],
        open_ts=10000,
        close_ts=None if is_open_order else 20000,
    )
    if kwargs:
        order = order._replace(**kwargs)
    return order


class OrderHistoryServiceTestSimplified(GasofoTestCase):
    # See OrderHistoryServiceTestWithoutFramework for an example of how to test this without GIVEN/WHEN/THEN

    SERVICE_CLASS = OrderHistory

    def test_archive_order__rejects_open_orders(self):
        open_order = make_order_details(order_id='id001', is_open_order=True)

        with self.assertRaisesRegexp(InvalidAction, 'Cannot archive open orders'):
            self.WHEN(port_called='archive_order', order_details=open_order)

    def test_archive_order__closed_order_are_written_to_db(self):
        # GIVEN db_store_closed_order is connected to something that returns object after saving it
        self.GIVEN(needs_port='db_store_closed_order', has_side_effect=lambda order_details: order_details)
        order = make_order_details(order_id='id001')

        # WHEN archive_order is called with an order
        self.WHEN(port_called='archive_order', order_details=order)

        # THEN the needs port is called and its output value is returned
        self.THEN(expected_output=order)
        self.assert_port_called_once_with(needs_port='db_store_closed_order', order_details=order)

    def test_get_order_history__returns_list_of_orders_retrieved_from_db(self):
        # GIVEN db_store_closed_order port returns a list of orders
        orders = [make_order_details(order_id='id001'), make_order_details(order_id='id002')]
        self.GIVEN(needs_port='db_get_closed_orders_for_room', returns=orders)

        # WHEN provides port called
        self.WHEN(port_called='get_order_history', room='room_x')

        # THEN the orders are returned
        self.THEN(expected_output=orders, is_sequence=True, order_matters=True)
        self.assert_port_called_once_with(needs_port='db_get_closed_orders_for_room', room='room_x')

    def test_get_order_history__returns_empty_list_if_no_historical_data(self):
        # GIVEN db_store_closed_order port returns a None (room with no historical orders)
        self.GIVEN(needs_port='db_get_closed_orders_for_room', returns=None)

        # WHEN provides port called
        self.WHEN(port_called='get_order_history', room='room_x')

        # THEN empty list returned
        self.THEN(expected_output=[])
        self.assert_port_called_once_with(needs_port='db_get_closed_orders_for_room', room='room_x')


class OrderHistoryServiceTestWithoutFramework(TestCase):
    # Replicates the OrderHistoryServiceTestSimplified tests, but without using GIVEN/WHEN/THEN methods

    def setUp(self):
        self.service = OrderHistory()

    def test_archive_order__rejects_open_orders(self):
        open_order = make_order_details(order_id='id001', is_open_order=True)

        with self.assertRaisesRegexp(InvalidAction, 'Cannot archive open orders'):
            self.service.archive_order(order_details=open_order)

    def test_archive_order__closed_order_are_written_to_db(self):
        # GIVEN db_store_closed_order is connected to something that returns object after saving it
        provider = attach_mock_provider(consumer=self.service, ports=['db_store_closed_order'])
        provider.db_store_closed_order.side_effect = lambda order_details: order_details

        order = make_order_details(order_id='id001')

        # WHEN archive_order is called with an order
        output = self.service.archive_order(order_details=order)

        # THEN the needs port is called and its output value is returned
        self.assertEqual(order, output)
        provider.db_store_closed_order.assert_called_once_with(order_details=order)

    def test_get_order_history__returns_list_of_orders_retrieved_from_db(self):
        # GIVEN db_store_closed_order port returns a list of orders
        orders = [make_order_details(order_id='id001'), make_order_details(order_id='id002')]
        provider = attach_mock_provider(consumer=self.service, ports={'db_get_closed_orders_for_room': orders})

        # WHEN provides port called
        output = self.service.get_order_history(room='room_x')

        # THEN the orders are returned
        self.assertSequenceEqual(orders, output)
        provider.db_get_closed_orders_for_room.assert_called_once_with(room='room_x')

    def test_get_order_history__returns_empty_list_if_no_historical_data(self):
        # GIVEN db_store_closed_order port returns a None (room with no historical orders)
        provider = attach_mock_provider(consumer=self.service, ports={'db_get_closed_orders_for_room': None})

        # WHEN provides port called
        output = self.service.get_order_history(room='room_x')

        # THEN empty list returned
        self.assertSequenceEqual([], output)
        provider.db_get_closed_orders_for_room.assert_called_once_with(room='room_x')

    @staticmethod
    def _make_order(order_id, is_open_order=False, **kwargs):
        order = OrderDetails(
            order_id=order_id,
            buyer='John Buyer',
            room='Awesome Chatroom',
            order_ts=10000,
            close_ts=None if is_open_order else 20000,
        )
        if kwargs:
            order = order._replace(**kwargs)
        return order
