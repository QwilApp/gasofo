from unittest import TestCase

from gasofo.convenience import (
    func_as_provider,
    object_as_provider
)
from gasofo.discoverable import auto_wire
from gasofo.exceptions import (
    DisconnectedPort,
    UnknownPort, InvalidPortName, YouCannotDoThat
)
from gasofo.service import (
    Needs,
    Service,
    provides
)


class MyTestService(Service):
    deps = Needs(['external_dep'])

    @provides
    def call_me_maybe(self):
        return self.deps.external_dep()


class FuncAsProviderTest(TestCase):

    def test_connecting_service_to_a_lambda_converted_to_a_provider(self):
        service = MyTestService()
        dep_provider = func_as_provider(func=lambda: 'Lambada!', port='external_dep')

        # before wiring
        self.assertRaises(DisconnectedPort, service.call_me_maybe)

        # after wiring
        auto_wire([service, dep_provider])
        self.assertEqual('Lambada!', service.call_me_maybe())
        self.assertRaises(UnknownPort, dep_provider.get_provider_func, 'not_a_port')

    def test_connecting_service_to_a_func_converted_to_a_provider(self):

        def some_func():
            return 'yolo'

        service = MyTestService()
        dep_provider = func_as_provider(func=some_func, port='external_dep')

        # before wiring
        self.assertRaises(DisconnectedPort, service.call_me_maybe)

        # after wiring
        auto_wire([service, dep_provider])
        self.assertEqual('yolo', service.call_me_maybe())

    def test_connecting_service_to_a_classmethod_converted_to_a_provider(self):

        class Deppy(object):
            @classmethod
            def wowza(cls):
                return cls.__name__

        service = MyTestService()
        dep_provider = func_as_provider(func=Deppy.wowza, port='external_dep')

        # before wiring
        self.assertRaises(DisconnectedPort, service.call_me_maybe)

        # after wiring
        auto_wire([service, dep_provider])
        self.assertEqual('Deppy', service.call_me_maybe())

    def test_connecting_service_to_a_staticmethod_converted_to_a_provider(self):

        class Deppy(object):
            @staticmethod
            def wowza():
                return 'Kapow'

        service = MyTestService()
        dep_provider = func_as_provider(func=Deppy.wowza, port='external_dep')

        # before wiring
        self.assertRaises(DisconnectedPort, service.call_me_maybe)

        # after wiring
        auto_wire([service, dep_provider])
        self.assertEqual('Kapow', service.call_me_maybe())

    def test_connecting_service_to_a_bound_method_converted_to_a_provider(self):

        class Deppy(object):
            def wowza(self):
                return 'Kapow'

        service = MyTestService()
        dep_provider = func_as_provider(func=Deppy().wowza, port='external_dep')

        # before wiring
        self.assertRaises(DisconnectedPort, service.call_me_maybe)

        # after wiring
        auto_wire([service, dep_provider])
        self.assertEqual('Kapow', service.call_me_maybe())

    def test_func_wrappers_support_flag_queries_but_has_no_flags(self):
        provider = func_as_provider(func=lambda: 'Lambada!', port='blah')

        self.assertIsNone(provider.get_provider_flag('blah', 'whatev'))
        self.assertEqual({}, provider.get_provider_flags('blah'))

        self.assertRaises(UnknownPort, provider.get_provider_flag, 'not_a_port', 'whatev')
        self.assertRaises(UnknownPort, provider.get_provider_flags, 'not_a_port')

    def test_creating_wrapper_with_invalid_port_name(self):
        msg = '"9_not_va!id_port" does not have required format for port names'
        with self.assertRaisesRegexp(InvalidPortName, msg):
            func_as_provider(func=lambda: 'Lambada!', port='9_not_va!id_port')


class ObjectAsProviderTest(TestCase):

    def test_connecting_service_to_an_obj_converted_to_a_provider(self):

        class Regurgitator(object):
            def __init__(self, value):
                self.value = value

            def external_dep(self):
                return self.value

        service = MyTestService()
        provider = Regurgitator('kapow!')
        dep_provider = object_as_provider(provider=provider, ports=['external_dep'])

        # before wiring
        self.assertRaises(DisconnectedPort, service.call_me_maybe)

        # after wiring
        auto_wire([service, dep_provider])
        self.assertEqual('kapow!', service.call_me_maybe())

    def test_connecting_service_to_class_with_classmethod_converted_to_a_provider(self):

        class Deppy(object):
            @classmethod
            def external_dep(cls):
                return cls.__name__

        service = MyTestService()
        dep_provider = object_as_provider(provider=Deppy, ports=['external_dep'])

        # before wiring
        self.assertRaises(DisconnectedPort, service.call_me_maybe)

        # after wiring
        auto_wire([service, dep_provider])
        self.assertEqual('Deppy', service.call_me_maybe())

    def test_connecting_service_to_class_with_staticmethod_converted_to_a_provider(self):

        class Deppy(object):
            @staticmethod
            def external_dep():
                return 'Sassy'

        service = MyTestService()
        dep_provider = object_as_provider(provider=Deppy, ports=['external_dep'])

        # before wiring
        self.assertRaises(DisconnectedPort, service.call_me_maybe)

        # after wiring
        auto_wire([service, dep_provider])
        self.assertEqual('Sassy', service.call_me_maybe())

    def test_object_wrappers_support_flag_queries_but_has_no_flags(self):

        class Dumpty(object):
            @staticmethod
            def blah():
                return 'Sassy'

        provider = object_as_provider(provider=Dumpty, ports=['blah'])

        self.assertIsNone(provider.get_provider_flag('blah', 'whatev'))
        self.assertEqual({}, provider.get_provider_flags('blah'))

        self.assertRaises(UnknownPort, provider.get_provider_flag, 'not_a_port', 'whatev')
        self.assertRaises(UnknownPort, provider.get_provider_flags, 'not_a_port')

    def test_creating_wrapper_with_invalid_port_name(self):

        class Dumpty(object):
            @staticmethod
            def add_port():
                return 'Sassy'

        msg = '"add_port" is a reserved word and cannot be used as port name'
        with self.assertRaisesRegexp(InvalidPortName, msg):
            object_as_provider(provider=Dumpty, ports=['add_port'])

    def test_misc_edge_cases(self):

        class Dumpty(object):
            some_value = 100

            @staticmethod
            def my_port():
                return 'Sassy'

        obj = Dumpty()

        # Assert auto correction of ports being a str instead of a list of str
        provider = object_as_provider(provider=obj, ports='my_port')
        self.assertEqual(['my_port'], provider.get_provides())

        # Assert handles bad requests for port
        self.assertRaises(UnknownPort, provider.get_provider_func, 'not_a_port')

        # Assert exporting port_name that does not match object attr
        msg = '"not_my_port" is not an attribute of {}'.format(obj)
        with self.assertRaisesRegexp(YouCannotDoThat, msg):
            object_as_provider(provider=obj, ports=['my_port', 'not_my_port'])

        # Assert exporting port_name that matches non-callable attribute
        msg = '{}.some_value is not callable'.format(obj)
        with self.assertRaisesRegexp(YouCannotDoThat, msg):
            object_as_provider(provider=obj, ports=['my_port', 'some_value'])
