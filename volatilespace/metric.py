import math


up_prefix = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
down_prefix = ['m', 'µ', 'n', 'p', 'f', 'a', 'z', 'y']


def format_si(value, decimal=3):
    """Convert number to string with SI prefix"""

    if value == 0:   # log does not work with 0
        return str(value)
    if value is None:
        return str(0)

    size = int(math.log10(abs(value)) / 3)   # calculate number size
    prefix = ''

    if size == 0:
        return str(round(value, decimal))
    else:

        # up prefix
        if size > 0:
            if size - 1 < len(up_prefix):   # if size is in prefix range
                prefix = up_prefix[size - 1]
            else:
                prefix = up_prefix[-1]   # use largest prefix
                size = len(up_prefix)   # lower size

        # down prefix
        else:
            if -size - 1 < len(down_prefix):
                prefix = down_prefix[-size - 1]
            else:
                prefix = down_prefix[-1]
                size = -len(down_prefix)

        scaled = float(value * math.pow(1000, -size))
        return str(round(scaled, decimal)) + " " + prefix


def parse_si(value_string):
    """Convert string with SI prefix to number"""
    try:   # if no prefix
        value = float(value_string)
        return value
    except ValueError:   # assume there is prefix

        try:   # if prefix is on end of number
            value = float(value_string[:-1])
            prefix = value_string[-1]
            if prefix == "K":
                prefix = "k"
            try:
                size = up_prefix.index(prefix) + 1
            except ValueError:
                size = down_prefix.index(prefix) + 1
                size = -size
            real_value = value * math.pow(1000, size)
            return real_value

        except ValueError:   # if still failed, return None
            return None
