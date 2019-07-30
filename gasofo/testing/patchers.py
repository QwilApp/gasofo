import mock

from gasofo import Service
from gasofo.exceptions import (
    DisconnectedPort,
    IncompatibleProvider,
    UnknownPort,
)


def patch_port(component, port_name):
    """ Patches all needs ports of the given name in the component (domain or service) and its children.

    Use this as a context manager as such:

        with patch_port(my_connected_app, 'port_x') as mock_port_x:
            mock_port_x.return_value = 100
            my_connected_app.do_something()

    Or by instantiating the patcher and manually starting/stopping it:

        class MyTestCase(TestCase):
            def setUp(self):
                patcher = patch_port(my_connected_app, 'port_x')
                self.mock_port_x = patcher.start()
                self.addCleanup(patcher.stop)

    Note that multiple needs ports may be end up connected to the mock provider. All the targeted needs ports must
    be connected to the same provider or an exception is raised.

    The mock object will be create with the spec_set of the connected provider.
    """
    return PortPatcher(component=component, port_name=port_name)


def wrap_port(component, port_name):
    """ Like `patch_port`, but calls to the mock object are passed through to the actual provider.

    However, if return_value is set on the mock object then calls are not passed to the wrapped provider and the
    `return_value` is returned instead. This would effectively then behave just like `patch_port`.

    Use this as a context manager as such:

        with wrap_port(my_connected_app, 'port_x') as wrapped_port_x:
            my_connected_app.do_something()
            wrapped_port_x.assert_called()

    Or by instantiating the patcher and manually starting/stopping it:

        class MyTestCase(TestCase):
            def setUp(self):
                patcher = wrap_port(my_connected_app, 'port_x')
                self.wrapped_port_x = patcher.start()
                self.addCleanup(patcher.stop)

    Note that multiple needs ports may be end up connected to the mock provider. All the targeted needs ports must
    be connected to the same provider or an exception is raised.

    """
    return PortPatcher(component=component, port_name=port_name, wraps_provider=True)


class PortPatcher(object):
    def __init__(self, component, port_name, wraps_provider=False):
        self.component = component
        self.port_name = port_name
        self.wraps_provider = wraps_provider
        self._patches = []
        self.is_started = False

        targets = self._find_services_that_needs_port(component=component, port_name=port_name)
        if not targets:
            raise UnknownPort('Could not find instances of port "{}"'.format(port_name))

        self.provider = self._get_common_provider(services=targets, port_name=port_name)
        self.targets = targets

    def start(self):
        if self.is_started:
            raise RuntimeError('patch already started')

        wrapped = self.provider if self.wraps_provider else None
        mock_provider = mock.Mock(spec_set=self.provider, wraps=wrapped)
        self._patches = [mock.patch.object(service.deps, self.port_name, mock_provider) for service in self.targets]
        for patcher in self._patches:
            patcher.start()

        self.is_started = True
        return mock_provider

    def stop(self):
        if not self.is_started:
            raise RuntimeError('patcher not yet started')
        for patcher in self._patches:
            patcher.stop()

        self._patches = None
        self.is_started = True

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.stop()
        return False

    def _find_services_that_needs_port(self, component, port_name):
        if isinstance(component, Service) and port_name in component.get_needs():
            return [component]

        found = []
        service_map = getattr(component, '_service_map', {})
        for child_instance in service_map.itervalues():
            found.extend(self._find_services_that_needs_port(component=child_instance, port_name=port_name))

        return found

    @staticmethod
    def _get_common_provider(services, port_name):
        provider = None
        for service in services:
            if service.deps.is_disconnected_port(port_name):
                raise DisconnectedPort(
                    '{}.{} is disconnected'.format(service.__class__.__name__, port_name))

            # get a reference to the needs provided and assert that all needers have same provider
            port_method = getattr(service.deps, port_name)
            assert callable(port_method)  # ports always callable unless some is really messed up
            if provider is not None and provider != port_method:
                raise IncompatibleProvider(
                    'Not all "{}" ports are provided by the same provider'.format(port_name))
            provider = port_method

        return provider
