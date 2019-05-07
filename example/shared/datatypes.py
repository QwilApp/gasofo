"""
Simple data types used as shared DTOs.
"""
from typing import NamedTuple, Optional, List


__author__ = 'shawn'


# TODO: should these be owned by specific services/domains?
# TODO: adapters to convert OrderSummary and OrderDetails DTO into chat-friendly text representation


class OrderSummary(NamedTuple(typename='OrderSummary', fields=[
    ('order_id', str),
    ('buyer', str),
    ('room', str),
])):
    __slots__ = ()


class OrderItem(NamedTuple(typename='OrderItem', fields=[
    ('item', str),
    ('recipient', str),
    ('order_ts', int),
])):
    __slots__ = ()


class OrderDetails(NamedTuple(typename='OrderDetails', fields=[
    ('order_id', str),
    ('buyer', str),
    ('room', str),
    ('orders', List[OrderItem]),
    ('open_ts', int),
    ('close_ts', Optional[int]),
])):
    __slots__ = ()
