from unittest import TestCase

from gasofo import (
    Needs,
    NeedsInterface,
    Service,
    provides,
)
from gasofo.convenience import func_as_provider
from gasofo.exceptions import (
    DisconnectedPort,
    InvalidPortName,
    NeedsInterfaceDefinitionError,
)


class ServiceNeedsTest(TestCase):

    def test_querying_needs_ports_on_service_class_and_instance(self):

        class MyService(Service):
            deps = Needs(['health', 'time', 'money'])

            @provides
            def happiness(self):
                return self.deps.health(), self.deps.time(), self.deps.money()

        self.assertCountEqual(['health', 'time', 'money'], MyService.get_needs())
        self.assertCountEqual(['health', 'time', 'money'], MyService().get_needs())

    def test_access_to_unadapted_needs_port_raises_DisconnectedPort(self):

        class MyService(Service):
            deps = Needs(['health'])

            @provides
            def happiness(self):
                return self.deps.health()

        service = MyService()

        with self.assertRaisesRegexp(DisconnectedPort, 'Port "health" has not been connected'):
            service.happiness()  # for brevity we access method directly rather than Provides port.

    def test_satisfying_service_needs_by_connecting_to_another_service(self):

        class Producer(Service):
            @provides
            def food(self):
                return 'Milk'

        class Consumer(Service):
            deps = Needs(['food'])

            @provides
            def eat(self):
                return self.deps.food()

        producer = Producer()
        consumer = Consumer()
        consumer.set_provider(port_name='food', provider=producer)

        self.assertEqual('Milk', consumer.eat())  # for brevity we access method directly rather than Provides port.

    def test_needs_of_different_service_instances_are_isolated_and_not_shared(self):

        class Producer(Service):
            @provides
            def food(self):
                return 'Milk'

        class Consumer(Service):
            deps = Needs(['food'])

            @provides
            def eat(self):
                return self.deps.food()

        producer = Producer()
        consumer = Consumer()
        another_consumer = Consumer()

        consumer.set_provider(port_name='food', provider=producer)

        self.assertEqual('Milk', consumer.eat())  # connected
        with self.assertRaisesRegexp(DisconnectedPort, 'Port "food" has not been connected'):
            another_consumer.eat()  # not connected

        self.assertIs(producer, consumer.get_provider(port_name='food'))


class ServiceNeedsInterfaceTest(TestCase):

    def test_service_needs_can_be_defined_with_interface_class(self):

        class MyServiceDeps(NeedsInterface):

            # Type hints and docs are optional, but makes it easier to use and validate

            def health(self, age):
                # type: (int) -> str
                """Some description."""

            def wealth(self, net_worth):
                # type: (int) -> str
                """Some description."""

        class MyService(Service):
            deps = MyServiceDeps()

            @provides
            def gimme(self):
                # type: () -> str
                return self.deps.wealth(50000) + self.deps.health(50)

        self.assertCountEqual(['health', 'wealth'], MyService.get_needs())
        self.assertCountEqual(['health', 'wealth'], MyService().get_needs())

    def test_service_needs_defined_with_interface_can_be_adapted(self):

        class MyServiceDeps(NeedsInterface):
            def some_data(self, data):
                # type: (str) -> str
                pass

        class MyService(Service):
            deps = MyServiceDeps()

            @provides
            def gimme(self, data):
                # type: (str) -> str
                return self.deps.some_data(data=data)

        service = MyService()
        self.assertRaises(DisconnectedPort, service.gimme, 'xyz')

        provider = func_as_provider(func=(lambda data: data.upper()), port='some_data')
        service.set_provider(port_name='some_data', provider=provider)
        self.assertEqual('YOLO', service.gimme(data='yolo'))

    def test_needs_interface_class_cannot_override_constructor(self):
        msg = 'CheekyInterface.__init__ - cannot override constructor of Needs Interface'
        with self.assertRaisesRegexp(NeedsInterfaceDefinitionError, msg):
            class CheekyInterface(NeedsInterface):
                def __init__(self):
                    super(CheekyInterface, self).__init__()

    def test_attributes_defined_in_interface_must_be_function(self):
        msg = 'BadInterface.my_data - only functions are allowed as attributes of a Needs Interface'
        with self.assertRaisesRegexp(NeedsInterfaceDefinitionError, msg):
            class BadInterface(NeedsInterface):
                my_data = "something that is not a function"

    def test_functions_defined_in_interface_must_meet_port_name_constraints(self):

        msg = '"add_port" is a reserved word and cannot be used as port name'
        with self.assertRaisesRegexp(InvalidPortName, msg):
            class BadInterface(NeedsInterface):
                def add_port(self): pass  # this is a reserved name and cannot be used as port name

        msg = '"_hide_me" does not have required format for port names'
        with self.assertRaisesRegexp(InvalidPortName, msg):
            class BadInterface2(NeedsInterface):
                def _hide_me(self): pass  # port names cannot start with underscore
