from example.domains.coffee_orders.coffee_menu_service import CoffeeMenu
from example.domains.coffee_orders.order_history_service import OrderHistory
from example.domains.coffee_orders.orders_service import Orders
from gasofo import Domain


__all__ = ['CoffeeOrderDomain']


class CoffeeOrderDomain(Domain):
    """Coffee Order Domain which encapsulates and auto wires all internal services."""

    __services__ = [
        CoffeeMenu,
        OrderHistory,
        Orders,
    ]

    __provides__ = [
        "open_for_orders",
        "close_orders",
        "make_order",
        "show_orders",
        "get_menu_items",
        "get_order_history"
    ]
