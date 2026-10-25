"""UI translations. Pure stdlib.

The Russian source string is the key: tr('Сохранить') looks it up in locales/<lang>.json and falls back
to the key itself, so Russian needs no file and free text (client names, notes) passes through unchanged.
Templates use str.format fields: tr('через {n} мин', n=5).
"""
import json
import os

LANGS = {'ru': 'Русский', 'en': 'English', 'de': 'Deutsch', 'es': 'Español', 'fr': 'Français',
         'ja': '日本語', 'zh': '中文'}
CJK = ('ja', 'zh')  # need a font with ideographs (Roboto has none)
LOCALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locales')

lang = 'ru'
_table = {}


def load(code):
    with open(os.path.join(LOCALE_DIR, f'{code}.json'), encoding='utf-8') as f:
        return json.load(f)


def set_lang(code):
    global lang, _table
    lang = code if code in LANGS else 'ru'
    _table = load(lang) if lang != 'ru' else {}
    return lang


def tr(text, **kw):
    text = _table.get(text, text)
    return text.format(**kw) if kw else text


def plural(n, one, few, many):
    """plural(5, 'сессия', 'сессии', 'сессий') -> 'сессий' (ru) / 'sessions' (en). Forms may contain {n}.

    Other languages translate the key 'one|few|many' into their own forms: 'session|sessions', 'セッション'.
    """
    n = abs(n)
    if lang == 'ru':
        i = 0 if n % 10 == 1 and n % 100 != 11 else 1 if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 2
        forms = (one, few, many)
    else:
        forms = tr(f'{one}|{few}|{many}').split('|')
        i = 0 if (n < 2 if lang == 'fr' else n == 1) else 1
    return forms[min(i, len(forms) - 1)].replace('{n}', str(n))
