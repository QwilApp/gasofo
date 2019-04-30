from unittest import TestCase

from gasofo.discoverable import IProvide
from gasofo.domain import Domain
from gasofo.discoverable import auto_wire
from gasofo.exceptions import (
    DisconnectedPort,
    DomainDefinitionError,
    UnknownPort
)
from gasofo.service import (
    Needs,
    Service,
    provides, provides_with
)


class DomainDefinitionTest(TestCase):

    def test_empty_domain(self):

        class EmptyDomain(Domain):
            __services__ = ()
            __provides__ = ()

        self.assertEqual([], EmptyDomain.get_needs())
        self.assertEqual([], EmptyDomain.get_provides())
        self.assertEqual([], EmptyDomain().get_needs())
        self.assertEqual([], EmptyDomain().get_provides())

    def test_domain_attributes_must_be_a_list_or_tuple(self):

        class OK(Domain):
            __services__ = ()
            __provides__ = ()

        class StillOK(Domain):
            __services__ = []
            __provides__ = []

        msg = 'NotOK.__services__ must be defined with a list of component classes'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class NotOK(Domain):
                __services__ = None
                __provides__ = []

        msg = 'AlsoNotOK.__provides__ must be defined with a list of port names'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class AlsoNotOK(Domain):
                __services__ = []
                __provides__ = None

    def test_simple_domain_with_provides_but_no_needs(self):

        class SimpleService(Service):
            @provides
            def bark(self):
                return 'woof'

        class SimpleDomain(Domain):
            __services__ = [SimpleService]
            __provides__ = ['bark']

        self.assertEqual([], SimpleDomain.get_needs())
        self.assertEqual(['bark'], SimpleDomain.get_provides())

        domain = SimpleDomain()
        self.assertEqual([], domain.get_needs())
        self.assertEqual(['bark'], domain.get_provides())
        self.assertEqual('woof', domain.bark())

    def test_domain_provides_must_match_port_of_internal_services(self):

        class SimpleService(Service):
            @provides
            def bark(self):
                return 'woof'

        msg = '"meow" listed in SimpleDomain.__provides__ is not provided by any of the services'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class SimpleDomain(Domain):
                __services__ = [SimpleService]
                __provides__ = ['meow']

    def test_simple_domain_with_needs_and_provides(self):

        class SimpleService(Service):
            deps = Needs('some_number')

            @provides
            def multiplied_number(self):
                return self.deps.some_number() * 100

        class SimpleDomain(Domain):
            __services__ = [SimpleService]
            __provides__ = ['multiplied_number']

        self.assertEqual(['some_number'], SimpleDomain.get_needs())
        self.assertEqual(['multiplied_number'], SimpleDomain.get_provides())

        domain = SimpleDomain()
        self.assertEqual(['some_number'], domain.get_needs())
        self.assertEqual(['multiplied_number'], domain.get_provides())

        with self.assertRaisesRegexp(DisconnectedPort, 'Port "some_number" has not been connected'):
            domain.multiplied_number()

    def test_domain_cannot_have_custom_constructor(self):
        msg = 'BadDomain has custom constructor which is not allowed for Domains'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class BadDomain(Domain):
                __services__ = ()
                __provides__ = ()

                def __init__(self):
                    super(BadDomain, self).__init__()

    def test_domain_cannot_have_custom_methods(self):
        msg = 'Domains cannot be defined with custom methods or attributes. Found do_something defined on BadDomain'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class BadDomain(Domain):
                __services__ = ()
                __provides__ = ()

                def do_something(self):
                    return 'nope'

    def test_domain_cannot_have_custom_attributes(self):
        msg = 'Domains cannot be defined with custom methods or attributes. Found meta defined on BadDomain'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class BadDomain(Domain):
                __services__ = ()
                __provides__ = ()
                meta = None

    def test_domain_ports_inherit_docs_from_underlying_port(self):
        class SimpleService(Service):
            @provides
            def bark(self):
                """Barks when you poke it with a stick."""
                return 'woof'

        class SimpleDomain(Domain):
            __services__ = [SimpleService]
            __provides__ = ['bark']

        self.assertEqual('Barks when you poke it with a stick.', SimpleDomain.bark.__doc__)

    def test_domain_with_no_service_definition_raises_DomainDefinitionError(self):
        msg = 'BadDomain.__services__ must be defined with a list of component classes'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class BadDomain(Domain):
                __provides__ = ['empty_promises']

    def test_domain_which_specifies_invalid_service_classes_raises_DomainDefinitionError(self):

        class Useless(object):
            pass

        msg = 'Component classes defined in BadDomain.__services__ should inherit be subclass of IProvide'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class BadDomain(Domain):
                __services__ = [Useless]

    def test_domain_which_specifies_service_instances_instead_of_class_raises_DomainDefinitionError(self):

        class ValidService(Service):
            pass

        class GoodButUselessDomain(Domain):  # Should not raise
            __services__ = [ValidService]
            __provides__ = []

        msg = 'BadDomain.__services__ should contain component classes not instances..*'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class BadDomain(Domain):
                __services__ = [ValidService()]

    def test_IProvide_classes_can_be_added_to_domain_but_not_have_its_port_exported(self):

        class StaticProvider(IProvide):

            def number(self):
                return 3

            @classmethod
            def get_provides(cls):
                return ['number']

            @classmethod
            def get_provider_flag(cls, port_name, flag_name):
                return None

            @classmethod
            def get_provider_flags(cls, port_name):
                return {}

            def get_provider_func(self, port_name):
                return self.number

        msg = r'Port of non-service class \(StaticProvider.number\) cannot be published on the domain'
        with self.assertRaisesRegexp(DomainDefinitionError, msg):
            class WillGoBoom(Domain):
                __services__ = [StaticProvider]
                __provides__ = ['number']  # static providers cannot be exported

        # ... but it can be used as a provider within the domain

        class Dog(Service):
            deps = Needs(['number'])

            @provides
            def bark(self):
                return ('woof ' * self.deps.number()).strip()

        class NoddyDomain(Domain):
            __services__ = [StaticProvider, Dog]
            __provides__ = ['bark']

        self.assertEqual([], NoddyDomain.get_needs())
        self.assertEqual('woof woof woof', NoddyDomain().bark())

    # TODO: update implementation so the following test passes
    # def test_domain_port_inherit_argspec_from_underlying_port(self):
    #
    #     class SimpleService(Service):
    #         @provides
    #         def func_with_args_kwargs(self, a, b=100, **kwargs):
    #             return "meow"
    #
    #         @provides
    #         def func_with_varargs(self, x, *args):
    #             return "woof"
    #
    #     class SimpleDomain(Domain):
    #         __services__ = [SimpleService]
    #         __provides__ = ['func_with_args_kwargs', 'func_with_varargs']
    #
    #     self.assert_has_same_argspec(SimpleService.func_with_args_kwargs, SimpleDomain.func_with_args_kwargs)
    #     self.assert_has_same_argspec(SimpleService.func_with_varargs, SimpleDomain.func_with_varargs)
    #
    # def assert_has_same_argspec(self, func1, func2):
    #     arg_spec1 = inspect.getargspec(func1)
    #     arg_spec2 = inspect.getargspec(func2)
    #     self.assertEqual(arg_spec1, arg_spec2)


class DomainProvidesTest(TestCase):

    def _get_animal_domain(self):

        class Dog(Service):
            @provides
            def bark(self):
                return 'woof'

        class Cat(Service):
            @provides_with('meow', volume=10)
            def growl(self, n):
                return ' '.join(['(nope)'] * n)

            @provides
            def stroke(self):
                return 'HISS!'

        class AnimalDomain(Domain):
            __services__ = [Cat, Dog]
            __provides__ = ['bark', 'meow']

        return AnimalDomain

    def test_published_domain_ports_can_be_called_as_instance_methods(self):
        AnimalDomain = self._get_animal_domain()
        animals = AnimalDomain()
        self.assertEqual('woof', animals.bark())
        self.assertEqual('(nope) (nope) (nope)', animals.meow(3))

        with self.assertRaisesRegexp(AttributeError, "'AnimalDomain' object has no attribute 'stroke'"):
            animals.stroke()  # this port is not exposed to domain

    def test_published_domain_ports_can_be_accessed_via_IProvide_methods(self):
        AnimalDomain = self._get_animal_domain()
        animals = AnimalDomain()

        self.assertEqual('woof', animals.get_provider_func('bark')())
        self.assertEqual('(nope) (nope) (nope)', animals.get_provider_func('meow')(3))

        with self.assertRaisesRegexp(UnknownPort, '"stroke" is not a valid port'):
            animals.get_provider_func('stroke')

    def test_port_flags_are_inherited_by_domain(self):
        AnimalDomain = self._get_animal_domain()

        self.assertIsNone(AnimalDomain.get_provider_flag('bark', 'volume'))
        self.assertEqual(10, AnimalDomain.get_provider_flag('meow', 'volume'))

        self.assertEqual({}, AnimalDomain.get_provider_flags('bark'))
        self.assertEqual({'volume': 10}, AnimalDomain.get_provider_flags('meow'))

    def test_provider_metadata_on_domain(self):
        AnimalDomain = self._get_animal_domain()
        animals = AnimalDomain()

        self.assertEqual('bark', animals.meta.get_provider_method_name('bark'))
        self.assertEqual('Dog', animals.meta.get_provider('bark').__class__.__name__)

        with self.assertRaisesRegexp(UnknownPort, '"moo" is not a valid port'):
            animals.meta.get_provider_method_name('moo')

        with self.assertRaisesRegexp(UnknownPort, '"moo" is not a valid port'):
            animals.meta.get_provider('moo')


class DomainNeedsTest(TestCase):

    @staticmethod
    def get_test_domain_class():

        class ServiceThatNeedsAandB(Service):
            deps = Needs(['a', 'b'])

            @provides
            def get_ab(self):
                return self.deps.a(), self.deps.b()

        class ServiceThatNeedsBandC(Service):
            deps = Needs(['b', 'c'])

            @provides
            def get_b(self):
                return self.deps.b()

            @provides
            def get_c(self):
                return self.deps.c()

        class TestDomain(Domain):
            __services__ = [ServiceThatNeedsAandB, ServiceThatNeedsBandC]
            __provides__ = ['get_ab', 'get_b', 'get_c']

        return TestDomain

    @staticmethod
    def get_provider_of_A_and_B():

        class ABProvider(Service):
            @provides
            def a(self):
                return 'A'

            @provides
            def b(self):
                return 'B'

        return ABProvider()

    def test_needs_of_services_are_exposed_on_domain(self):
        TestDomain = self.get_test_domain_class()
        domain = TestDomain

        self.assertItemsEqual(['a', 'b', 'c'], TestDomain.get_needs())
        self.assertItemsEqual(['a', 'b', 'c'], domain.get_needs())

    def test_providers_can_be_assigned_to_needs_of_a_domain(self):
        TestDomain = self.get_test_domain_class()
        domain = TestDomain()

        provider = self.get_provider_of_A_and_B()
        domain.set_provider('a', provider)
        domain.set_provider('b', provider)

        self.assertEqual(('A', 'B'), domain.get_ab())
        self.assertEqual('B', domain.get_b())

        with self.assertRaisesRegexp(DisconnectedPort, 'Port "c" has not been connected'):
            domain.get_c()


class DomainConnectivityTest(TestCase):

    def test_services_within_domain_are_wired_up_as_expected(self):
        A, B, C, D = self._get_service_and_domain_classes()

        d = D()
        # map service classes to actual instances
        a = d._service_map[A]
        b = d._service_map[B]
        c = d._service_map[C]

        self.assertIs(b, a.get_provider('b1'))
        self.assertIs(c, b.get_provider('c1'))

        self.assertItemsEqual(['x', 'y'], d.get_needs())
        self.assertItemsEqual(['a1', 'b2'], d.get_provides())

    @staticmethod
    def _get_service_and_domain_classes():
        """
             +----------------------------- D ------------------------------------+
             |                                                                    |
             |        +-------+                                                   |
             |        |       x ......................+.......................... x
            a1 ..... a1   A   |                       .                           |
             |        |       b1 ..+                  .                           |
             |        +-------+    .     +-------+    .      .................... y
             |                     .... b1       x ....      .                    |
             |                           |   B   y ...........    +-------+       |
            b2 ........................ b2       c1 ............ c1       |       |
             |                           +-------+                |   C   |       |
             |                                                   c2       |       |
             |                                                    +-------+       |
             +--------------------------------------------------------------------+
        """
        class A(Service):
            deps = Needs(['b1', 'x'])

            @provides
            def a1(self):
                """returns (b1 + x)."""
                return self.deps.b1() + self.deps.x()

        class B(Service):
            deps = Needs(['c1', 'x', 'y'])

            @provides
            def b1(self):
                """returns (c1 * 2)."""
                return self.deps.c1() * 2

            @provides
            def b2(self):
                """return (x + y)."""
                return self.deps.x() + self.deps.y()

        class C(Service):
            @provides
            def c1(self):
                return 100

            @provides
            def c2(self):
                return 'unused'

        class D(Domain):
            __services__ = [A, B, C]
            __provides__ = ['a1', 'b2']

        return A, B, C, D

    @staticmethod
    def _get_expected_values_of_D_domain(x, y):
        c1 = 100
        b1 = c1 * 2
        b2 = x + y
        a1 = b1 + x
        return {'a1': a1, 'b2': b2}

    @staticmethod
    def _get_provider_service(x, y):

        class ProviderService(Service):
            @provides
            def x(self):
                return x

            @provides
            def y(self):
                return y

        return ProviderService

    def test_wiring_domain_to_a_service(self):
        x = 1234
        y = 98716
        expected_values = self._get_expected_values_of_D_domain(x=x, y=y)

        _, _, _, D = self._get_service_and_domain_classes()
        domain = D()
        provider = self._get_provider_service(x, y)()

        auto_wire([domain, provider])

        self.assertEqual(expected_values['a1'], domain.a1())
        self.assertEqual(expected_values['b2'], domain.b2())

    def test_wiring_domain_to_a_domain(self):
        x = 1234
        y = 98716
        expected_values = self._get_expected_values_of_D_domain(x=x, y=y)

        _, _, _, D = self._get_service_and_domain_classes()
        domain = D()

        ProviderService = self._get_provider_service(x, y)

        class ProviderDomain(Domain):
            __services__ = [ProviderService]
            __provides__ = ['x', 'y']

        auto_wire([domain, ProviderDomain()])

        self.assertEqual(expected_values['a1'], domain.a1())
        self.assertEqual(expected_values['b2'], domain.b2())

    def test_wiring_service_to_a_domain(self):
        x = 1234
        y = 98716
        expected_values = self._get_expected_values_of_D_domain(x=x, y=y)

        _, _, _, D = self._get_service_and_domain_classes()

        class MultiplierService(Service):
            deps = Needs(['a1', 'b2'])

            @provides
            def multiplied(self):
                return self.deps.a1() * self.deps.b2()

        domain = D()
        provider = self._get_provider_service(x, y)()
        multiplier_service = MultiplierService()
        auto_wire([domain, provider, multiplier_service])

        self.assertEqual(expected_values['a1'], domain.a1())
        self.assertEqual(expected_values['b2'], domain.b2())
        self.assertEqual(expected_values['a1'] * expected_values['b2'], multiplier_service.multiplied())

    def test_instances_of_same_domain_are_isolated(self):
        x = 1234
        y = 98716
        expected_values = self._get_expected_values_of_D_domain(x=x, y=y)

        _, _, _, D = self._get_service_and_domain_classes()

        domain = D()
        another_domain = D()
        provider = self._get_provider_service(x, y)()

        auto_wire([domain, provider])

        # first instance wired
        self.assertEqual(expected_values['a1'], domain.a1())
        self.assertEqual(expected_values['b2'], domain.b2())

        # other instance remains disconnected
        with self.assertRaisesRegexp(DisconnectedPort, 'Port .+ has not been connected'):
            another_domain.a1()

        with self.assertRaisesRegexp(DisconnectedPort, 'Port .+ has not been connected'):
            another_domain.b2()

    def test_nesting_domains_and_service_within_domain(self):
        x = 1234
        y = 98716
        expected_values = self._get_expected_values_of_D_domain(x=x, y=y)

        _, _, _, D = self._get_service_and_domain_classes()
        ProviderService = self._get_provider_service(x, y)

        class ParentDomain(Domain):
            __services__ = [D, ProviderService]
            __provides__ = ['a1', 'b2']

        domain = ParentDomain()
        self.assertItemsEqual(['a1', 'b2'], domain.get_provides())
        self.assertItemsEqual([], domain.get_needs())

        self.assertEqual(expected_values['a1'], domain.a1())
        self.assertEqual(expected_values['b2'], domain.b2())
