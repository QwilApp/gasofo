from unittest import TestCase

from unittest import mock

from gasofo import (
    Domain,
    Needs,
    Service,
    func_as_provider,
    provides,
)
from gasofo.exceptions import (
    UnknownPort,
    DisconnectedPort,
)
from gasofo.testing import (
    patch_port,
    wrap_port,
)


def get_domain():
    """
    +---------------------- D --------------------+
    |                                             |
    |      +--- A ---+           +--- B ---+      |
    |      |         |           |         |      |
    a .... a         b ...+..... b         c .... c .... [ C ]
    |      |         |    .      |         |      |      c = 5
    |      +---------+    .      +---------+      |
    |      a(v) = b(v)    .     b(v) = v*10 + c   |
    |                     .                       |
    |                     .                       |
    |      +--- E ---+    .                       |
    |      |         |    .                       |
    e .... e         b ...+                       |
    |      |         |                            |
    |      +---------+                            |
    |     e(v) = b(2*v)                           |
    +---------------------------------------------+

    """

    class A(Service):
        deps = Needs(['b'])

        @provides
        def a(self, value):
            return self.deps.b(value=value)

    class B(Service):
        deps = Needs(['c'])

        @provides
        def b(self, value):
            return (value * 10) + self.deps.c()

    class E(Service):
        deps = Needs(['b'])

        @provides
        def e(self, value):
            return self.deps.b(value=2 * value)

    class D(Domain):
        __services__ = [A, B, E]
        __provides__ = ['a', 'e']

    domain = D()
    domain.set_provider(port_name='c', provider=func_as_provider(func=lambda: 5, port='c'))
    return domain


class PatchPortTest(TestCase):

    def test_patch_port_as_context_manager(self):
        domain = get_domain()

        self.assertEqual(9 * 10 + 5, domain.a(9))  # before patch

        with patch_port(component=domain, port_name='b') as mock_b:
            mock_b.side_effect = lambda value: 100 * value
            self.assertEqual(100 * 9, domain.a(9))  # patched

        mock_b.assert_called_once_with(value=9)
        self.assertEqual(9 * 10 + 5, domain.a(9))  # patch removed outside of context

    def test_patch_port_with_manual_start_stop(self):
        domain = get_domain()
        patcher = patch_port(component=domain, port_name='b')

        self.assertEqual(9 * 10 + 5, domain.a(9))  # before patch started

        mock_b = patcher.start()
        mock_b.side_effect = lambda value: 100 * value
        self.assertEqual(100 * 9, domain.a(9))  # patched

        patcher.stop()
        self.assertEqual(9 * 10 + 5, domain.a(9))  # patch removed once stopped

    def test_patch_port_affects_all_consumers_of_a_port(self):
        domain = get_domain()

        # before patch
        self.assertEqual(9 * 10 + 5, domain.a(9))
        self.assertEqual(2 * 9 * 10 + 5, domain.e(9))

        with patch_port(component=domain, port_name='b') as mock_b:
            mock_b.side_effect = lambda value: 100 * value
            self.assertEqual(100 * 9, domain.a(9))  # patched
            self.assertEqual(100 * 2 * 9, domain.e(9))  # patched

        mock_b.assert_has_calls([mock.call(value=9), mock.call(value=2 * 9)], any_order=False)

        # patch removed outside of context
        self.assertEqual(9 * 10 + 5, domain.a(9))
        self.assertEqual(2 * 9 * 10 + 5, domain.e(9))

    def test_patch_port_with_unknown_port_raises(self):
        domain = get_domain()

        with self.assertRaisesRegexp(UnknownPort, 'Could not find instances of port "unknown_port"'):
            patch_port(domain, port_name='unknown_port')

    def test_patch_port_with_disconnected_port_raises(self):
        domain = get_domain()
        domain2 = domain.__class__()  # get new instance of domain where 'c' port is not yet connected

        with self.assertRaisesRegexp(DisconnectedPort, 'B.c is disconnected'):
            patch_port(domain2, port_name='c')

    def test_stopping_patcher_before_starting_raises(self):
        domain = get_domain()
        patcher = patch_port(domain, port_name='c')

        with self.assertRaisesRegexp(RuntimeError, 'patcher not yet started'):
            patcher.stop()

    def test_stopping_patcher_twice_raises(self):
        domain = get_domain()
        patcher = patch_port(domain, port_name='c')
        patcher.start()
        patcher.stop()

        with self.assertRaisesRegexp(RuntimeError, 'patcher not yet started'):
            patcher.stop()

    def test_starting_patcher_already_started_raises(self):
        domain = get_domain()
        patcher = patch_port(domain, port_name='c')
        patcher.start()

        with self.assertRaisesRegexp(RuntimeError, 'patch already started'):
            patcher.start()

    def test_default_behaviour_of_mock_obj(self):
        domain = get_domain()
        with patch_port(domain, port_name='c') as m:
            self.assertIsNone(m.side_effect)
            self.assertIsInstance(m.return_value, mock.Mock)

    def test_side_effect_can_be_specified_during_patching(self):
        domain = get_domain()
        with patch_port(domain, port_name='c', side_effect=ValueError):
            with self.assertRaises(ValueError):
                domain.a(9)

    def test_return_value_can_be_specified_during_patching(self):
        domain = get_domain()
        with patch_port(domain, port_name='c', return_value=100):
            self.assertEqual(10 * 9 + 100, domain.a(9))


class WrapPortTest(TestCase):

    def test_wrap_port_as_context_manager(self):
        domain = get_domain()

        with wrap_port(component=domain, port_name='b') as wrapped_b:
            self.assertEqual(9 * 10 + 5, domain.a(9))  # should call through to actual port
            wrapped_b.assert_called_once_with(value=9)  # mock object can be used to assert calls

        # patch removed outside of context manager and calls no longer intercepted
        wrapped_b.reset_mock()
        self.assertEqual(9 * 10 + 5, domain.a(9))
        wrapped_b.assert_not_called()

    def test_wrap_port_with_manual_start_stop(self):
        domain = get_domain()
        patcher = wrap_port(component=domain, port_name='b')

        wrapped_b = patcher.start()
        self.assertEqual(9 * 10 + 5, domain.a(9))  # should call through to actual port
        wrapped_b.assert_called_once_with(value=9)  # mock object can be used to assert calls

        patcher.stop()
        # once stopped, calls no longer intercepted
        wrapped_b.reset_mock()
        self.assertEqual(9 * 10 + 5, domain.a(9))
        wrapped_b.assert_not_called()

    def test_patch_port_affects_all_consumers_of_a_port(self):
        domain = get_domain()

        with wrap_port(component=domain, port_name='b') as wrapped_b:
            self.assertEqual(9 * 10 + 5, domain.a(9))
            self.assertEqual(2 * 9 * 10 + 5, domain.e(9))

            wrapped_b.assert_has_calls([mock.call(value=9), mock.call(value=2 * 9)], any_order=False)

        # patch removed outside of context manager and calls no longer intercepted
        wrapped_b.reset_mock()
        self.assertEqual(9 * 10 + 5, domain.a(9))
        self.assertEqual(2 * 9 * 10 + 5, domain.e(9))
        wrapped_b.assert_not_called()

    def test_wrap_port_with_unknown_port_raises(self):
        domain = get_domain()

        with self.assertRaisesRegexp(UnknownPort, 'Could not find instances of port "unknown_port"'):
            wrap_port(domain, port_name='unknown_port')

    def test_wrap_port_with_disconnected_port_raises(self):
        domain = get_domain()
        domain2 = domain.__class__()  # get new instance of domain where 'c' port is not yet connected

        with self.assertRaisesRegexp(DisconnectedPort, 'B.c is disconnected'):
            wrap_port(domain2, port_name='c')

    def test_stopping_patcher_before_starting_raises(self):
        domain = get_domain()
        patcher = wrap_port(domain, port_name='c')

        with self.assertRaisesRegexp(RuntimeError, 'patcher not yet started'):
            patcher.stop()

    def test_stopping_patcher_twice_raises(self):
        domain = get_domain()
        patcher = wrap_port(domain, port_name='c')
        patcher.start()
        patcher.stop()

        with self.assertRaisesRegexp(RuntimeError, 'patcher not yet started'):
            patcher.stop()

    def test_starting_patcher_already_started_raises(self):
        domain = get_domain()
        patcher = wrap_port(domain, port_name='c')
        patcher.start()

        with self.assertRaisesRegexp(RuntimeError, 'patch already started'):
            patcher.start()

