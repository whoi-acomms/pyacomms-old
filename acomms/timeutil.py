__author__ = 'Eric'

from datetime import datetime, timedelta
import isodate


def convert_to_datetime(object_to_convert):
    # First, is it already a datetime?
    if isinstance(object_to_convert, datetime):
        as_datetime = object_to_convert
    else:
        # If it is an decimal (or sting convertable to a decimal), assume it is a unix time.
        try:
            as_datetime = datetime.utcfromtimestamp(int(object_to_convert))
        except ValueError:
            # If it can't be an int, try to parse it as a string.  Blank strings return None
            try:
                if object_to_convert == "":
                    return None
                as_datetime = isodate.parse_datetime(object_to_convert)
            except ValueError:
                raise(ValueError("Unable to parse object into a datetime"))

    return as_datetime

def convert_to_timedelta(object_to_convert):
    # Is it already a timeval?
    if isinstance(object_to_convert, timedelta):
        as_timedelta = object_to_convert
    else:
        # If it is an number (or a number as string or something), assume it is in seconds.
        try:
            as_timedelta = timedelta(seconds=int(object_to_convert))
        except ValueError:
            # Try parsing it as an ISO8601 string
            try:
                as_timedelta = isodate.parse_duration(object_to_convert)
            except ValueError:
                raise(ValueError("Unable to parse object into a timedelta"))
    return as_timedelta


def to_utc_iso8601(datetime_to_convert, strip_fractional_seconds=False):
    # Strip fractional seconds, if requested.
    if strip_fractional_seconds:
        datetime_to_convert.replace(microsecond=0)

    if (datetime_to_convert.tzinfo is None) or (datetime_to_convert.utcoffset is None):
        datetime_to_convert = datetime_to_convert.replace(tzinfo=isodate.UTC)
    else:
        datetime_to_convert = datetime_to_convert.astimezone(isodate.UTC)

    return isodate.datetime_isoformat(datetime_to_convert)


