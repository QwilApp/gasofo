from typing import Optional

from example.shared.datatypes import OrderSummary, OrderDetails, OrderItem
from example.shared.exceptions import InvalidAction
from gasofo import (
    NeedsInterface,
    Service,
    provides,
)


class OrdersNeeds(NeedsInterface):

    def db_get_active_order(self, room):
        # type: (str) -> Optional[OrderSummary]
        """Returns summary of active order if exists, None otherwise."""

    def db_create_order(self, room, buyer):
        # type: (str, str) -> OrderSummary
        """Creates a new order."""

    def db_close_order(self, room):
        # type: (str) -> OrderDetails
        """Closes an order for the room and returns the details."""

    def db_get_order_details(self, room):
        # type: (str) -> OrderDetails
        """Returns details of open orders for the given room."""

    def db_add_order_item(self, room, item, recipient):
        # type: (str, str, str) -> OrderItem
        """Adds an item to open order of room."""

    def archive_order(self, order_details):
        # type: (OrderDetails) -> OrderDetails
        """Archives a closed order."""

    def is_valid_menu_item(self, item_name):
        # type: (str) -> bool
        """Checks if the given item is on the menu."""


class Orders(Service):

    deps = OrdersNeeds()

    @provides
    def open_for_orders(self, requester, room):
        # type: (str, str) -> OrderSummary
        """Creates an offer to buy coffer by requester in given room.

        Args:
            requester: User ID of buyer
            room: Chat room ID

        Returns:
            Order summary or new order

        Raises:
            InvalidAction: if there is already an open offer in the given room
        """
        active_offer = self.deps.db_get_active_order(room=room)
        if active_offer and active_offer.buyer == requester:
            raise InvalidAction('You already have an open offer to buy coffee')
        elif active_offer:
            raise InvalidAction('There is already an offer to by coffee by ' + active_offer.buyer)

        return self.deps.db_create_order(room=room, buyer=requester)

    @provides
    def close_orders(self, requester, room):
        # type: (str, str) -> OrderDetails
        """Closes an open order.

        Args:
            requester: User ID of buyer
            room: Chat room ID

        Returns:
            Details of the closed order

        Raises:
            InvalidAction: if there are no open offers in the room
            InvalidAction: if requester is not the buyer who opened the offer
        """
        active_offer = self.deps.db_get_active_order(room=room)
        if not active_offer:
            raise InvalidAction('There are no open offers in this room')
        elif active_offer.buyer != requester:
            raise InvalidAction("You cannot close someone else's order")

        order_details = self.deps.db_close_order(room=room)
        self.deps.archive_order(order_details=order_details)
        return order_details

    @provides
    def make_order(self, requester, room, order_item):
        # type: (str, str, str) -> OrderItem
        """Adds an item to the existing order.

        Args:
            requester: User ID of buyer
            room: Chat room ID
            order_item: Name of item being ordered

        Returns:
            Instance of OrderItem

        Raises:
            InvalidAction: if there are no open offers
            InvalidAction: if item being ordered is not valid
        """
        active_offer = self.deps.db_get_active_order(room=room)
        if not active_offer:
            raise InvalidAction('There are no open offers in this room')

        if not self.deps.is_valid_menu_item(item_name=order_item):
            raise InvalidAction(order_item + ' is not a valid menu item')

        order_item = self.deps.db_add_order_item(room=room,
                                                 item=order_item,
                                                 recipient=requester)
        return order_item

    @provides
    def show_orders(self, room):
        # type: (str) -> OrderDetails
        """Returns details of existing open offer.

        Args:
            room: Chat room ID

        Returns:
            Instance of OrderDetails

        Raises:
            InvalidAction: if there are no open offers in the room
        """
        order_details = self.deps.db_get_order_details(room=room)
        if not order_details:
            raise InvalidAction('There are no open offers in this room')

        return order_details
