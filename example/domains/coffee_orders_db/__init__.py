from example.domains.coffee_orders_db.orders_store_service import OrdersStore
from example.domains.coffee_orders_db.order_history_store_service import OrderHistoryStore

from octa import ServiceGroup

__all__ = ['CoffeeOrderDBInterface']


# TODO: Should this be a service group instead?


class CoffeeOrderDBInterface(ServiceGroup):
    """Domain which encapsulates DB layer used by Coffee Order Domain."""

    __services__ = [
        OrdersStore,
        OrderHistoryStore,
    ]
