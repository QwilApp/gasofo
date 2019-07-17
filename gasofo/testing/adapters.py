import mock

from gasofo.convenience import object_as_provider
from gasofo.discoverable import (
    INeed,
    auto_wire,
)
from gasofo.exceptions import UnknownPort
from gasofo.service import get_template_funcs

__author__ = 'shawn'


def attach_mock_provider(consumer, ports):
    assert isinstance(consumer, INeed)
    assert isinstance(ports, (list, dict))

    invalid_ports = set(ports).difference(consumer.get_needs())
    if invalid_ports:
        raise UnknownPort('Invalid ports for {} - {}'.format(consumer, ', '.join(invalid_ports)))

    # create the underlying object that will hold all the mock functions for the specified ports
    template_funcs = get_template_funcs(service=consumer)
    template_func_subset = {port: template_funcs[port] for port in ports}
    template_class = type('Mock' + consumer.__class__.__name__, (), template_func_subset)
    provider_impl = mock.create_autospec(spec=template_class, spec_set=True, instance=True)

    # supply return_value if provider
    if isinstance(ports, dict):
        for port, value in ports.iteritems():
            getattr(provider_impl, port).return_value = value

    provider = object_as_provider(provider=provider_impl, ports=ports)
    auto_wire(components=[consumer, provider])

    return provider_impl
