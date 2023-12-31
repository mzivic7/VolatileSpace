def to_date(seconds, clip=True):
    """Formats time from seconds to (Y, D, HH:MM:SS) and clips Y and D if they are 0,"""
    years = days = hours = minutes = 0
    minutes, seconds = divmod(seconds, 60)
    if minutes:
        hours, minutes = divmod(minutes, 60)
        if hours:
            days, hours = divmod(hours, 24)
            if days:
                years, days = divmod(days, 365)
                if years > 999:
                    years = 999
    if seconds < 10:
        seconds = "0" + str(seconds)
    if minutes < 10:
        minutes = "0" + str(minutes)
    if hours < 10:
        hours = "0" + str(hours)
    if clip:
        if years:
            return f"{years}y, {days}d, {hours}:{minutes}:{seconds}"
        elif days:
            return f"{days}d, {hours}:{minutes}:{seconds}"
        else:
            return f"{hours}:{minutes}:{seconds}"
    else:
        return f"{years}y, {days}d, {hours}:{minutes}:{seconds}"
