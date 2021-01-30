from datetime import time, tzinfo, timedelta


class IST(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=2)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "+02:00"

    def __repr__(self):
        return f"{self.__class__.__name__}()"
