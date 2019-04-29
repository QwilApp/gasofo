from example.shared.exceptions import InvalidAction
from gasofo import (
    Needs,
    Service,
    provides
)

__author__ = 'shawn'


class OrderHistory(Service):
    deps = Needs([
        "db_store_order",
        "db_get_closed_orders_for_room",
    ])

    def archive_order(self, order_details):
        """Archives a closed order.

        Args:
            order_details (OrderDetails): A closed order.
        """
        if order_details.close_ts is None:
            raise InvalidAction('Cannot archive open orders.')
        self.deps.db_store_order(order_details=order_details)

    @provides
    def get_order_history(self, room):
        orders = self.deps.db_get_closed_orders_for_room(room=room)
        if orders:
            return orders
        else:
            return []
