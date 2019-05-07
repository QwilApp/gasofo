from collections import namedtuple

from gasofo.exceptions import (
    DisconnectedPort,
    DuplicateProviders,
    IncompatibleProvider,
    SelfReferencingMadness,
    UnknownPort
)

__author__ = 'shawn'


class IProvide(object):
    def get_provides(self):  # pragma: no cover
        raise NotImplementedError('Implement me to return list of Provides port names')

    def get_provider_func(self, port_name):  # pragma: no cover
        raise NotImplementedError('Implement me to return a callable given a port name')

    def get_provider_flag(self, port_name, flag_name):  # pragma: no cover
        raise NotImplementedError('Implement me to return a flag value or None if unset')

    def get_provider_flags(self, port_name):  # pragma: no cover
        raise NotImplementedError('Implement me to return a dict of flags')


class INeed(object):
    def __init__(self):
        self._providers = {}

    def get_needs(self):  # pragma: no cover
        raise NotImplementedError('Implement me to return a list of Needs port names')

    def _satisfy_need(self, port_name, func):  # pragma: no cover
        raise NotImplementedError('Implement me to implement logic for satisfying internal Need')

    def _is_compatible_provider(self, port_name, provider):  # pragma: no cover
        raise NotImplementedError('Implement me to check if provider is compatible with given port')

    def set_provider(self, port_name, provider):
        if port_name in self._providers:
            raise DuplicateProviders('There is already a provider for "{}"'.format(port_name))

        if not self._is_compatible_provider(port_name, provider):
            raise IncompatibleProvider('{} is not compatible with port "{}"'.format(provider, port_name))
        self._satisfy_need(port_name, provider.get_provider_func(port_name))
        self._providers[port_name] = provider

    def get_provider(self, port_name):
        try:
            return self._providers[port_name]
        except KeyError:
            raise DisconnectedPort('"{}" has not been assigned a provider'.format(port_name))


DiscoveredConnection = namedtuple('DiscoveredConnection', 'port_name consumer provider')


class AutoDiscoverConnections(object):

    def __init__(self, components):
        self._components = components
        self._needs = self._gather_needs(components)
        self._provides = self._gather_provides(components)
        self.assert_no_components_satisfying_themselves(self._needs, self._provides)

    def get_needs(self):
        return sorted(self._needs.iterkeys())

    def get_provides(self):
        return sorted(self._provides.iterkeys())

    def unsatisfied_needs(self):
        unsatisfied = set(self._needs).difference(self._provides)
        return sorted(unsatisfied)

    def satisfied_needs(self):
        satisfied = set(self._needs).intersection(self._provides)
        return sorted(satisfied)

    def get_provider(self, port_name):
        try:
            return self._provides[port_name]
        except KeyError:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))

    def connections(self):
        for port in self._needs:
            provider = self._provides.get(port, None)
            if not provider:
                continue
            for consumer in self._needs[port]:
                yield DiscoveredConnection(port_name=port, consumer=consumer, provider=provider)

    @staticmethod
    def _gather_needs(components):
        needs = {}
        needy_components = (c for c in components if hasattr(c, 'get_needs'))
        for component in needy_components:
            for port in component.get_needs():
                needs.setdefault(port, []).append(component)
        return needs

    @staticmethod
    def _gather_provides(components):
        provides = {}
        provider_components = (c for c in components if hasattr(c, 'get_provides'))
        for component in provider_components:
            for port in component.get_provides():
                if port in provides:
                    msg = 'Duplicate providers for "{}" - {} and {}'.format(port, component, provides[port])
                    raise DuplicateProviders(msg)
                provides[port] = component
        return provides

    @staticmethod
    def assert_no_components_satisfying_themselves(needs, provides):
        for port, needy_component in needs.iteritems():
            provider = provides.get(port, None)
            if provider and provider in needy_component:
                raise SelfReferencingMadness('{} both needs and provides "{}". Madness.'.format(provider, port))


def wire_up_discovered_connections(discovered):
    for port_name, consumer, provider in discovered.connections():
        consumer.set_provider(port_name=port_name, provider=provider)


def auto_wire(components, expect_all_ports_connected=False):
    discovered = AutoDiscoverConnections(components)

    no_matches = discovered.unsatisfied_needs()
    if expect_all_ports_connected and no_matches:
        raise DisconnectedPort('The following ports are disconnected - {}'.format(', '.join(no_matches)))

    wire_up_discovered_connections(discovered)
