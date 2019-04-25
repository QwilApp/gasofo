import logging
import re
from collections import namedtuple

from octa.exceptions import (
    WiringError,
    PortDefinitionError,
    NotAdapted
)

__author__ = 'shawn'


logger = logging.getLogger(__name__)


VALID_PORT_NAME_FORMAT = re.compile(r'[a-z][a-zA-Z0-9_]*')
RESERVED_NAMES = frozenset((
    'get_needs',
    'get_provides',
    'meta',
))


PortProvider = namedtuple('PortProvider', 'resource port_name')


def bypass_adapter(provider, provider_port_name):
    return getattr(provider, provider_port_name)


class UnadaptedPort(object):
    def __init__(self, parent, port_name):
        self.parent = parent
        self.port_name = port_name

    def __call__(self, *_, **kwargs):
        raise NotAdapted('Unadapted port "{}" called on {}'.format(self.port_name, self.parent))


class PortArray(object):
    """ Mixin that generalises the concept of ports that can be created and adapted.

        This would be used as a proxy to the Needs of a Service, but could also be used to implement intermediary
        Needs and Provides ports of a Domain that is hooked up with the encapsulated Services.
    """

    VALID_PORT_NAME_FORMAT = re.compile(r'[a-z][a-zA-Z0-9_]*')

    RESERVED_NAMES = frozenset((
        'get_needs',
        'get_provides',
        'add_port',
        'assign_port_provider',
        'connect_port',
        'meta',
    ))

    def __init__(self):
        self._ports = set()
        self._providers = {}
        self._connected = set()

    def get_needs(self):
        return list(self._ports)

    def add_port(self, port_name):
        if port_name in self._ports:
            raise PortDefinitionError('Port "{}" already defined'.format(port_name))
        self._ports.add(port_name)

        assert not hasattr(self, port_name), 'did we missed a reserved name?'
        setattr(self, port_name, UnadaptedPort(self, port_name))

    def assign_port_provider(self, port_name, provider, provider_port_name):
        if port_name not in self._ports:
            raise PortDefinitionError('Port "{}" does not exist on {}'.format(port_name, self))
        if port_name in self._providers:
            raise PortDefinitionError('Port "{}" on {} already has provider {}'.format(
                port_name,
                self,
                self._providers[port_name]
            ))
        self._providers[port_name] = PortProvider(resource=provider, port_name=provider_port_name)

    def connect_port(self, port_name, with_adapter=None, adapter_factory=bypass_adapter):
        if port_name not in self._ports:
            raise PortDefinitionError('Port "{}" does not exist on {}'.format(port_name, self))
        if port_name in self._connected:
            raise PortDefinitionError('Port "{}" on {} already connected'.format(port_name, self))

        try:
            port_provider = self._providers[port_name]
        except KeyError:
            raise PortDefinitionError('Port "{}" on {} has not been assigned a provider'.format(port_name, self))

        if with_adapter:
            adapter = with_adapter
        else:
            adapter = adapter_factory(port_provider.resource, port_provider.port_name)

        if not callable(adapter):
            raise WiringError('Adapter for port "{}" on {} is not callable'.format(port_name, self))

        setattr(self, port_name, adapter)
        self._connected.add(port_name)

    @classmethod
    def assert_valid_port_name(cls, name):
        if not cls.VALID_PORT_NAME_FORMAT.match(name):
            raise PortDefinitionError('"{}" is not a valid port name. Expected pattern - "{}"'.format(
                name,
                cls.VALID_PORT_NAME_FORMAT.pattern,
            ))

        if name in cls.RESERVED_NAMES:
            raise PortDefinitionError('"{}" is a reserved word and cannot be used as a port name'.format(name))


class ProviderMeta(object):

    def get_provides(self):
        raise NotImplemented('implement me to return a list of Provides port names.')

    def get_port_provider(self, port_name):
        raise NotImplemented('implement me to return a PortProvider instance.')

    def get_provider_func(self, port_name):
        raise NotImplemented('implement me to return a callable that does the actual providing')

    def get_port_flag(self, port_name, flag_name):
        raise NotImplemented('implement me to return a flag value or None')

    def get_port_flags(self, port_name):
        raise NotImplemented('implement me to return a dict of flags')


class HasNeedsAndProvides(object):
    """Base class for all constructs that has discoverable Needs and Provides ports."""

    deps = PortArray()  # will be overridden by subclass
    meta = ProviderMeta()  # will be overridden by subclass

    @classmethod
    def get_needs(cls):
        return list(cls.deps.get_needs())

    @classmethod
    def get_provides(cls):
        return cls.meta.get_provides()


def auto_discover_needs(consumers, producers, raise_if_needs_unsatisfied=True):
    wired = []
    needers = {}
    for consumer in consumers:
        for port in consumer.get_needs():
            needers.setdefault(port, []).append(consumer)

    providers = {}
    for producer in producers:
        for port in producer.get_provides():
            if port not in needers:
                continue
            if port in providers:
                raise WiringError('Duplicate providers of "{}" - {} and {}'.format(port, providers[port], producer))

            providers[port] = producer

    for port in needers:
        try:
            provider = providers[port]
        except KeyError:
            if raise_if_needs_unsatisfied:
                raise WiringError('No providers found for "{}"'.format(port))
            else:
                continue

        for consumer in needers[port]:
            if provider is consumer:
                raise WiringError('Attempt by {} to satisfy its own needs ("{}")'.format(provider, port))
            port_provider = providers[port].meta.get_port_provider(port)
            consumer.deps.assign_port_provider(
                port_name=port,
                provider=port_provider.resource,
                provider_port_name=port_provider.port_name
            )
            wired.append(port)

            logger.debug('[AUTO-WIRING] {}.{} --> {}.{}'.format(
                _get_resource_label(consumer), port,
                _get_resource_label(provider), port,
            ))

    return wired


def _get_resource_label(resource):
    """Used for resolving a label we could use to reference a resource type, whether it is a class or object."""
    try:
        return resource.__name__
    except AttributeError:
        if hasattr(resource, '__class__'):
            return resource.__class__.__name__
        else:
            return str(resource)


