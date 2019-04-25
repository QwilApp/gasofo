import inspect

from octa.exceptions import (
    ServiceDefinitionError,
    PortDefinitionError,
    WiringError
)
from octa.ports import (
    HasNeedsAndProvides,
    PortArray,
    ProviderMeta,
    PortProvider
)


def provides(method):
    """Decorator which tags class methods so they can be detected as a provider of a Service."""
    method.__port_attributes__ = {}  # set up as dict so we can tag on extra stuff later
    return method


def provides_with(name=None, web_only=True, internal_only=True, **kwargs):
    """ Decorator which tags class methods so they can be detected as a provider of a Service.

        Use this instead of @provides when exposing a port with a custom name or to tag on additional flags.
    """
    PortArray.assert_valid_port_name(name)
    port_attrs = dict(web_only=web_only, internal_only=internal_only)
    port_attrs.update(kwargs)
    if name:
        assert isinstance(name, str)
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


class ServiceProviderMeta(ProviderMeta):
    """Object for tracking Provides port metadata. (FOR INTERNAL USE ONLY)."""
    def __init__(self, for_class):
        self._providers = {}
        self._flags = {}
        self._parent_class_name = for_class

    def register_provider(self, port_name, method_name, flags):
        if port_name in self._providers:
            raise PortDefinitionError('Duplicate providers for "{}" - {}.{} and {}.{}'.format(
                port_name,
                self._parent_class_name, method_name,
                self._parent_class_name, self._providers[port_name],
            ))

        self._providers[port_name] = method_name
        self._flags[port_name] = flags or {}

    def get_provides(self):
        return self._providers.keys()

    def get_port_provider(self, port_name):
        self._assert_valid_port_name(port_name)
        return PortProvider(resource=self, port_name=port_name)

    def get_provider_func(self, port_name):
        self._assert_valid_port_name(port_name)
        method_name = self._providers[port_name]
        return getattr(self, method_name)

    def get_port_flag(self, port_name, flag_name):
        self._assert_valid_port_name(port_name)
        return self._flags[port_name].get(flag_name, None)

    def get_port_flags(self, port_name):
        self._assert_valid_port_name(port_name)
        return self._flags[port_name].copy()  # return a shallow copy

    def _assert_valid_port_name(self, port_name):
        if port_name not in self._providers:
            raise WiringError('Port "{}" does not exist on {}'.format(port_name, self._parent_class_name))


class ServiceMetaclass(type):
    """ Metaclass that makes classes aware of @provides and ensures .deps and .meta is specified correctly."""
    def __new__(mcs, name, bases, state):

        mcs.validate_overridden_attributes(attrs=state, subclass_name=name)

        # walk attributes and register the ones that have been tagged by @provides
        meta = ServiceProviderMeta(for_class=name)
        for attr_name, member in state.iteritems():
            if hasattr(member, '__port_attributes__') and callable(member):
                port_name = member.__port_attributes__.get('with_name', attr_name)
                PortArray.assert_valid_port_name(port_name)
                meta.register_provider(port_name=port_name, method_name=attr_name, flags=member.__port_attributes__)

        # store resulting metadata in .meta of the created class
        state['meta'] = meta

        return type.__new__(mcs, name, bases, state)

    @classmethod
    def validate_overridden_attributes(mcs, attrs, subclass_name):

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

        conflicts = PortArray.RESERVED_NAMES.intersection(attrs)
        if conflicts:
            raise ServiceDefinitionError('Reserved attributes cannot be overridden - {}'.format(', '.join(conflicts)))


class Service(HasNeedsAndProvides):
    __metaclass__ = ServiceMetaclass

    # override in subclass to declare Needs ports. Must be set to an instance of octa.Needs
    deps = Needs([])


class ServiceGroup(HasNeedsAndProvides):
    pass  # TODO: implement me
