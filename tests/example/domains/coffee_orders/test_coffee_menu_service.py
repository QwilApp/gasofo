from example.domains.coffee_orders.coffee_menu_service import CoffeeMenu
from gasofo.testing import GasofoTestCase


class CoffeeMenuServiceTest(GasofoTestCase):
    SERVICE_CLASS = CoffeeMenu

    def test_get_menu_items__returns_statis_set_of_items(self):
        expected = {
            "Black Americano",
            "White Americano",
            "Cappucino",
            "Flat White",
            "English Breakfast Tea",
            "Hot Chocolate",
        }

        self.assertItemsEqual(expected, self.service.get_menu_items())

    def test_is_valid_menu_item__returns_False_if_item_not_in_menu(self):
        self.assertFalse(
            self.WHEN(port_called='is_valid_menu_item', item_name='Organic Triple Oat Decaf Vegan Frappuccino')
        )

    def test_is_valid_menu_item__returns_True_for_valid_items(self):
        self.assertTrue(
            self.WHEN(port_called='is_valid_menu_item', item_name='Flat White')
        )
