import inspect
import re
from functools import wraps

from gasofo.discoverable import (
    AutoDiscoverConnections,
    INeed,
    IProvide,
    wire_up_discovered_connections,
)
from gasofo.exceptions import (
    DomainDefinitionError,
    InconsistentInterface,
    UnknownPort,
)
from gasofo.ports import (
    PortArray,
    ShadowPortArray,
)
from gasofo.service import (
    ProviderMetadata,
    Service,
    get_template_funcs,
    unknown_interface,
)

__author__ = 'shawn'

GENERIC_ARGSPEC = inspect.getargspec(unknown_interface)


class DomainProviderMetadata(ProviderMetadata):

    def __init__(self):
        super(DomainProviderMetadata, self).__init__()
        self.ports = None  # only set for instance metadata

    def register_provider(self, port_name, service, flags):
        super(DomainProviderMetadata, self).register_provider(
            port_name=port_name,
            provider_ref=service,
            flags=flags,
        )

    def get_provider_method_name(self, port_name):
        if port_name not in self.get_provides():
            raise UnknownPort('"{}" is not a valid port'.format(port_name))
        else:
            return port_name

    def get_provider(self, port_name):
        try:
            return self._providers[port_name]
        except KeyError:
            raise UnknownPort('"{}" is not a valid port'.format(port_name))

    def get_instance_metadata(self, service_map):
        clone = self.__class__()
        clone.ports = PortArray()

        for port in self.get_provides():
            provider_class = self.get_provider(port)
            provider_instance = service_map[provider_class]
            provider_flags = provider_instance.get_provider_flags(port_name=port)

            provider_func = provider_instance.get_provider_func(port_name=port)
            clone.register_provider(port_name=port, service=provider_instance, flags=provider_flags)

            # create and connect ports
            clone.ports.add_port(port_name=port)
            clone.ports.connect_port(port_name=port, func=provider_func)
        return clone


def generate_domain_method(port_name, provider):
    # We can't use get_provider_func here since we're operating on service classes.
    # - we don't need the bound method, here. We just want a ref to the method so we can pull docstrings etc.
    provider_method_name = provider.meta.get_provider_method_name(port_name=port_name)
    provider_func = getattr(provider, provider_method_name)

    # TODO: inherit argspec from service ports. (and what can we do about type hints?)
    @wraps(provider_func)
    def generated(self, *args, **kwargs):
        port = getattr(self.meta.ports, port_name)
        return port(*args, **kwargs)

    # generated.__doc__ = provider_func.__doc__
    generated.__name__ = port_name
    return generated


class AutoProvide(object):

    def __init__(self, pattern=None):
        self.matcher = re.compile(pattern) if pattern else None

    def filter(self, port_names):
        return [port for port in port_names if self.acceptable_port_name(port)]

    def acceptable_port_name(self, port_name):
        if not self.matcher:
            return True
        else:
            return bool(self.matcher.match(port_name))


class DomainMetaclass(type):

    def __new__(mcs, name, bases, state):
        if bases == (INeed, IProvide):  # This is the Domain class itself, not its subclass
            return type.__new__(mcs, name, bases, state)

        mcs.validate_overridden_attributes(attrs=state, class_name=name)

        if '__services__' not in state or not isinstance(state['__services__'], (list, tuple)):
            raise DomainDefinitionError('{}.__services__ must be defined with a list of component classes'.format(name))
        else:
            service_classes = state['__services__']
            for service_class in service_classes:
                mcs._assert_is_compatible_class(name, service_class)

        discovered = AutoDiscoverConnections(service_classes)
        provides = state.get('__provides__', None)

        if provides is None or not isinstance(provides, (list, tuple, AutoProvide)):
            raise DomainDefinitionError('{}.__provides__ must be defined with a list of port names'.format(name))
        else:
            if isinstance(provides, AutoProvide):  # auto-discover provides ports
                auto_provider = provides
                provides_ports = auto_provider.filter(discovered.get_provides())
            else:
                for port_name in provides:
                    if port_name not in discovered.get_provides():
                        msg = '"{}" listed in {}.__provides__ is not provided by any of the services'.format(
                            port_name,
                            name,
                        )
                        raise DomainDefinitionError(msg)
                provides_ports = provides

        # all unsatisfied deps are exposed as dependencies of the domain
        state['deps'] = deps = PortArray()
        for port_name in discovered.unsatisfied_needs():
            deps.add_port(port_name)

        # make a shadow copy of template_funcs. Used mainly for tracking intended interfaces for ports so we can
        # use for validation during testing. At some point we might use this for wiring-time checks too to ensure
        # compatibility between ports.
        deps._needs_template_funcs = template_funcs = {}
        for port in deps.get_ports():
            template_func = mcs._assert_providers_compatible_and_extract_template_func(
                providers=discovered._needs[port],
                port_name=port,
            )
            template_funcs[port] = template_func

        # declared 'provides' ports are registered and entry points created
        state['meta'] = meta = DomainProviderMetadata()
        for port in provides_ports:
            provider = discovered.get_provider(port_name=port)

            if not issubclass(provider, (Service, Domain)):
                msg = 'Port of non-service class ({}.{}) cannot be published on the domain'.format(
                    provider.__name__,
                    port
                )
                raise DomainDefinitionError(msg)

            inherited_flags = provider.get_provider_flags(port)
            inherited_flags.pop('with_name', None)  # don't inherit name-change flags
            meta.register_provider(port_name=port, service=provider, flags=inherited_flags)
            state[port] = generate_domain_method(port_name=port, provider=provider)

        return type.__new__(mcs, name, bases, state)

    @classmethod
    def _assert_is_compatible_class(mcs, name, service_class):
        if not inspect.isclass(service_class):
            raise DomainDefinitionError('{}.__services__ should contain component classes not instances. Got {}'.format(
                name,
                service_class,
            ))
        if not issubclass(service_class, IProvide):
            msg = 'Component classes defined in {}.__services__ should be subclasses of IProvide. '
            msg += 'Instead, got class {} with class hierarchy "{}"'
            raise DomainDefinitionError(msg.format(
                name,
                service_class.__name__,
                ' -> '.join(c.__name__ for c in service_class.__mro__))
            )

    @classmethod
    def validate_overridden_attributes(mcs, attrs, class_name):
        if '__init__' in attrs:
            raise DomainDefinitionError('{} has custom constructor which is not allowed for Domains'.format(class_name))

        allowed_attrs = {'__provides__', '__services__'}
        non_underscored_attrs = (attr for attr in attrs if not attr.startswith('_'))
        bad_attrs = [attr for attr in non_underscored_attrs if attr not in allowed_attrs]
        if bad_attrs:
            raise DomainDefinitionError((
                'Domains cannot be defined with custom methods or attributes. '
                'Found {} defined on {}'
            ).format(', '.join(bad_attrs), class_name))

    @staticmethod
    def _assert_providers_compatible_and_extract_template_func(providers, port_name):
        assert providers, 'why are you calling me if there are no providers for {}?'.format(port_name)

        func_map = {}
        spec_map = {}

        for provider in providers:
            func_map[provider] = func = get_template_funcs(provider)[port_name]
            spec_map[provider] = inspect.getargspec(func)

        non_generic_specs = {provider: spec for provider, spec in spec_map.iteritems() if spec != GENERIC_ARGSPEC}

        if not non_generic_specs:  # all needs of this port did not specific an interface
            return func_map.itervalues().next()  # just return the first one

        specs = non_generic_specs.values()
        if not all(spec == specs[0] for spec in specs):  # we have a mixture of specs
            msg = 'The following components all need "{}" but expect different interfaces - {}'.format(
                port_name,
                ', '.join(sorted(p.__name__ for p in non_generic_specs.iterkeys()))
            )
            raise InconsistentInterface(msg)
        else:
            chosen_one = non_generic_specs.iterkeys().next()
            return func_map[chosen_one]


class Domain(INeed, IProvide):
    """
        @DynamicAttrs <-- let pycharm know to expect dynamically added attributes
    """
    __metaclass__ = DomainMetaclass
    __services__ = ()  # must be overridden in subclass to define list of services within this domain
    __provides__ = ()  # must be overridden to expose ports that this domain provides

    def __init__(self):
        super(Domain, self).__init__()
        self._service_map = service_map = self._instantiate_and_map_services()

        # replace 'meta' with a variant for the instance (don't share self.__class__.meta)
        self.meta = self.__class__.meta.get_instance_metadata(service_map=service_map)

        # replace 'deps' with a ShadowPortArray which serves as proxy to the deps of internal services
        components = service_map.values()
        component_deps = [c.deps for c in components if isinstance(getattr(c, 'deps', None), (PortArray, ShadowPortArray))]
        discovered = AutoDiscoverConnections(components=components)
        self.deps = ShadowPortArray(arrays=component_deps, ignore_ports=discovered.satisfied_needs())

        # materialize connections between services
        wire_up_discovered_connections(discovered=discovered)

    def _instantiate_and_map_services(self):
        mapper = {service_class: service_class() for service_class in self.__services__}
        return mapper

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
        provider = self.meta.get_provider(port_name=port_name)
        provider_func = provider.get_provider_func(port_name=port_name)
        return provider_func

    @classmethod
    def get_provider_flag(cls, port_name, flag_name):
        return cls.meta.get_provider_flag(port_name, flag_name)

    @classmethod
    def get_provider_flags(cls, port_name):
        return cls.meta.get_provider_flags(port_name)
