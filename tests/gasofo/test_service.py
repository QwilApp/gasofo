import inspect
from unittest import TestCase

from gasofo.exceptions import (
    DuplicatePortDefinition,
    DuplicateProviders,
    InvalidPortName,
    ServiceDefinitionError,
    UnknownPort,
    UnusedPort,
)
from gasofo.service import (
    Service,
    get_template_funcs,
    provides,
    provides_with,
)
from gasofo.service_needs import (
    Needs,
    NeedsInterface,
)


class ServiceDefinitionTest(TestCase):

    def test_defining_empty_service(self):

        class EmptyService(Service):
            pass

        self.assertEqual([], EmptyService.get_needs())
        self.assertEqual([], EmptyService.get_provides())

        service = EmptyService()
        self.assertEqual([], service.get_needs())
        self.assertEqual([], service.get_provides())

    def test_service_with_needs_and_provides(self):

        class MyService(Service):
            deps = Needs(['stuff'])

            @provides
            def provider_a(self):
                return self.deps.stuff()

        self.assertEqual(['stuff'], MyService.get_needs())
        self.assertEqual(['provider_a'], MyService.get_provides())

        service = MyService()
        self.assertEqual(['stuff'], service.get_needs())
        self.assertEqual(['provider_a'], service.get_provides())

    def test_needs_defined_with_str_rather_than_list_is_autocorrected(self):
        class MyService(Service):
            deps = Needs('stuff')

            @provides
            def provider_a(self):
                return self.deps.stuff()

        self.assertEqual(['stuff'], MyService.get_needs())

    def test_service_definition_with_duplicate_provides_ports_raises_DuplicateProviders(self):

        with self.assertRaisesRegexp(DuplicateProviders, 'Duplicate providers for "provider_a"'):
            class MyService(Service):

                @provides
                def provider_a(self):
                    return 'A'

                @provides_with(name='provider_a')
                def another_provider(self):
                    return 'X'

    def test_service_definition_with_duplicate_needs_raises_DuplicatePortDefinition(self):

        with self.assertRaisesRegexp(DuplicatePortDefinition, '"stuff" port is duplicated'):
            class MyService(Service):
                deps = Needs(['stuff', 'more_stuff', 'stuff'])

    def test_service_with_unused_deps_raises_ServiceDefinitionError(self):

        with self.assertRaisesRegexp(UnusedPort, 'MyService has unused Needs - fluff'):
            class MyService(Service):
                deps = Needs(['stuff', 'fluff'])

                @provides
                def provider_a(self):
                    return self.deps.stuff()

    def test_service_deps_usage_analysis_also_takes_into_account_internal_methods(self):

        class MyService(Service):  # Should not raise
            deps = Needs(['stuff', 'fluff'])

            @provides
            def provider_a(self):
                return self.deps.stuff() + self._fluff()

            def _fluff(self):
                return self.deps.fluff()

    def test_service_deps_usage_analysis_does_not_take_into_account_comments(self):

        class MyService(Service):  # Should not raise
            deps = Needs(['stuff'])

            @provides
            def provider_a(self):
                return self.deps.stuff() + self._fluff()

            def _fluff(self):
                # intentional comments. do not remove.
                # self.deps.fluff()
                return 10  # + self.deps.gruff()

    def test_service_with_multiple_unused_deps(self):

        with self.assertRaisesRegexp(UnusedPort, 'MyService has unused Needs - acorn, fluff'):
            class MyService(Service):
                deps = Needs(['stuff', 'fluff', 'acorn'])

                @provides
                def provider_a(self):
                    return self.deps.stuff()

    def test_invalid_provides_port_name_raises_InvalidPortName(self):

        with self.assertRaisesRegexp(InvalidPortName, '"9_bad_port_name" does not have required format for port names'):
            class MyService(Service):
                @provides_with('9_bad_port_name')
                def provider(self):
                    return False

    def test_invalid_needs_port_name_raises_InvalidPortName(self):

        with self.assertRaisesRegexp(InvalidPortName, '"9_bad_port_name" does not have required format for port names'):
            class MyService(Service):
                deps = Needs(['9_bad_port_name'])

    def test_port_name_matching_reserved_names_raises_InvalidPortName(self):

        with self.assertRaisesRegexp(InvalidPortName, '"get_needs" is a reserved word and cannot be used as port name'):
            class MyService(Service):
                deps = Needs(['get_needs'])

    def test_reference_to_undeclared_deps_raises_UnknownPort(self):

        with self.assertRaisesRegexp(UnknownPort, 'MyService.provider_a references undeclared Needs - not_a_port'):
            class MyService(Service):

                @provides
                def provider_a(self):
                    return self.deps.not_a_port()

    def test_multiple_references_to_undeclared_deps(self):

        with self.assertRaisesRegexp(UnknownPort, 'MyService.provider_a references undeclared Needs - abc, not_a_port'):
            class MyService(Service):

                @provides
                def provider_a(self):
                    return self.deps.not_a_port(), self.deps.not_a_port(), self.deps.abc()

    def test_constructor_not_allowed_for_services(self):
        msg = 'To emphasize statelessness, MyService should not define __init__'
        with self.assertRaisesRegexp(ServiceDefinitionError, msg):
            class MyService(Service):
                def __init__(self):
                    super(MyService, self).__init__()


class ServiceProvidesTest(TestCase):

    def test_querying_provides_ports_on_service_class_and_instance(self):

        class MyService(Service):
            @provides
            def provider_a(self):
                return 'A'

        self.assertItemsEqual(['provider_a'], MyService.get_provides())
        self.assertItemsEqual(['provider_a'], MyService().get_provides())

    def test_querying_provides_ports_with_custom_name_on_service_class_and_instance(self):

        class MyService(Service):
            @provides
            def provider_a(self):
                return 'A'

            @provides_with(name='provider_b')
            def another_provider(self):
                return 'B'

        self.assertItemsEqual(['provider_a', 'provider_b'], MyService.get_provides())
        self.assertItemsEqual(['provider_a', 'provider_b'], MyService().get_provides())

    def test_getting_provider_func_from_service_instance(self):

        class MyService(Service):
            @provides
            def provider_a(self):
                return 'A'

            @provides_with(name='provider_b')
            def another_provider(self):
                return 'B'

        service = MyService()
        self.assertEqual('A', service.get_provider_func('provider_a')())
        self.assertEqual('B', service.get_provider_func('provider_b')())

    def test_calling_get_provider_func_on_service_class_raises_TypeError(self):

        class MyService(Service):
            @provides
            def provider_a(self):
                return 'A'

        with self.assertRaisesRegexp(TypeError, 'unbound method .+ must be called with MyService instance .*'):
            MyService.get_provider_func('provider_a')

    def test_getting_provider_func_with_invalid_port_name_raises_UnknownPort(self):

        class MyService(Service):
            @provides
            def provider_a(self):
                return 'A'

        service = MyService()
        with self.assertRaisesRegexp(UnknownPort, '"unknown_port" is not a valid port'):
            service.get_provider_func('unknown_port')

    def test_getting_provider_flags_on_port_with_no_flags(self):

        class MyService(Service):
            @provides
            def provider_a(self):
                return 'A'

        expected_flags = {}
        self.assertEqual(expected_flags, MyService.get_provider_flags('provider_a'))
        self.assertEqual(expected_flags, MyService().get_provider_flags('provider_a'))

    def test_getting_provider_flags_on_port_with_custom_name_but_no_flags(self):

        class MyService(Service):
            @provides_with(name='provider_b')
            def another_provider(self):
                return 'B'

        expected_flags = {'with_name': 'provider_b'}
        self.assertEqual(expected_flags, MyService.get_provider_flags('provider_b'))
        self.assertEqual(expected_flags, MyService().get_provider_flags('provider_b'))

    def test_getting_provider_flags_on_port_with_custom_name_and_flags(self):

        class MyService(Service):
            @provides_with(name='provider_b', web_only=True)
            def another_provider(self):
                return 'B'

        expected_flags = {'with_name': 'provider_b', 'web_only': True}
        self.assertEqual(expected_flags, MyService.get_provider_flags('provider_b'))
        self.assertEqual(expected_flags, MyService().get_provider_flags('provider_b'))

    def test_querying_a_specific_provider_flag(self):

        class MyService(Service):
            @provides_with(name='provider_b', some_flag='flag_value')
            def another_provider(self):
                return 'B'

        self.assertEqual('flag_value', MyService.get_provider_flag('provider_b', 'some_flag'))
        self.assertEqual('flag_value', MyService().get_provider_flag('provider_b', 'some_flag'))

    def test_querying_provider_flag_that_does_not_exist(self):

        class MyService(Service):
            @provides
            def provider_a(self):
                return 'A'

            @provides_with(name='provider_b', some_flag='flag_value')
            def another_provider(self):
                return 'B'

        self.assertIsNone(MyService.get_provider_flag('provider_a', 'unknown_flag'))
        self.assertIsNone(MyService().get_provider_flag('provider_a', 'unknown_flag'))
        self.assertIsNone(MyService.get_provider_flag('provider_b', 'unknown_flag'))
        self.assertIsNone(MyService().get_provider_flag('provider_b', 'unknown_flag'))

    def test_getting_provider_flags_on_port_that_does_not_exist(self):

        class MyService(Service):
            @provides_with(name='provider_b', some_flag='flag_value')
            def another_provider(self):
                return 'B'

        with self.assertRaisesRegexp(UnknownPort, '"not_a_valid_port" is not a valid port'):
            MyService.get_provider_flags('not_a_valid_port')

        with self.assertRaisesRegexp(UnknownPort, '"not_a_valid_port" is not a valid port'):
            MyService().get_provider_flags('not_a_valid_port')

    def test_querying_provider_flag_on_port_that_does_not_exist(self):

        class MyService(Service):
            @provides_with(name='provider_b', some_flag='flag_value')
            def another_provider(self):
                return 'B'

        with self.assertRaisesRegexp(UnknownPort, '"not_a_valid_port" is not a valid port'):
            MyService.get_provider_flag('not_a_valid_port', 'some_flag')

        with self.assertRaisesRegexp(UnknownPort, '"not_a_valid_port" is not a valid port'):
            MyService().get_provider_flag('not_a_valid_port', 'some_flag')

    def test_setting_deps_to_anything_other_than_Needs_raises_ServiceDeclarationError(self):

        with self.assertRaisesRegexp(ServiceDefinitionError, 'Yolo.deps must be an instance of gasofo.Needs'):
            class Yolo(Service):
                deps = ['a']

    def test_overriding_meta_in_Service_raises_ServiceDeclarationError(self):
        msg = '"meta" is a reserved attributes and should not be overridden'
        with self.assertRaisesRegexp(ServiceDefinitionError, msg):
            class Yolo(Service):
                meta = None


class ServiceTemplateFuncTest(TestCase):
    """
    These tests ensures that _get_template_funcs() works correctly. This feature is not used in 'production' usage
    and only by the test framework to assert ports are called with expected args/kwargs.

    In other words, this is a test of a feature used only by the test utility to test actual usage.
    """

    def test_needs_defined_using_Needs_class_has_template_funcs_with_correct_argspec(self):
        class MyService(Service):
            deps = Needs(ports=['a', 'b'])

            @provides
            def x(self):
                return self.deps.a() + self.deps.b()

        service = MyService()
        template_funcs = get_template_funcs(service=service)
        self.assertItemsEqual(['a', 'b'], template_funcs.keys())

        def expected_template(self, *args, **kwargs):
            pass

        self.assert_has_same_argspec(expected_template, template_funcs['a'])
        self.assert_has_same_argspec(expected_template, template_funcs['b'])

    def test_needs_defined_using_NeedsInterface_class_has_templte_funcs_with_correct_argspec(self):

        class MyDeps(NeedsInterface):
            def a(self, x, y=123): pass
            def b(self, x, **kwargs): pass
            def c(self, *args, **kwargs): pass

        class MyService(Service):
            deps = MyDeps()

            @provides
            def x(self):
                return self.deps.a() + self.deps.b() + self.deps.c()

        service = MyService()
        template_funcs = get_template_funcs(service=service)
        self.assertItemsEqual(['a', 'b', 'c'], template_funcs.keys())

        self.assert_has_same_argspec(lambda self, x, y=123: None, template_funcs['a'])
        self.assert_has_same_argspec(lambda self, x, **kwargs: None, template_funcs['b'])
        self.assert_has_same_argspec(lambda self, *args, **kwargs: None, template_funcs['c'])

    def test_default_template_func_is_consistent_and_has_wildcard_specs_but_not_callable(self):
        class MyService(Service):
            deps = Needs(ports=['a', 'b'])

            @provides
            def x(self):
                return self.deps.a() + self.deps.b()

        service = MyService()
        template_funcs = get_template_funcs(service=service)

        func = template_funcs['a']
        self.assertIs(func, template_funcs['b'])
        self.assert_has_same_argspec(lambda self, *args, **kwargs: None, func)
        self.assertRaises(NotImplementedError, func, None)  # template func meant as unbound methods so expects a 'self'

    def assert_has_same_argspec(self, func1, func2):
        self.assertEqual(inspect.getargspec(func=func1), inspect.getargspec(func=func2))
