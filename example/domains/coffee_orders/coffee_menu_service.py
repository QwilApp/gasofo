from octa import Service, provides


class CoffeeMenu(Service):

    def __init__(self):
        super(CoffeeMenu, self).__init__()

        self._items = frozenset([  # for lookup
            "Black Americano",
            "White Americano",
            "Cappucino",
            "Flat White",
            "English Breakfast Tea",
            "Hot Chocolate",
        ])
        self._sorted_items = sorted(self._items)

    @provides
    def is_valid_menu_item(self, item_name):
        """Determines if the given item is in the menu.

        Args:
            item_name (str): Name of item to look up.

        Returns:
            bool
        """
        return item_name in self._items

    @provides
    def get_menu_items(self):
        """Returns a list of all menu items.

        Returns:
            list
        """
        return list(self._sorted_items)  # return a copy
