from datetime import time, tzinfo, timedelta
from freebusy_range import TZ_DELTA

class IST(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=TZ_DELTA)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "+02:00"

    def __repr__(self):
        return f"{self.__class__.__name__}()"
