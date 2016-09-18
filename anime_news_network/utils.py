import datetime

import dateutil
import dateutil.parser


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.date, datetime.datetime)):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


def parse_date(date):
    return datetime.date(*dateutil.parser.parse(date).timetuple()[:3])


def safe_compare(lmb=None):
    """Convert a cmp= function into a key= function
    """

    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
            self.lmb = lmb or (lambda x: x)

        def __lt__(self, other):
            try:
                return self.lmb(self.obj) < other
            except TypeError:
                return False

        def __gt__(self, other):
            try:
                return self.lmb(self.obj) > other
            except TypeError:
                return False

        def __eq__(self, other):
            try:
                return self.lmb(self.obj) == other
            except TypeError:
                return False

        def __le__(self, other):
            try:
                return self.lmb(self.obj) <= other
            except TypeError:
                return False

        def __ge__(self, other):
            try:
                return self.lmb(self.obj) >= other
            except TypeError:
                return False

        def __ne__(self, other):
            try:
                return self.lmb(self.obj) != other
            except TypeError:
                return False
    return K
