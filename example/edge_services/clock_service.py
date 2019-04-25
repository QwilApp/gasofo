import calendar
import datetime

from octa import (
    Service,
    provides
)


class Clock(Service):
    """Shared clock."""

    @provides
    def get_current_ts(self):
        now = datetime.datetime.utcnow()
        ts = calendar.timegm(now.utctimetuple())
        return ts
