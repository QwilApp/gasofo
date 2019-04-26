from gasofo.discoverable import (
    INeed,
    IProvide
)
from gasofo.exceptions import (
    DuplicateProviders,
    ServiceDefinitionError,
    UnknownPort
)
from gasofo.ports import PortArray
import inspect


def provides(method):
    """Decorator which tags class methods so they can be detected as a provider of a Service."""
    method.__port_attributes__ = {}  # set up as dict so we can tag on extra stuff later
    return method


def provides_with(name=None, **kwargs):
    """ Decorator which tags class methods so they can be detected as a provider of a Service.

        Use this instead of @provides when exposing a port with a custom name or to tag on additional flags.
    """
    PortArray.assert_valid_port_name(name)
    port_attrs = kwargs

    if name:
        PortArray.assert_valid_port_name(name)
        port_attrs['with_name'] = name

    def decorator(method):
        method.__port_attributes__ = port_attrs
        return method

    return decorator


class Needs(PortArray):
    """Used to defined the Needs ports of a Service."""

    def __init__(self, needs):
        super(Needs, self).__init__()
        for port in needs:
            self.add_port(port)


class ServiceClassMeta(object):
    """ Metadata for providers stored on Service class.

        Provider funcs are referenced only by method names since actual bound method does not exist yet.
    """
    def __init__(self):
        self._providers = {}
        self._flags = {}

    def register_provider(self, port_name, method_name, flags):
        if port_name in self._providers:
            raise DuplicateProviders('Duplicate providers for "{}"'.format(port_name))

        self._providers[port_name] = method_name
        self._flags[port_name] = flags or {}

    def get_provides(self):
        return self._providers.keys()

    def get_provider_method_name(self, port_name):
        try:
            return self._providers[port_name]
        except KeyError:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))

    def get_provider_flag(self, port_name, flag_name):
        try:
            return self._flags[port_name].get(flag_name, None)
        except KeyError:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))

    def get_provider_flags(self, port_name):
        try:
            return self._flags[port_name].copy()
        except KeyError:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))


class ServiceMetaclass(type):
    """ Metaclass that makes classes aware of @provides and ensures .deps and .meta is specified correctly."""

    def __new__(mcs, name, bases, state):
        mcs.validate_overridden_attributes(attrs=state, subclass_name=name)

        # walk attributes and register the ones that have been tagged by @provides
        meta = ServiceClassMeta()
        for attr_name, member in state.iteritems():
            if hasattr(member, '__port_attributes__') and callable(member):  # tagged
                port_name = member.__port_attributes__.get('with_name', attr_name)
                PortArray.assert_valid_port_name(port_name)
                meta.register_provider(port_name=port_name, method_name=attr_name, flags=member.__port_attributes__)

        state['meta'] = meta
        return type.__new__(mcs, name, bases, state)

    @classmethod
    def validate_overridden_attributes(mcs, attrs, subclass_name):
        if 'meta' in attrs:
            raise ServiceDefinitionError('"meta" is a reserved attributes and should not be overridden')

        if 'deps' in attrs and not isinstance(attrs['deps'], Needs):
            raise ServiceDefinitionError('{}.deps must be an instance of {}.{}'.format(
                subclass_name,
                Needs.__module__,
                Needs.__name__,
            ))

        if '__init__' in attrs:
            arg_spec = inspect.getargspec(attrs['__init__'])
            if len(arg_spec.args) != 1 or arg_spec.varargs or arg_spec.keywords:
                raise ServiceDefinitionError('Service constructor should not expect additional args/kwargs')


class Service(INeed, IProvide):
    __metaclass__ = ServiceMetaclass

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
