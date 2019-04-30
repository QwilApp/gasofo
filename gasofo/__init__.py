from gasofo.convenience import (
    func_as_provider,
    object_as_provider
)
from gasofo.discoverable import (
    INeed,
    IProvide,
    auto_wire
)
from gasofo.domain import (
    AutoProvide,
    Domain
)
from gasofo.service import (
    Needs,
    Service,
    provides,
    provides_with
)

__all__ = [
    'auto_wire',
    'AutoProvide',
    'Needs',
    'Service',
    'provides_with',
    'provides',
    'Domain',
    'INeed',
    'IProvide',
    'object_as_provider',
    'func_as_provider',
]
