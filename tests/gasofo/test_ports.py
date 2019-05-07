from unittest import TestCase

from gasofo.exceptions import (
    DisconnectedPort,
    InvalidPortName,
    UnknownPort,
    WiringError
)
from gasofo.ports import (
    PortArray,
    ShadowPortArray
)


class PortArrayTests(TestCase):
    def setUp(self):
        self.ports = PortArray()

    def test_empty_array_can_be_instantiated(self):
        self.assertEqual([], self.ports.get_ports())

    def test_adding_port(self):
        self.ports.add_port('hello')
        self.assertItemsEqual(['hello'], self.ports.get_ports())

        self.ports.add_port('world')
        self.assertItemsEqual(['hello', 'world'], self.ports.get_ports())

    def test_newly_added_port_raises_DisconnectedPort_when_called(self):
        self.ports.add_port('hello')
        with self.assertRaisesRegexp(DisconnectedPort, 'Port "hello" has not been connected'):
            self.ports.hello()

    def test_connecting_port_to_plain_function(self):

        def echo(s):
            return s.upper()

        self.ports.add_port('hello')
        self.ports.connect_port('hello', echo)
        self.assertEqual('YOLO', self.ports.hello('yolo'))

    def test_connecting_port_to_lambda_function(self):
        self.ports.add_port('hello')
        self.ports.connect_port('hello', lambda s: s.upper())
        self.assertEqual('YOLO', self.ports.hello('yolo'))

    def test_connecting_port_to_bound_method(self):

        class EchoChamber(object):
            def echo(self, s):
                return s.upper()

        self.ports.add_port('hello')
        self.ports.connect_port('hello', EchoChamber().echo)
        self.assertEqual('YOLO', self.ports.hello('yolo'))

    def test_connecting_port_to_static_method(self):

        class EchoChamber(object):
            @staticmethod
            def echo(s):
                return s.upper()

        self.ports.add_port('hello')
        self.ports.connect_port('hello', EchoChamber.echo)
        self.assertEqual('YOLO', self.ports.hello('yolo'))

    def test_connecting_port_to_class_method(self):

        class EchoChamber(object):
            @classmethod
            def echo(cls, s):
                return s.upper()

        self.ports.add_port('hello')
        self.ports.connect_port('hello', EchoChamber.echo)
        self.assertEqual('YOLO', self.ports.hello('yolo'))

    def test_connecting_port_to_callable_object(self):

        class EchoChamber(object):
            def __call__(self, s):
                return s.upper()

        self.ports.add_port('hello')
        self.ports.connect_port('hello', EchoChamber())
        self.assertEqual('YOLO', self.ports.hello('yolo'))

    def test_raises_WiringError_when_connecting_port_to_non_callable(self):
        self.ports.add_port('hello')
        with self.assertRaisesRegexp(WiringError, 'Cannot connect port to a non-callable object'):
            self.ports.connect_port('hello', None)

    def test_raises_UnknownPort_when_connecting_to_an_unknown_port(self):
        with self.assertRaisesRegexp(UnknownPort, '"hello" is not a valid port'):
            self.ports.connect_port('hello', lambda: None)

    def test_raises_InvalidPortName_when_port_name_does_not_match_constraints(self):
        self.assert_invalid_port_name_pattern('_starts_with_underscore')
        self.assert_invalid_port_name_pattern('has spaces')
        self.assert_invalid_port_name_pattern('9_does_not_start_with_lowercase_char')
        self.assert_invalid_port_name_pattern('A_does_not_start_with_lowercase_char')
        self.assert_invalid_port_name_pattern('not_!_alphanum')
        self.assert_invalid_port_name_pattern('no_-_dashes_please')

        # these should be fine
        self.ports.add_port('has_underscores')
        self.ports.add_port('has_UppErCaSe')
        self.ports.add_port('has_d1g1ts')

    def assert_invalid_port_name_pattern(self, port_name):
        expected_msg = '"{}" does not have required format for port names'.format(port_name)
        with self.assertRaisesRegexp(InvalidPortName, expected_msg):
            self.ports.add_port(port_name)

    def test_raises_InvalidPortName_when_reserved_words_used(self):
        self.assert_raises_when_port_name_is_reserved_word('add_port')
        self.assert_raises_when_port_name_is_reserved_word('get_ports')
        self.assert_raises_when_port_name_is_reserved_word('connect_port')
        self.assert_raises_when_port_name_is_reserved_word('get_needs')
        self.assert_raises_when_port_name_is_reserved_word('get_provides')

        # also pull in all attrs in case we miss something
        port_array_attrs = [a for a in dir(self.ports) if not a.startswith('_')]
        for name in port_array_attrs:
            self.assert_raises_when_port_name_is_reserved_word(name)

    def assert_raises_when_port_name_is_reserved_word(self, port_name):
        expected_msg = '"{}" is a reserved word and cannot be used as port name'.format(port_name)
        with self.assertRaisesRegexp(InvalidPortName, expected_msg):
            self.ports.add_port(port_name)

    def test_disconnect_port(self):
        self.ports.add_port('hello')
        self.ports.connect_port('hello', lambda: None)
        self.ports.disconnect_port('hello')

        with self.assertRaisesRegexp(DisconnectedPort, 'Port "hello" has not been connected'):
            self.ports.hello()

    def test_if_is_fine_to_disconnect_port_that_is_not_connected(self):
        self.ports.add_port('hello')
        self.ports.disconnect_port('hello')

        with self.assertRaisesRegexp(DisconnectedPort, 'Port "hello" has not been connected'):
            self.ports.hello()

    def test_raise_UnknownPort_when_disconnecting_an_unknown_port(self):
        with self.assertRaisesRegexp(UnknownPort, '"hello" is not a valid port'):
            self.ports.disconnect_port('hello')

    def test_replicating_port_array_results_in_array_with_disconnected_ports(self):
        self.ports.add_port('hello')
        self.ports.add_port('world')
        self.ports.connect_port('hello', lambda: None)

        new_ports = PortArray.replicate(self.ports)
        self.assertIsNot(new_ports, self.ports)
        self.assertItemsEqual(['hello', 'world'], new_ports.get_ports())

        # all ports should be disconnected
        with self.assertRaisesRegexp(DisconnectedPort, 'Port "hello" has not been connected'):
            new_ports.hello()
        with self.assertRaisesRegexp(DisconnectedPort, 'Port "world" has not been connected'):
            new_ports.world()


class ShadowPortArrayTest(TestCase):

    def setUp(self):
        self.array_a = PortArray()
        self.array_a.add_port('a_only')
        self.array_a.add_port('in_both')
        self.array_a.add_port('also_a_only')

        self.array_b = PortArray()
        self.array_b.add_port('b_only')
        self.array_b.add_port('in_both')

    def test_empty_shadow_port_array_can_be_created(self):
        shadow = ShadowPortArray([])
        self.assertEqual([], shadow.get_ports())

    def test_shadow_with_only_one_child(self):
        shadow = ShadowPortArray([self.array_b])
        self.assertItemsEqual(['b_only', 'in_both'], shadow.get_ports())

    def test_shadow_with_multiple_children(self):
        shadow = ShadowPortArray([self.array_a, self.array_b])
        self.assertItemsEqual(['a_only', 'also_a_only', 'b_only', 'in_both'], shadow.get_ports())

    def test_connecting_ports_via_shadow(self):
        shadow = ShadowPortArray([self.array_a, self.array_b])
        shadow.connect_port('in_both', lambda: 'both')
        shadow.connect_port('a_only', lambda: 'a')

        self.assertEqual('a', self.array_a.a_only())
        self.assertEqual('both', self.array_a.in_both())
        self.assertEqual('both', self.array_b.in_both())

        with self.assertRaisesRegexp(DisconnectedPort, 'Port "b_only" has not been connected'):
            self.array_b.b_only()

    def test_disconnecting_ports_via_shadow(self):
        shadow = ShadowPortArray([self.array_a, self.array_b])
        shadow.connect_port('in_both', lambda: 'both')
        shadow.connect_port('a_only', lambda: 'a')
        shadow.connect_port('b_only', lambda: 'b')

        shadow.disconnect_port('in_both')
        shadow.disconnect_port('b_only')

        with self.assertRaisesRegexp(DisconnectedPort, 'Port "in_both" has not been connected'):
            self.array_a.in_both()

        with self.assertRaisesRegexp(DisconnectedPort, 'Port "in_both" has not been connected'):
            self.array_b.in_both()

        with self.assertRaisesRegexp(DisconnectedPort, 'Port "b_only" has not been connected'):
            self.array_b.b_only()

        self.assertEqual('a', self.array_a.a_only())  # this should remain connected

    def test_raises_WiringError_when_connecting_port_to_non_callable(self):
        shadow = ShadowPortArray([self.array_a, self.array_b])
        with self.assertRaisesRegexp(WiringError, 'Cannot connect port to a non-callable object'):
            shadow.connect_port('in_both', None)

    def test_raise_UnknownPort_when_connecting_an_unknown_port(self):
        shadow = ShadowPortArray([self.array_a, self.array_b])
        with self.assertRaisesRegexp(UnknownPort, '"hello" is not a valid port'):
            shadow.connect_port('hello', lambda: 'hello')

    def test_raise_UnknownPort_when_disconnecting_an_unknown_port(self):
        shadow = ShadowPortArray([self.array_a, self.array_b])
        with self.assertRaisesRegexp(UnknownPort, '"hello" is not a valid port'):
            shadow.disconnect_port('hello')

    def test_shadow_does_not_inherit_ignored_ports(self):
        shadow = ShadowPortArray([self.array_a, self.array_b], ignore_ports=['in_both', 'also_a_only', 'fluff'])
        self.assertItemsEqual(['a_only', 'b_only'], shadow.get_ports())

    # TODO: Test ShadowPortArray of ShadowPortArray (e.g. when we have nested domains
