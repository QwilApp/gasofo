from gasofo.discoverable import IProvide
from gasofo.ports import PortArray
from gasofo.exceptions import (
    UnknownPort,
    YouCannotDoThat
)


def object_as_provider(provider, ports):
    return AdHocObjectProvider(provider=provider, ports=ports)


def func_as_provider(func, port):
    return AdHocFuncProvider(provider=func, port_name=port)


class _FlagQueryMixin(object):
    def __init__(self, valid_ports):
        self._ports = valid_ports

    def get_provider_flag(self, port_name, __):
        self._assert_valid_port(port_name)
        return None  # no support for flags yet

    def get_provider_flags(self, port_name):
        self._assert_valid_port(port_name)
        return {}  # no support for flags yet

    def _assert_valid_port(self, port_name):
        if port_name not in self._ports:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))


class AdHocFuncProvider(_FlagQueryMixin, IProvide):
    """Wraps a single callable so it can be published as a provider with a specific port name."""

    def __init__(self, provider, port_name):
        PortArray.assert_valid_port_name(port_name)
        self.provider = provider
        self.port_name = port_name
        _FlagQueryMixin.__init__(self, valid_ports=[port_name])

    def get_provides(self):
        return [self.port_name]

    def get_provider_func(self, port_name):
        if port_name != self.port_name:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))
        else:
            return self.provider


class AdHocObjectProvider(_FlagQueryMixin, IProvide):
    """Wraps an object so it can be published as a provider with some of its attributes exposed as ports."""
    def __init__(self, provider, ports):
        if isinstance(ports, basestring):
            ports = [ports]

        self._assert_attr_exists_on_provider(provider, ports)

        for port_name in ports:
            PortArray.assert_valid_port_name(port_name)

        self.provider = provider
        self.ports = frozenset(ports)
        _FlagQueryMixin.__init__(self, valid_ports=self.ports)

    def get_provides(self):
        return sorted(self.ports)

    def get_provider_func(self, port_name):
        if port_name not in self.ports:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))
        return getattr(self.provider, port_name)

    @staticmethod
    def _assert_attr_exists_on_provider(provider, ports):
        for port in ports:
            try:
                target = getattr(provider, port)
            except AttributeError:
                raise YouCannotDoThat('"{}" is not an attribute of {}'.format(port, provider))

            if not callable(target):
                raise YouCannotDoThat('{}.{} is not callable'.format(provider, port))
