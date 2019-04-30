from example.domains.coffee_orders_db.order_history_store_service import OrderHistoryStore
from example.domains.coffee_orders_db.orders_store_service import OrdersStore
from gasofo import Domain, AutoProvide

__author__ = 'shawn'
__all__ = ['CoffeeOrderDBInterface']


class CoffeeOrderDBInterface(Domain):
    """Domain which encapsulates DB layer used by Coffee Order Domain."""

    __services__ = [
        OrdersStore,
        OrderHistoryStore,
    ]

    __provides__ = AutoProvide(pattern=r'bl_.+')
