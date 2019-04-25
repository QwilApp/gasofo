"""
Simple data types used as shared DTOs.
"""
from collections import namedtuple


__author__ = 'shawn'


# TODO: should these be owned by specific services/domains?
# TODO: adapters to convert OrderSummary and OrderDetails DTO into chat-friendly text representation


OrderSummary = namedtuple('OrderSummary', 'order_id buyer room')

OrderDetails = namedtuple('OrderDetails', 'order_id buyer room orders open_ts close_ts')

OrderItem = namedtuple('OrderItem', 'item recipient order_ts')
