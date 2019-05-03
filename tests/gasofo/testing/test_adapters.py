from unittest import TestCase

from gasofo import (
    Domain,
    Needs,
    NeedsInterface,
    Service,
    provides,
)
from gasofo.exceptions import DisconnectedPort
from gasofo.testing import attach_mock_provider


class AttachMockProviderTest(TestCase):

    def test_attaching_mock_provider_to_service(self):

        class MyService(Service):
            deps = Needs(['a', 'b'])

            @provides
            def get_a(self):
                return self.deps.a()

            @provides
            def get_b(self):
                return self.deps.b()

        service = MyService()
        attach_mock_provider(consumer=service, ports={
            'a': 100
        })

        self.assertEqual(100, service.get_a())
        self.assertRaises(DisconnectedPort, service.get_b)

    def test_returned_mock_provider_can_be_operated_on(self):

        class MyService(Service):
            deps = Needs(['a', 'b'])

            @provides
            def get_a(self):
                return self.deps.a()

            @provides
            def get_b(self):
                return self.deps.b()

        service = MyService()
        provider = attach_mock_provider(consumer=service, ports=['a'])
        provider.a.side_effect = KeyError

        self.assertRaises(KeyError, service.get_a)
        self.assertRaises(DisconnectedPort, service.get_b)

        provider.a.assert_called_once_with()

    def test_argspecs_are_validated_when_called_via_mock_provider(self):

        class MyServiceNeeds(NeedsInterface):
            def a(self, a, b=10):
                pass

        class MyService(Service):
            deps = MyServiceNeeds()

            @provides
            def get_a(self, *args, **kwargs):
                return self.deps.a(*args, **kwargs)

        service = MyService()
        provider = attach_mock_provider(consumer=service, ports=['a'])
        provider.a.side_effect = lambda a, b=10: a + b

        # assert works as expected if called properly
        self.assertEqual(53, service.get_a(50, 3))
        self.assertEqual(53, service.get_a(a=50, b=3))
        self.assertEqual(53, service.get_a(b=50, a=3))
        self.assertEqual(60, service.get_a(a=50))

        with self.assertRaisesRegexp(TypeError, "'a' parameter lacking default value"):
            service.get_a()

        with self.assertRaisesRegexp(TypeError, "too many keyword arguments {'c': 10}"):
            service.get_a(100, c=10)

        with self.assertRaisesRegexp(TypeError, "'a' parameter lacking default value"):
            service.get_a(b=10)

    def test_interface_restriction_transferred_to_service_with_shared_needs(self):
        class MyServiceNeeds(NeedsInterface):
            def a(self, a, b=10):
                pass

        class MyService(Service):
            deps = MyServiceNeeds()

            @provides
            def get_a(self, *args, **kwargs):
                return self.deps.a(*args, **kwargs)

        class AnotherService(Service):
            deps = Needs(['a'])  # no interface supplied, but inherited with shared port of domain

            @provides
            def get_another(self, *args, **kwargs):
                return self.deps.a(*args, **kwargs)

        class MyDomain(Domain):
            __services__ = [MyService, AnotherService]
            __provides__ = ['get_another']

        domain = MyDomain()
        provider = attach_mock_provider(consumer=domain, ports=['a'])
        provider.a.side_effect = lambda a, b=10: a + b

        # assert works as expected if called properly
        self.assertEqual(53, domain.get_another(a=50, b=3))

        with self.assertRaisesRegexp(TypeError, "too many keyword arguments {'c': 10}"):
            domain.get_another(100, c=10)
