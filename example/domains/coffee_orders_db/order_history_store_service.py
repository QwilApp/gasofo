from collections import defaultdict

from octa import (
    Service,
    provides
)


__author__ = 'shawn'


class OrderHistoryStore(Service):
    """Dummy store that persists data in-memory rather than in DB."""

    def __init__(self):
        super(OrderHistoryStore, self).__init__()
        self._orders_by_room = defaultdict(list)

    @provides
    def db_store_order(self, order_details):
        room = order_details.room
        immutable_order = order_details._replace(orders=tuple(order_details.orders))
        self._orders_by_room[room].append(immutable_order)

    @provides
    def db_get_closed_orders_for_room(self, room):
        return self._orders_by_room.get(room, [])