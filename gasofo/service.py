import inspect
from typing import (
    Any,
    Dict,
    Generic,
    List,
    TypeVar,
)

from gasofo.dep_parser import parse_deps_used
from gasofo.discoverable import (
    INeed,
    IProvide,
)
from gasofo.exceptions import (
    DuplicateProviders,
    ServiceDefinitionError,
    UnknownPort,
    UnusedPort,
)
from gasofo.ports import (
    PortArray,
    RESERVED_PORT_NAMES,
)
from gasofo.service_needs import (
    Needs,
)


def provides(method):
    """Decorator which tags class methods so they can be detected as a provider of a Service."""
    method.__port_attributes__ = {}  # set up as dict so we can tag on extra stuff later
    return method


def provides_with(name: str = None, **kwargs):
    """ Decorator which tags class methods so they can be detected as a provider of a Service.

        Use this instead of @provides when exposing a port with a custom name or to tag on additional flags.
    """
    PortArray.assert_valid_port_name(port_name=name)
    port_attrs = kwargs

    if name:
        PortArray.assert_valid_port_name(port_name=name)
        port_attrs['with_name'] = name

    def decorator(method):
        method.__port_attributes__ = port_attrs
        return method

    return decorator


# Provider Meta could reference providers by provider class, instance, or by name depending on  where it is used.
REF_TYPE = TypeVar('REF_TYPE')


class ProviderMetadata(Generic[REF_TYPE]):
    def __init__(self):
        self._providers: Dict[str, REF_TYPE] = {}
        self._flags: Dict[str, Any] = {}

    def get_provides(self) -> List[str]:
        return list(self._providers.keys())

    def get_provider_flag(self, port_name: str, flag_name: str) -> Any:
        try:
            return self._flags[port_name].get(flag_name, None)
        except KeyError:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))

    def get_provider_flags(self, port_name: str) -> dict:
        try:
            return self._flags[port_name].copy()
        except KeyError:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))

    def get_provider(self, port_name) -> REF_TYPE:
        try:
            return self._providers[port_name]
        except KeyError:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))

    def register_provider(self, port_name: str, provider: REF_TYPE, flags: dict):
        if port_name in self._providers:
            raise DuplicateProviders('Duplicate providers for "{}"'.format(port_name))

        self._providers[port_name] = provider
        self._flags[port_name] = flags or {}


class ServiceProviderMetadata(ProviderMetadata[str]):
    """ meta that references provider by name """
    def get_provider_method_name(self, port_name: str) -> str:
        try:
            return self._providers[port_name]
        except KeyError:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))


class ServiceMetaclass(type):
    """ Metaclass that makes classes aware of @provides and ensures .deps and .meta is specified correctly."""

    def __new__(mcs, name, bases, state):
        if bases == (INeed, IProvide):  # This is the Service class itself, not its subclass
            return type.__new__(mcs, name, bases, state)

        mcs.validate_overridden_attributes(attrs=state, class_name=name)

        # walk attributes and register the ones that have been tagged by @provides
        meta = ServiceProviderMetadata()
        for attr_name, member in state.items():
            if hasattr(member, '__port_attributes__') and callable(member):  # tagged

                port_name = member.__port_attributes__.get('with_name', attr_name)
                PortArray.assert_valid_port_name(port_name)
                meta.register_provider(port_name=port_name, provider=attr_name, flags=member.__port_attributes__)

        mcs.validate_deps_declaration_and_usage(class_state=state, class_name=name)

        state['meta'] = meta
        return type.__new__(mcs, name, bases, state)

    @classmethod
    def validate_overridden_attributes(mcs, attrs: dict, class_name: str):
        if 'meta' in attrs:
            raise ServiceDefinitionError('"meta" is a reserved attributes and should not be overridden')

        if 'deps' in attrs and not isinstance(attrs['deps'], Needs):
            raise ServiceDefinitionError('{}.deps must be an instance of gasofo.Needs'.format(class_name))

        if '__init__' in attrs:
            raise ServiceDefinitionError('To emphasize statelessness, {} should not define __init__'.format(class_name))

    @classmethod
    def validate_deps_declaration_and_usage(mcs, class_state: dict, class_name: str):
        deps = class_state.get('deps', None)
        needs_ports_defined = frozenset(deps.get_ports() if deps else ())
        all_deps_used = set()

        for attr_name, member in class_state.items():
            if callable(member):
                deps_used = parse_deps_used(member)
                invalid_ports = deps_used.difference(needs_ports_defined).difference(RESERVED_PORT_NAMES)
                all_deps_used.update(deps_used)
                if invalid_ports:
                    raise UnknownPort('{}.{} references undeclared Needs - {}'.format(
                        class_name,
                        attr_name,
                        ', '.join(sorted(invalid_ports))
                    ))

        unused_needs = needs_ports_defined.difference(all_deps_used)
        if unused_needs:
            raise UnusedPort('{} has unused Needs - {}'.format(class_name, ', '.join(sorted(unused_needs))))


class Service(INeed, IProvide, metaclass=ServiceMetaclass):

    deps = Needs([])  # override me in subclass to define service needs

    def __init__(self):
        super(Service, self).__init__()
        self.deps = PortArray.replicate(self.__class__.deps)   # each service instance should have its own copy

    # ---- implement INeed ----
    @classmethod
    def get_needs(cls):
        return cls.deps.get_ports()

    def _is_compatible_provider(self, port_name, provider):
        return True  # no flag checking for now

    def _satisfy_need(self, port_name, func):
        self.deps.connect_port(port_name, func)

    # ---- implement IProvide ----

    @classmethod
    def get_provides(cls):
        return cls.meta.get_provides()

    def get_provider_func(self, port_name):
        meta = self.__class__.meta
        method_name = meta.get_provider_method_name(port_name)
        return getattr(self, method_name)

    @classmethod
    def get_provider_flag(cls, port_name, flag_name):
        return cls.meta.get_provider_flag(port_name, flag_name)

    @classmethod
    def get_provider_flags(cls, port_name):
        return cls.meta.get_provider_flags(port_name)


def get_template_funcs(service):
    """Used by gasofo testing utils to assert calls are made with correct argspec."""
    try:
        if inspect.isclass(service):
            deps = service.deps
        else:
            deps = service.__class__.deps
        return deps._needs_template_funcs.copy()
    except AttributeError:
        return {port: unknown_interface for port in service.get_needs()}


def unknown_interface(self, *args, **kwargs):
    raise NotImplementedError
