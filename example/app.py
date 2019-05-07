from example.domains.coffee_orders import CoffeeOrderDomain
from example.domains.coffee_orders_db import CoffeeOrderDBInterface
from example.helpers.clock import get_clock_provider
from example.helpers.storage import DictStore
from example.helpers.uuid import UuidGenerator
from gasofo import (
    Domain,
    auto_wire,
)


class App(Domain):
    """This will encapsulate the business domain without any of the edge resources."""
    __services__ = [CoffeeOrderDomain, CoffeeOrderDBInterface]
    __provides__ = CoffeeOrderDomain.get_provides()  # export whatever this domain exports


def create_app():
    app = App()

    edge_dependencies = [
        # Inconsistencies in how these deps are instantiated is down to each helper being implemented differently
        # so as to showcase different options.
        UuidGenerator().as_provider(),
        get_clock_provider(),
        DictStore.as_provider('get_dict_store_for_orders'),
        DictStore.as_provider('get_dict_store_for_order_history'),
    ]

    auto_wire([app] + edge_dependencies, expect_all_ports_connected=True)  # raises if there are disconnected ports

    return app


if __name__ == '__main__':
    create_app()  # Just so we can this module to debug wiring
