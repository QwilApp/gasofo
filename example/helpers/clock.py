import calendar
import datetime

from gasofo import func_as_provider


class Clock(object):
    """Shared clock."""

    @staticmethod
    def get_current_ts():
        now = datetime.datetime.utcnow()
        ts = calendar.timegm(now.utctimetuple())
        return ts


def get_clock_provider():
    return func_as_provider(func=Clock.get_current_ts, port='get_current_ts')
