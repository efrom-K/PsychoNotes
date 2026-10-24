"""Russian date/number formatting. Pure stdlib."""
from datetime import date

MONTHS_GEN = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
              'августа', 'сентября', 'октября', 'ноября', 'декабря')
MONTHS = ('Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль',
          'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь')
MONTHS_PREP = ('январе', 'феврале', 'марте', 'апреле', 'мае', 'июне', 'июле',
               'августе', 'сентябре', 'октябре', 'ноябре', 'декабре')
WEEKDAYS = ('пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс')
WEEKDAYS_FULL = ('Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье')


def plural(n, one, few, many):
    """plural(5, 'сессия', 'сессии', 'сессий') -> 'сессий'."""
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def human_date(iso, today=None, weekday=False):
    """'2026-10-24' -> 'Сегодня' / 'Вчера' / 'Завтра' / '24 октября' (+ year if not current)."""
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ''
    today = today or date.today()
    relative = {0: 'Сегодня', -1: 'Вчера', 1: 'Завтра'}.get((d - today).days)
    text = relative or f'{d.day} {MONTHS_GEN[d.month - 1]}'
    if not relative and d.year != today.year:
        text += f' {d.year}'
    if weekday:
        text += f', {WEEKDAYS[d.weekday()]}'
    return text


def time_until(when, now):
    """datetime -> 'через 40 мин' / 'через 2 ч 15 мин' / 'через 3 дня'."""
    minutes = int((when - now).total_seconds() // 60)
    if minutes < 1:
        return 'сейчас'
    if minutes < 60:
        return f'через {minutes} мин'
    if minutes < 24 * 60:
        h, m = divmod(minutes, 60)
        return f'через {h} ч' + (f' {m} мин' if m and h < 3 else '')
    days = (when.date() - now.date()).days
    return f"через {days} {plural(days, 'день', 'дня', 'дней')}"


def month_title(iso, today=None):
    d = date.fromisoformat(iso)
    today = today or date.today()
    return MONTHS[d.month - 1] + ('' if d.year == today.year else f' {d.year}')


def initials(name):
    parts = (name or '').split()
    return ''.join(p[0] for p in parts[:2]).upper() or '?'


def delta_text(before, after):
    if before is None or after is None:
        return ''
    d = after - before
    return f'+{d}' if d > 0 else str(d).replace('-', '−')


