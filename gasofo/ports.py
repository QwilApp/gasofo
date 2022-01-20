import re
from functools import partial
from typing import (
    Callable,
    List,
    Optional,
    Set,
    Union,
)

from gasofo.exceptions import (
    DisconnectedPort,
    DuplicatePortDefinition,
    InvalidPortName,
    UnknownPort,
    WiringError,
)

VALID_PORT_NAME_FORMAT = re.compile(r'[a-z][a-zA-Z0-9_]*$')

RESERVED_PORT_NAMES = frozenset((
    'meta',
    'deps',
    'add_port',
    'get_ports',
    'replicate',
    'is_disconnected_port',
    'disconnect_port',
    'connect_port',
    'get_needs',
    'get_provides',
    'get_interface_class',
    'assert_valid_port_name',
))


class PortArray:
    def __init__(self):
        self._ports = set()

    def add_port(self, port_name: str):
        self.assert_valid_port_name(port_name)
        if port_name in self._ports:
            raise DuplicatePortDefinition('Port "{}" already defined'.format(port_name))

        self._ports.add(port_name)
        # TODO: generate func that inherits argspec from a template func (if one is provided)
        raise_not_connected = self._get_placeholder_func_for_disconnected_port(port_name=port_name)
        setattr(self, port_name, raise_not_connected)

    def get_ports(self) -> List[str]:
        return list(self._ports)

    def connect_port(self, port_name: str, func: Callable):
        if not callable(func):
            raise WiringError('Cannot connect port to a non-callable object')
        if port_name not in self._ports:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))
        setattr(self, port_name, func)

    def disconnect_port(self, port_name: str):
        if port_name not in self._ports:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))
        raise_not_connected = self._get_placeholder_func_for_disconnected_port(port_name=port_name)
        setattr(self, port_name, raise_not_connected)

    @staticmethod
    def _get_placeholder_func_for_disconnected_port(port_name: str):
        func = partial(not_yet_connected, port_name)
        setattr(func, 'disconnected', True)  # used to identify if func is a placeholder for disconnected ports
        return func

    def is_disconnected_port(self, port_name: str) -> bool:
        if port_name not in self._ports:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))
        port = getattr(self, port_name)
        return getattr(port, 'disconnected', False)

    @classmethod
    def replicate(cls, another_port_array: 'PortArray') -> 'PortArray':
        new_array = cls()
        for port in another_port_array.get_ports():
            new_array.add_port(port)
        return new_array

    @staticmethod
    def assert_valid_port_name(port_name: str):
        if not VALID_PORT_NAME_FORMAT.match(port_name):
            raise InvalidPortName('"{}" does not have required format for port names'.format(port_name))

        if port_name in RESERVED_PORT_NAMES:
            raise InvalidPortName('"{}" is a reserved word and cannot be used as port name'.format(port_name))


def not_yet_connected(port_name: str, *_, **__):
    raise DisconnectedPort('Port "{}" has not been connected'.format(port_name))


class ShadowPortArray:
    """Fronts a group of PortArrays and passes on operations to relevant child array."""
    def __init__(self, arrays: List[Union[PortArray, 'ShadowPortArray']], ignore_ports: Optional[List[str]] = None):
        self.ignored_ports = set(ignore_ports or [])
        self._children = arrays
        self._ports = self._gather_ports(arrays=self._children, ignored_ports=self.ignored_ports)

    def get_ports(self) -> List[str]:
        return list(self._ports.keys())

    def connect_port(self, port_name: str, func: Callable):
        if not callable(func):
            raise WiringError('Cannot connect port to a non-callable object')
        if port_name not in self._ports:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))

        for array in self._ports[port_name]:
            array.connect_port(port_name, func)

    def disconnect_port(self, port_name: str):
        if port_name not in self._ports:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))

        for array in self._ports[port_name]:
            array.disconnect_port(port_name)

    @staticmethod
    def _gather_ports(arrays: List[Union[PortArray, 'ShadowPortArray']], ignored_ports: Set[str]):
        ports = {}
        for array in arrays:
            for port in array.get_ports():
                if port in ignored_ports:
                    continue
                ports.setdefault(port, []).append(array)
        return ports
