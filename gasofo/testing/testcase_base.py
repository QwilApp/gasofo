from unittest import TestCase

import mock

from gasofo.testing.adapters import attach_mock_provider
from collections import namedtuple
from contextlib import contextmanager


class GasofoTestCase(TestCase):

    SERVICE_CLASS = None
    UNSPECIFIED = object()  # sentry for unspecified values

    PortCalled = namedtuple('PortCalled', 'port kwargs')

    def setUp(self):
        self.service = self.SERVICE_CLASS()
        self.parent_mock = mock.Mock()
        self.last_rc = self.UNSPECIFIED

    def GIVEN(self, needs_port, returns=UNSPECIFIED, has_side_effect=UNSPECIFIED):
        # TODO: check if already patched
        provider = attach_mock_provider(self.service, [needs_port])
        mocked_port = getattr(provider, needs_port)
        self.parent_mock.attach_mock(mocked_port, needs_port)

        if has_side_effect is not self.UNSPECIFIED:
            assert returns is self.UNSPECIFIED, "don't set both side effect and return value since one masks the other"
            mocked_port.side_effect = has_side_effect
        elif returns is not self.UNSPECIFIED:
            mocked_port.return_value = returns

        return mocked_port  # return mock object so custom setup and assertions can still be called

    def WHEN(self, port_called, **kwargs):
        self.last_rc = self.service.get_provider_func(port_called)(**kwargs)
        return self.last_rc

    def call(self, port, **kwargs):
        """Alias for self.WHEN. Used when we're not testing in the GIVEN-WHEN-THEN style."""
        return self.WHEN(port_called=port, **kwargs)

    def THEN(self, expected_output, is_sequence=False, order_matters=False):
        if self.last_rc is self.UNSPECIFIED:
            self.fail('No output recorded. Was self.WHEN(..) called?')

        if is_sequence:
            if order_matters:
                self.assertSequenceEqual(expected_output, self.last_rc)
            else:
                self.assertItemsEqual(expected_output, self.last_rc)
        else:
            self.assertEqual(expected_output, self.last_rc)

    def assert_port_called_once_with(self, needs_port, **kwargs):
        # intentionally exclude *args since we want to force Qwil developers to always call with kwargs
        getattr(self.parent_mock, needs_port).assert_called_once_with(**kwargs)

    def assert_ports_called(self, calls):
        mock_calls = [getattr(mock.call, call.port)(**call.kwargs) for call in calls]
        with self.showFullDiffOnError():
            self.assertSequenceEqual(mock_calls, self.parent_mock.method_calls)

    @contextmanager
    def showFullDiffOnError(self):
        """Temporarily sets self.maxDiff to None"""
        ori = self.maxDiff
        self.maxDiff = None
        yield
        self.maxDiff = ori
