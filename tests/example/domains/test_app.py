from builtins import next
from builtins import object
import itertools

from example.app import App
from example.helpers.storage import DictStore
from example.helpers.uuid import UuidGenerator
from gasofo import (
    auto_wire,
    func_as_provider,
)
from gasofo.testing import GasofoTestCase
from example.shared.datatypes import OrderDetails, OrderItem
from example.shared.exceptions import InvalidAction


class AppAcceptanceTests(GasofoTestCase):
    """ Example of how we could do Acceptance/Integration tests against Domains that are wired up. """

    SERVICE_CLASS = App

    def setUp(self):
        super(AppAcceptanceTests, self).setUp()

        dependencies = [
            UuidGenerator(start=1, width=4).as_provider(),  # 'get_next_unique_id' which returns "ID0001", "ID0002", ...
            FakeClock().as_provider(),  # 'get_current_ts' which returns 10001, 10002, ...
            DictStore.as_provider(port_name='get_dict_store_for_orders'),
            DictStore.as_provider(port_name='get_dict_store_for_order_history'),
        ]

        auto_wire(components=[self.service] + dependencies, expect_all_ports_connected=True)

    # NOTE: we are only testing a very small subset of the acceptance criteria here.
    #       This is meant to be merely an example and not a comprehensive test of the app.

    def test_orders_being_made_in_a_room_and_eventually_closed(self):
        # Nicolas offers to buy everyone coffee
        self.call(port='open_for_orders', requester='Nicolas', room='qwil')

        # A bunch of people take up the offer
        self.call(port='make_order', requester='Shawn', room='qwil', order_item='Black Americano')
        self.call(port='make_order', requester='Nicolas', room='qwil', order_item='Flat White')
        self.call(port='make_order', requester='Laura', room='qwil', order_item='Flat White')
        self.call(port='make_order', requester='Casey', room='qwil', order_item='Cappucino')

        # Nicolas closes the order and gets a summary
        summary = self.call(port='close_orders', requester='Nicolas', room='qwil')

        self.assertEqual(OrderDetails(
            order_id='ID0001',
            buyer='Nicolas',
            room='qwil',
            orders=[
                OrderItem(item='Black Americano', recipient='Shawn', order_ts=10002),
                OrderItem(item='Flat White', recipient='Nicolas', order_ts=10003),
                OrderItem(item='Flat White', recipient='Laura', order_ts=10004),
                OrderItem(item='Cappucino', recipient='Casey', order_ts=10005),
            ],
            open_ts=10001,
            close_ts=10006,
        ), summary)

    def test_cannot_make_an_order_if_no_offer_in_current_room(self):
        # Nicolas offers to buy everyone coffee
        self.call(port='open_for_orders', requester='Nicolas', room='qwil')

        # Shawn tries to make an order in a different chat room
        with self.assertRaisesRegexp(InvalidAction, 'There are no open offers in this room'):
            self.call(port='make_order', requester='Shawn', room='baml', order_item='Black Americano')

    def test_historical_closed_orders_can_be_retrieved(self):
        # Order #1
        self.call(port='open_for_orders', requester='Nicolas', room='qwil')
        self.call(port='make_order', requester='Shawn', room='qwil', order_item='Black Americano')
        self.call(port='close_orders', requester='Nicolas', room='qwil')

        # Order #2
        self.call(port='open_for_orders', requester='Shawn', room='qwil')
        self.call(port='make_order', requester='Casey', room='qwil', order_item='Flat White')
        self.call(port='close_orders', requester='Shawn', room='qwil')

        # Order in another room
        self.call(port='open_for_orders', requester='Shawn', room='baml')
        self.call(port='make_order', requester='Justin', room='baml', order_item='Flat White')
        self.call(port='close_orders', requester='Shawn', room='baml')

        # Open Order. Should not show up in historical records.
        self.call(port='open_for_orders', requester='Casey', room='qwil')
        self.call(port='make_order', requester='Nicolas', room='qwil', order_item='Flat White')

        # query order history for 'qwil'
        history = self.call(port='get_order_history', room='qwil')

        self.assertEqual([
            OrderDetails(
                order_id='ID0001',
                buyer='Nicolas',
                room='qwil',
                orders=[
                    OrderItem(item='Black Americano', recipient='Shawn', order_ts=10002),
                ],
                open_ts=10001,
                close_ts=10003,
            ),
            OrderDetails(
                order_id='ID0002',
                buyer='Shawn',
                room='qwil',
                orders=[
                    OrderItem(item='Flat White', recipient='Casey', order_ts=10005),
                ],
                open_ts=10004,
                close_ts=10006,
            )
        ], history)


class FakeClock(object):
    def __init__(self):
        self._counter = itertools.count(start=10001)

    def tick(self):
        return next(self._counter)

    def as_provider(self):
        return func_as_provider(func=self.tick, port='get_current_ts')
