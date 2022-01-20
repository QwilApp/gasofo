"""
Simple data types used as shared DTOs.
"""
from typing import (
    List,
    NamedTuple,
    Optional,
)


# TODO: should these be owned by specific services/domains?
# TODO: adapters to convert OrderSummary and OrderDetails DTO into chat-friendly text representation


class OrderSummary(NamedTuple):
    order_id: str
    buyer: str
    room: str


class OrderItem(NamedTuple):
    item: str
    recipient: str
    order_ts: int


class OrderDetails(NamedTuple):
    order_id: str
    buyer: str
    room: str
    orders: List[OrderItem]
    open_ts: int
    close_ts: Optional[int]

