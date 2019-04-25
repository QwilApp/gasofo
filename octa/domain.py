import inspect
import logging
import types
import functools
from octa.exceptions import (
    DomainDefinitionError,
    WiringError
)
from octa.ports import (
    HasNeedsAndProvides,
    PortArray,
    PortProvider,
    ProviderMeta,
    auto_wire,
)
from octa.service import Service

__author__ = 'shawn'


logger = logging.getLogger(__name__)


class DomainProviderMeta(ProviderMeta):
    def __init__(self):
        self._providers = {}
        self._flags = {}

    def register_provider_service(self, port_name, service):
        assert port_name not in self._providers  # duplicates should have been trapped by DomainMetaclass
        self._providers[port_name] = service.meta.get_port_provider(port_name)
        self._flags[port_name] = service.meta.get_port_flags(port_name)

    def get_provides(self):
        return self._providers.keys()

    def get_port_provider(self, port_name):
        try:
            return self._providers[port_name]
        except KeyError:
            self._raise_missing_port(port_name)

    def get_provider_func(self, port_name):
        port_provider = self.get_port_provider(port_name)

        provider = port_provider.resource
        provider_port = port_provider.port_name
        return provider.meta.get_provider_func(port_name=provider_port)

    def get_port_flag(self, port_name, flag_name):
        try:
            return self._flags[port_name].get(flag_name, None)
        except KeyError:
            self._raise_missing_port(port_name)

    def get_port_flags(self, port_name):
        try:
            return self._flags[port_name].copy()  # return a shallow copy
        except KeyError:
            self._raise_missing_port(port_name)

    def _raise_missing_port(self, port_name):
        raise WiringError('Port "{}" does not exist on {}'.format(port_name, self._parent_class_name))


class DomainDepsProviderMeta(ProviderMeta):
    def __init__(self, parent):
        self.parent = parent

    def get_provides(self):
        return self.parent.get_needs()

    def get_port_provider(self, port_name):
        return PortProvider(resource=self.parent, port_name=port_name)

    def get_provider_func(self, port_name):
        return getattr(self.parent, port_name)

    def get_port_flag(self, port_name, flag_name):
        return None

    def get_port_flags(self, port_name):
        return {}


class DomainDeps(PortArray):
    # Since this serves as a proxy for service needs and external providers, it will essentially
    # have needs as well as provides
    def __init__(self, needs):
        super(DomainDeps, self).__init__()
        for port in needs:
            self.add_port(port)
        self.meta = DomainDepsProviderMeta(parent=self)


class DomainMetaclass(type):

    def __new__(mcs, name, bases, state):
        if '__services__' not in state or not isinstance(state['__services__'], (list, tuple)):
            raise DomainDefinitionError('{}.__services__ must be defined with a list of Service classes'.format(name))
        else:
            services = state['__services__']
            for service_class in services:
                mcs._assert_valid_service_class(name, service_class)

        needs = mcs._gather_needs(services)
        provides = mcs._gather_provides(services)

        if '__provides__' not in state or not isinstance(state['__provides__'], (list, tuple)):
            raise DomainDefinitionError('{}.__provides__ must be defined with a list of Service classes'.format(name))
        else:
            for port_name in state['__provides__']:
                if port_name not in provides:
                    raise DomainDefinitionError(
                        '"{}" listed in {}.__provides__ is not provided by any of the services'.format(port_name, name))

        # wire up inter-service dependencies
        wired = auto_wire(consumers=services, producers=services, raise_if_needs_unsatisfied=False, assign_only=True)

        # any unsatisfied needs are exposed as needs of the Domain
        unwired_needs_ports = set(needs.keys()).difference(wired)
        domain_deps = DomainDeps(unwired_needs_ports)
        state['deps'] = domain_deps
        # .. then hooked up to the services that needs them
        for port in unwired_needs_ports:
            for service in needs[port]:
                service.deps.assign_port_provider(port_name=port, provider=domain_deps, provider_port_name=port)

        # expose Provides ports and wire up to the providing service
        meta = DomainProviderMeta()
        for port_name in state['__provides__']:
            service = provides[port_name]
            meta.register_provider_service(port_name=port_name, service=service)
        state['meta'] = meta

        return type.__new__(mcs, name, bases, state)

    @classmethod
    def _assert_valid_service_class(mcs, name, service_class):
        if not inspect.isclass(service_class):
            raise DomainDefinitionError('{}.__services__ should contain service classes not instances. Got {}'.format(
                name,
                service_class,
            ))
        if not issubclass(service_class, Service):
            raise DomainDefinitionError('{}.__services__ should contain only subclasses of {}.Service'.format(
                name,
                Service.__module__
            ))

    @classmethod
    def _gather_needs(mcs, service_classes):
        gathered = {}
        for service_class in service_classes:
            for need in service_class.get_needs():
                gathered.setdefault(need, []).append(service_class)
        return gathered

    @classmethod
    def _gather_provides(mcs, service_classes):
        gathered = {}
        for service_class in service_classes:
            for provide in service_class.get_provides():
                if provide in gathered:
                    raise DomainDefinitionError('Duplicate providers. Both {} and {} provide "{}"'.format(
                        gathered[provide].__name__,
                        service_class.__name__,
                        provide
                    ))
                gathered[provide] = service_class
        return gathered


class VirtualToConcreteConnectionAdapter(object):
    def __init__(self, class_to_instance_mapper):
        self._mapper = class_to_instance_mapper

    def __call__(self, provider, port_name):
        if inspect.isclass(provider):
            try:
                provider_object = self._mapper[provider]
            except KeyError:
                raise WiringError('Unmapped provider class - {}'.format(provider))
        else:
            provider_object = provider
        return provider_object.meta.get_provider_func(port_name=port_name)


class Domain(HasNeedsAndProvides, PortArray):
    __metaclass__ = DomainMetaclass
    __services__ = ()  # must be overridden in subclass to define list of services within this domain
    __provides__ = ()  # must be overridden to expose ports that this domain provides

    def __init__(self):
        super(Domain, self).__init__()
        self._service_map = self._instantiate_and_map_services()
        self._materialise_connections(self._service_map)

    def _instantiate_and_map_services(self):
        mapper = {service_class: service_class() for service_class in self.__services__}
        return mapper

    def _materialise_connections(self, service_map):
        mapper = {self.__class__: self}  # need to include Domain since some Services exposes needs to domain level
        mapper.update(service_map)
        virtual_to_concrete = VirtualToConcreteConnectionAdapter(mapper)

        for service in service_map.itervalues():
            for port in service.get_needs():
                service.deps.connect_assigned_port(port_name=port, with_adapter=virtual_to_concrete)

        for port in self.get_provides():
            self._ports.add(port)
            provider = self.meta.get_port_provider(port)
            target_object = mapper[provider.resource]
            target_func = getattr(target_object, provider.port_name)

            @functools.wraps(target_func)
            def unbound_method(_, *args, **kwargs):
                return target_func(*args, **kwargs)

            method = types.MethodType(unbound_method, self)
            setattr(self, port, method)
