import calendar
import datetime

from gasofo import (
    Service,
    provides
)

__author__ = 'shawn'


class Clock(Service):
    """Shared clock."""

    @provides
    def get_current_ts(self):
        now = datetime.datetime.utcnow()
        ts = calendar.timegm(now.utctimetuple())
        return ts
