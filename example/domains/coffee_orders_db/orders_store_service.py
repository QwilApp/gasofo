from copy import deepcopy

from example.shared.datatypes import (
    OrderSummary,
    OrderItem,
    OrderDetails
)
from example.shared.exceptions import InvalidAction
from octa import (
    Service,
    Needs,
    provides_with
)


class OrdersStore(Service):
    """Dummy store that persists data in-memory rather than in DB."""

    deps = Needs([
        "get_current_ts",
        "get_next_unique_id",
    ])

    def __init__(self):
        super(OrdersStore, self).__init__()
        self._orders = {}

    @staticmethod
    def _extract_summary(order_details):
        return OrderSummary(order_id=order_details.order_id, buyer=order_details.buyer, room=order_details.room)

    @provides_with(name='db_create_order')
    def create_order(self, room, buyer):
        if room in self._orders:
            raise InvalidAction('Order already open for room ' + room)

        order_details = OrderDetails(
            order_id=self.deps.get_next_unique_id(),
            buyer=buyer,
            room=room,
            orders=[],
            open_ts=self.deps.get_current_ts(),
            close_ts=None,
        )

        self._orders[room] = order_details
        order_summary = self._extract_summary(order_details)
        return order_summary

    @provides_with(name='db_close_order')
    def close_order(self, room):
        try:
            order = self._orders.pop(room)
        except KeyError:
            raise InvalidAction('No open orders for room ' + room)

        closed_order = order._replace(close_ts=self.deps.get_current_ts())
        return closed_order

    @provides_with(name='db_has_active_order')
    def has_active_order(self, room):
        return room in self._orders

    @provides_with(name='db_add_order_item')
    def add_order_item(self, room, item, recipient):
        try:
            order_details = self._orders[room]
        except KeyError:
            raise InvalidAction('No open orders for room ' + room)

        order_item = OrderItem(item=item, recipient=recipient, order_ts=self.deps.get_current_ts())
        order_details.append(order_item)
        return order_item

    @provides_with(name='db_get_order_details')
    def get_order_details(self, room):
        try:
            order_details = self._orders[room]
        except KeyError:
            raise InvalidAction('No open orders for room ' + room)

        return deepcopy(order_details)