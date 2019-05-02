from gasofo.convenience import (
    func_as_provider,
    object_as_provider,
)
from gasofo.discoverable import (
    INeed,
    IProvide,
    auto_wire,
)
from gasofo.domain import (
    AutoProvide,
    Domain,
)
from gasofo.service import (
    Service,
    provides,
    provides_with,
)
from gasofo.service_needs import (
    Needs,
    NeedsInterface,
)

__all__ = [
    'auto_wire',
    'AutoProvide',
    'Needs',
    'NeedsInterface',
    'Service',
    'provides_with',
    'provides',
    'Domain',
    'INeed',
    'IProvide',
    'object_as_provider',
    'func_as_provider',
]
