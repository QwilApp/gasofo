from gasofo import Service, provides


__author__ = 'shawn'


class CoffeeMenu(Service):

    @provides
    def is_valid_menu_item(self, item_name):
        """Determines if the given item is in the menu.

        Args:
            item_name (str): Name of item to look up.

        Returns:
            bool
        """
        return item_name in self._items()

    @provides
    def get_menu_items(self):
        """Returns a list of all menu items.

        Returns:
            list
        """
        return sorted(self._items())  # return a copy

    @staticmethod
    def _items():
        return frozenset([  # for lookup
            "Black Americano",
            "White Americano",
            "Cappucino",
            "Flat White",
            "English Breakfast Tea",
            "Hot Chocolate",
        ])
