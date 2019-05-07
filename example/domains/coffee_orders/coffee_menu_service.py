from gasofo import Service, provides
from typing import List

__author__ = 'shawn'


class CoffeeMenu(Service):

    @provides
    def is_valid_menu_item(self, item_name):
        # type: (str) -> bool
        """Determines if the given item is in the menu.

        Args:
            item_name: Name of item to look up.

        Returns:
            bool
        """
        return item_name in self._items()

    @provides
    def get_menu_items(self):
        # type: () -> List[str]
        """ Returns a list of all menu items. """
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
