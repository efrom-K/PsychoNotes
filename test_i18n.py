"""Every Russian string in the code must be translated in every locale, with the same {fields}.
`python test_i18n.py keys` prints the source keys as JSON (a starting point for a new locale)."""
import ast
import json
import re
import string
import sys
import unittest

import i18n

SOURCES = ('main.py', 'fmt.py', 'database.py', 'demo.py')
CYRILLIC = re.compile('[А-Яа-яЁё]')


def _py_keys(path):
    tree = ast.parse(open(path, encoding='utf-8').read())
    docs, plural_args, keys = set(), set(), []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
            docs.add(id(node.body[0].value))
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'plural':
            forms = node.args[1:4]
            plural_args.update(map(id, forms))
            keys.append('|'.join(a.value for a in forms))
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'tr' and isinstance(node.args[0], ast.Constant):
            keys.append(node.args[0].value)  # templates without Cyrillic, like '{d} {month}'
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str) and CYRILLIC.search(node.value)
                and id(node) not in docs and id(node) not in plural_args):
            keys.append(node.value)
    return keys


def _kv_keys(path):
    keys = []
    for line in open(path, encoding='utf-8'):
        if not line.lstrip().startswith('#'):
            keys += [ast.literal_eval(m) for m in re.findall(r"'(?:[^'\\\n]|\\.)*'", line) if CYRILLIC.search(m)]
    return keys


def source_keys():
    keys = [k for path in SOURCES for k in _py_keys(path)] + _kv_keys('ui.kv')
    return sorted(set(keys))


def fields(text):
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


class LocaleTest(unittest.TestCase):
    def test_locales_complete(self):
        keys = source_keys()
        self.assertGreater(len(keys), 100)
        for code in i18n.LANGS:
            if code == 'ru':
                continue
            table = i18n.load(code)
            with self.subTest(code):
                self.assertEqual(sorted(set(keys) - set(table)), [], 'missing')
                self.assertEqual(sorted(set(table) - set(keys)), [], 'unused')
                for key, value in table.items():
                    self.assertEqual(fields(value), fields(key), key)
                    if '|' in key:
                        self.assertEqual(value.count('|'), 0 if code in i18n.CJK else 1, key)

    def test_formatting(self):
        from datetime import date, datetime
        from fmt import human_date, time_until
        try:
            i18n.set_lang('en')
            self.assertEqual(i18n.plural(1, 'сессия', 'сессии', 'сессий'), 'session')
            self.assertEqual(i18n.plural(5, '{n} день', '{n} дня', '{n} дней'), '5 days')
            self.assertEqual(human_date('2025-03-08', date(2026, 10, 24)), 'March 8, 2025')
            self.assertEqual(time_until(datetime(2026, 10, 27, 9), datetime(2026, 10, 24, 10)), 'in 3 days')
            i18n.set_lang('fr')
            self.assertEqual(i18n.plural(0, 'сессия', 'сессии', 'сессий'), 'séance')
        finally:
            i18n.set_lang('ru')


if __name__ == '__main__':
    if sys.argv[1:] == ['keys']:
        print(json.dumps({k: '' for k in source_keys()}, ensure_ascii=False, indent=1))
    else:
        unittest.main()
