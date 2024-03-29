from unittest import TestCase

from gasofo.discoverable import (
    AutoDiscoverConnections,
    DiscoveredConnection,
    INeed,
    auto_wire
)
from gasofo.exceptions import (
    DisconnectedPort,
    DuplicateProviders,
    IncompatibleProvider,
    SelfReferencingMadness,
    UnknownPort
)
from gasofo.service import (
    Needs,
    Service,
    provides
)


class AutoDiscoverAndWiringTest(TestCase):

    def test_discovery_when_there_are_no_ports(self):

        class Empty(Service):
            pass

        empty_component = Empty()
        discovered = AutoDiscoverConnections([empty_component])

        self.assertEqual([], discovered.get_needs())
        self.assertEqual([], discovered.get_provides())
        self.assertEqual([], discovered.unsatisfied_needs())
        self.assertEqual([], list(discovered.connections()))

    @staticmethod
    def get_services():
        """
             +-------+
             |       x
            a1   A   |          +-------+
             |       b1 ...... b1       y            +-------+
             +-------+          |   B   |            |       |
                               b2       c1 ........ c1   C   |
                                +-------+            |       |
                                                     +-------+
        """
        class A(Service):
            deps = Needs(['b1', 'x'])

            @provides
            def a1(self):
                return self.deps.b1() + self.deps.x()

        class B(Service):
            deps = Needs(['c1', 'x', 'y'])

            @provides
            def b1(self):
                return self.deps.c1()

            @provides
            def b2(self):
                return self.deps.x(), self.deps.y()

        class C(Service):
            @provides
            def c1(self):
                return 'boo'

        return A, B, C

    def test_discovery_of_ports_from_a_collection_of_components_classes(self):
        # We need to be able to discover connects between uninstantiated components for visualisation and analysis
        A, B, C = self.get_services()
        discovered = AutoDiscoverConnections([A, B, C])

        self.assertEqual(['b1', 'c1', 'x', 'y'], discovered.get_needs())
        self.assertEqual(['a1', 'b1', 'b2', 'c1'], discovered.get_provides())
        self.assertEqual(['x', 'y'], discovered.unsatisfied_needs())
        self.assertCountEqual([
            DiscoveredConnection(port_name='b1', consumer=A, provider=B),
            DiscoveredConnection(port_name='c1', consumer=B, provider=C)
        ], discovered.connections())

        self.assertEqual(A, discovered.get_provider('a1'))
        self.assertEqual(B, discovered.get_provider('b1'))
        self.assertEqual(B, discovered.get_provider('b2'))
        self.assertEqual(C, discovered.get_provider('c1'))

        with self.assertRaisesRegexp(UnknownPort, '"x1" is not a valid port'):
            self.assertEqual(C, discovered.get_provider('x1'))

    def test_discovery_of_ports_from_a_collection_of_components_instances(self):

        A, B, C = self.get_services()
        a = A()
        b = B()
        c = C()
        discovered = AutoDiscoverConnections([a, b, c])

        self.assertEqual(['b1', 'c1', 'x', 'y'], discovered.get_needs())
        self.assertEqual(['a1', 'b1', 'b2', 'c1'], discovered.get_provides())
        self.assertEqual(['x', 'y'], discovered.unsatisfied_needs())
        self.assertCountEqual([
            DiscoveredConnection(port_name='b1', consumer=a, provider=b),
            DiscoveredConnection(port_name='c1', consumer=b, provider=c)
        ], discovered.connections())

        self.assertEqual(a, discovered.get_provider('a1'))
        self.assertEqual(b, discovered.get_provider('b1'))
        self.assertEqual(b, discovered.get_provider('b2'))
        self.assertEqual(c, discovered.get_provider('c1'))

        with self.assertRaisesRegexp(UnknownPort, '"x1" is not a valid port'):
            self.assertEqual(c, discovered.get_provider('x1'))

    def test_auto_wiring_of_ports_from_a_collection_of_component_instances(self):
        A, B, C = self.get_services()
        a = A()
        b = B()
        c = C()

        auto_wire([a, b, c])

        self.assertEqual(b, a.get_provider('b1'))
        self.assertEqual(c, b.get_provider('c1'))

        self.assertRaises(DisconnectedPort, a.get_provider, 'x')
        self.assertRaises(DisconnectedPort, b.get_provider, 'y')

    def test_SelfReferencingMadness_raised_if_component_attempts_to_satisfy_itself(self):

        class Mad(Service):
            """This isn't strictly speaking wrong, but cannot sensible participate in auto-wiring."""
            deps = Needs('attention')

            @provides
            def attention(self):
                return self.deps.attention()

        with self.assertRaisesRegexp(SelfReferencingMadness, '.* both needs and provides "attention".*'):
            AutoDiscoverConnections([Mad()])

    def test_DuplicateProviders_raised_when_more_than_one_component_provides_the_same_port(self):

        class X(Service):
            @provides
            def x(self):
                return 'X'

            @provides
            def y(self):
                return 'Y'

        class Axe(Service):
            @provides
            def x(self):
                return 'X'

        with self.assertRaisesRegexp(DuplicateProviders, 'Duplicate providers for "x".*'):
            AutoDiscoverConnections([X(), Axe()])


class INeedTest(TestCase):

    class FakeProvider:
        def get_provider_func(self, port_name):
            return lambda: port_name.upper()

    class Needy(INeed):
        def __init__(self):
            super(INeedTest.Needy, self).__init__()
            self.stored_for_assertion = {}

        def _satisfy_need(self, port_name, func):
            self.stored_for_assertion[port_name] = func

        def _is_compatible_provider(self, port_name, provider):
            return True

    class NothingCompatible(Needy):
        def _is_compatible_provider(self, port_name, provider):
            return False

    def test_set_provider_calls__satisfy_needs(self):
        n = INeedTest.Needy()
        n.set_provider('my_port', INeedTest.FakeProvider())
        self.assertEqual('MY_PORT', n.stored_for_assertion['my_port']())

    def test_DuplicateProviders_raised_if_provider_set_for_same_port(self):
        n = INeedTest.Needy()
        n.set_provider('my_port', INeedTest.FakeProvider())
        with self.assertRaisesRegexp(DuplicateProviders, 'There is already a provider for "my_port"'):
            n.set_provider('my_port', INeedTest.FakeProvider())

    def test_is_compatible_provider_called_when_setting_provider(self):
        n = INeedTest.NothingCompatible()
        with self.assertRaisesRegexp(IncompatibleProvider, '.* is not compatible with port "my_port"'):
            n.set_provider('my_port', INeedTest.FakeProvider())

    def test_retrieving_a_previously_assigned_provider(self):
        p = INeedTest.FakeProvider()
        n = INeedTest.Needy()
        n.set_provider('my_port', p)

        self.assertIs(p, n.get_provider('my_port'))

    def test_retrieving_provider_from_unassigned_port_raises_DisconnectedPort(self):
        n = INeedTest.Needy()

        with self.assertRaisesRegexp(DisconnectedPort, '"my_port" has not been assigned a provider'):
            n.get_provider('my_port')
