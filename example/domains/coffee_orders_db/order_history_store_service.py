from example.shared.datatypes import OrderDetails
from gasofo import (
    NeedsInterface,
    Service,
    provides,
)


class OrderHistoryStoreNeeds(NeedsInterface):

    def get_dict_store_for_order_history(self) -> dict:
        """Gets a reference to a dict object from and in-mem provider."""


class OrderHistoryStore(Service):
    """Dummy store that persists data in-memory rather than in DB."""

    deps = OrderHistoryStoreNeeds()

    @provides
    def db_store_closed_order(self, order_details: OrderDetails):
        room = order_details.room
        immutable_order = order_details._replace(orders=list(order_details.orders))
        self._orders_by_room.setdefault(room, []).append(immutable_order)

    @provides
    def db_get_closed_orders_for_room(self, room: str) -> OrderDetails:
        return self._orders_by_room.get(room, [])

    @property
    def _orders_by_room(self):
        return self._get_dict_store()

    def _get_dict_store(self):
        """PLEASE DO NOT CONSIDER THIS AN EXAMPLE OF GOOD PRACTICE.

           We're doing this to simplify the example and not have to used a DB/redis provider for storage, while keeping
           the Service questionably 'stateless'.
        """
        return self.deps.get_dict_store_for_order_history()
