from example.shared.exceptions import InvalidAction
from gasofo import (
    Needs,
    Service,
    provides
)

__author__ = 'shawn'


class Orders(Service):
    deps = Needs([
        "db_create_order",
        "db_close_order",
        "db_has_active_order",
        "db_add_order_item",
        "db_get_order_details",

        "is_valid_menu_item",
        "archive_order"
    ])

    @provides
    def open_for_orders(self, requester, room):
        """Creates an offer to buy coffer by requester in given room.

        Args:
            requester (str): User ID of buyer
            room (str): Chat room ID

        Returns:
            Instance of ActiveOfferSummary.

        Raises:
            InvalidAction: if there is already an open offer in the given room
        """
        active_offer = self.deps.db_has_active_order(room=room)
        if active_offer and active_offer.buyer == requester:
            raise InvalidAction('You already have an open offer to buy coffee')
        elif active_offer:
            raise InvalidAction('There is already an offer to by coffee by ' + active_offer.buyer)

        return self.deps.db_create_order(room=room, buyer=requester)

    @provides
    def close_orders(self, requester, room):
        """Closes an open order.

        Args:
            requester (str): User ID of buyer
            room (str): Chat room ID

        Returns:
            Instance of ActiveOfferDetails

        Raises:
            InvalidAction: if there are no open offers in the room
            InvalidAction: if requester is not the buyer who opened the offer
        """
        active_offer = self.deps.db_has_active_order(room=room)
        if not active_offer:
            raise InvalidAction('There are no open offers in this room')
        elif active_offer.buyer != requester:
            raise InvalidAction("You cannot close someone else's order")

        order_details = self.deps.db_close_order(room=room)
        self.deps.archive_order(order_details)
        return order_details

    @provides
    def make_order(self, requester, room, order_item):
        """Adds an item to the existing order.

        Args:
            requester (str): User ID of buyer
            room (str): Chat room ID
            order_item (str): Name of item being ordered

        Returns:
            Instance of OrderItem

        Raises:
            InvalidAction: if there are no open offers
            InvalidAction: if item being ordered is not valid
        """
        active_offer = self.deps.db_has_active_order(room=room)
        if not active_offer:
            raise InvalidAction('There are no open offers in this room')

        menu_item = self.deps.is_valid_menu_item(item_name=order_item)
        if not menu_item:
            raise InvalidAction(order_item + ' is not a valid menu item')

        order_item = self.deps.db_add_order_item(room=room,
                                                 item=menu_item.item,
                                                 recipient=requester)
        return order_item

    @provides
    def show_orders(self, room):
        """Returns details of existing open offer.

        Args:
            room (str): Chat room ID

        Returns:
            Instance of ActiveOfferDetails

        Raises:
            InvalidAction: if there are no open offers in the room
        """
        order_details = self.deps.db_get_order_details(room=room)
        if not order_details:
            raise InvalidAction('There are no open offers in this room')

        return order_details
