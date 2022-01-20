from copy import deepcopy

from typing import Optional

from example.shared.datatypes import (
    OrderDetails,
    OrderItem,
    OrderSummary,
)
from example.shared.exceptions import InvalidAction
from gasofo import (
    NeedsInterface,
    Service,
    provides_with,
)


class OrdersStoreNeeds(NeedsInterface):

    def get_dict_store_for_orders(self):
        # type: () -> dict
        """Gets a reference to a dict object from and in-mem provider."""

    def get_next_unique_id(self):
        # type: () -> str
        """Gets next unique id for orders."""

    def get_current_ts(self):
        # type: () -> int
        """Gets current timestamp."""


class OrdersStore(Service):
    """ Dummy store that persists data in-memory rather than in DB.

        For simplicity, we use a dict for storage but since Services have to be stateless, we expect this dict to be
        provided by a helper via a port.

    """

    deps = OrdersStoreNeeds()

    @provides_with(name='db_create_order')
    def create_order(self, room, buyer):
        # type: (str, str) -> OrderSummary
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
        order_summary = self._extract_summary(order_details=order_details)
        return order_summary

    @provides_with(name='db_close_order')
    def close_order(self, room):
        # type: (str) -> OrderDetails
        try:
            order = self._orders.pop(room)
        except KeyError:
            raise InvalidAction('No open orders for room ' + room)

        closed_order = order._replace(close_ts=self.deps.get_current_ts(), orders=tuple(order.orders))
        return closed_order

    @provides_with(name='db_get_active_order')
    def get_active_order(self, room):
        # type: (str) -> Optional[OrderSummary]
        try:
            order_details = self._orders[room]
            return self._extract_summary(order_details)
        except KeyError:
            return None

    @provides_with(name='db_add_order_item')
    def add_order_item(self, room, item, recipient):
        try:
            order_details = self._orders[room]
        except KeyError:
            raise InvalidAction('No open orders for room ' + room)

        order_item = OrderItem(item=item, recipient=recipient, order_ts=self.deps.get_current_ts())
        order_details.orders.append(order_item)
        return order_item

    @provides_with(name='db_get_order_details')
    def get_order_details(self, room):
        try:
            order_details = self._orders[room]
        except KeyError:
            raise InvalidAction('No open orders for room ' + room)

        return deepcopy(order_details)

    @property
    def _orders(self):
        return self._get_store()

    def _get_store(self):
        """PLEASE DO NOT CONSIDER THIS AN EXAMPLE OF GOOD PRACTICE.

           We're doing this to simplify the example and not have to used a DB/redis provider for storage, while keeping
           the Service questionably 'stateless'.
        """
        return self.deps.get_dict_store_for_orders()

    @staticmethod
    def _extract_summary(order_details):
        return OrderSummary(order_id=order_details.order_id, buyer=order_details.buyer, room=order_details.room)
