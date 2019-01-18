import datetime
from collections import namedtuple
from io import StringIO

InterfaceNotifyData = namedtuple(
    'InterfaceNotifyData',
    ['interface', 'alias', 'hostname', 'from_status', 'to_status', 'time']
)


class NotifyData:
    header = ''
    message = ''

    def __init__(self, *args):
        pass

    def __str__(self):
        return self.message


def diff_datetime_human(d1: datetime.datetime, d2: datetime.datetime) -> str:
    diff = d2 - d1

    return timedelta_human(diff)


def timedelta_human(t: datetime.timedelta) -> str:
    days, seconds = t.days, t.seconds
    # hours = days * 24 + seconds // 3600
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    text = StringIO()
    if days > 0:
        text.write("{} days ".format(days))
    if hours > 0:
        text.write("{} hours ".format(hours))
    if minutes > 0:
        text.write("{} minutes ".format(minutes))
    if days == 0 and hours == 0 and minutes == 0 and seconds >= 0:
        text.write("< 1 minutes")

    if len(text.getvalue()) < 1:
        text.write("< 1 minutes")
    return text.getvalue()
