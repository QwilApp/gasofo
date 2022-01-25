from example.shared.exceptions import InvalidAction
from example.shared.datatypes import OrderDetails
from typing import Optional, List
from gasofo import (
    NeedsInterface,
    Service,
    provides
)


class OrderHistoryNeeds(NeedsInterface):

    def db_store_closed_order(self, order_details: OrderDetails) -> OrderDetails:
        """Stores an order"""

    def db_get_closed_orders_for_room(self, room: str) -> Optional[List[OrderDetails]]:
        """Returns list of historical orders for given room."""


class OrderHistory(Service):

    deps = OrderHistoryNeeds()

    @provides
    def archive_order(self, order_details: OrderDetails) -> OrderDetails:
        """Archives a closed order."""
        if order_details.close_ts is None:
            raise InvalidAction('Cannot archive open orders')
        stored = self.deps.db_store_closed_order(order_details=order_details)
        return stored

    @provides
    def get_order_history(self, room: str) -> List[OrderDetails]:
        orders = self.deps.db_get_closed_orders_for_room(room=room)
        if orders:
            return orders
        else:
            return []
