"""Localized date/number formatting. Pure stdlib. Russian words are translation keys (see i18n)."""
from datetime import date

from i18n import plural, tr

MONTHS_GEN = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
              'августа', 'сентября', 'октября', 'ноября', 'декабря')
MONTHS = ('Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль',
          'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь')
MONTHS_PREP = ('январе', 'феврале', 'марте', 'апреле', 'мае', 'июне', 'июле',
               'августе', 'сентябре', 'октябре', 'ноябре', 'декабре')
MONTHS_SHORT = ('янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек')
WEEKDAYS = ('пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс')
WEEKDAYS_FULL = ('Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье')


def day_month(d):
    """date -> '24 октября' / 'October 24' / '10月24日'."""
    return tr('{d} {month}', d=d.day, month=tr(MONTHS_GEN[d.month - 1]))


def short_date(d):
    """date -> '24 окт' / 'Oct 24'."""
    return tr('{d} {mon}', d=d.day, mon=tr(MONTHS_SHORT[d.month - 1]))


def human_date(iso, today=None, weekday=False, inline=False):
    """'2026-10-24' -> 'Сегодня' / 'Вчера' / 'Завтра' / '24 октября' (+ year if not current).
    inline=True gives the mid-sentence form of the relative words ('сегодня')."""
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ''
    today = today or date.today()
    words = ('вчера', 'сегодня', 'завтра') if inline else ('Вчера', 'Сегодня', 'Завтра')
    delta = (d - today).days
    if -1 <= delta <= 1:
        text = tr(words[delta + 1])
    else:
        text = day_month(d)
        if d.year != today.year:
            text = tr('{date} {year}', date=text, year=d.year)
    if weekday:
        text = tr('{date}, {wd}', date=text, wd=tr(WEEKDAYS[d.weekday()]))
    return text


def today_title(d):
    """date -> 'Суббота, 24 октября'."""
    return tr('{wd}, {date}', wd=tr(WEEKDAYS_FULL[d.weekday()]), date=day_month(d))


def time_until(when, now):
    """datetime -> 'через 40 мин' / 'через 2 ч 15 мин' / 'через 3 дня'."""
    minutes = int((when - now).total_seconds() // 60)
    if minutes < 1:
        return tr('сейчас')
    if minutes < 60:
        return tr('через {m} мин', m=minutes)
    if minutes < 24 * 60:
        h, m = divmod(minutes, 60)
        return tr('через {h} ч {m} мин', h=h, m=m) if m and h < 3 else tr('через {h} ч', h=h)
    days = (when.date() - now.date()).days
    return tr('через {t}', t=plural(days, '{n} день', '{n} дня', '{n} дней'))


def month_year(month, year):
    return tr('{month} {year}', month=tr(MONTHS[month - 1]), year=year)


def month_title(iso, today=None):
    d = date.fromisoformat(iso)
    today = today or date.today()
    return tr(MONTHS[d.month - 1]) if d.year == today.year else month_year(d.month, d.year)


def initials(name):
    parts = (name or '').split()
    return ''.join(p[0] for p in parts[:2]).upper() or '?'


def delta_text(before, after):
    if before is None or after is None:
        return ''
    d = after - before
    return f'+{d}' if d > 0 else str(d).replace('-', '−')
