"""python -m unittest  — data layer and formatting; no Kivy needed."""
import os
import tempfile
import unittest
from datetime import date, datetime

import demo
from database import Database, valid_time
from fmt import delta_text, human_date, initials, plural, time_until


def note(client_id, day, time='10:00', **kw):
    return dict(client_id=client_id, meeting_date=day, meeting_time=time, **kw)


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.cid = self.db.save_client({'full_name': 'Анна Соколова', 'anamnesis': 'важное', 'requests': ['Сон', ' ']})

    def test_client_roundtrip_drops_blank_requests(self):
        c = self.db.client(self.cid)
        self.assertEqual(c['requests'], ['Сон'])
        self.assertEqual(c['anamnesis'], 'важное')

    def test_editing_note_keeps_client_profile(self):
        # v1 bug: saving a note wiped the client's anamnesis and requests
        nid = self.db.save_note(note(self.cid, '2026-10-01'))
        self.db.save_note(note(self.cid, '2026-10-02', meeting_outcome='итог'), nid)
        c = self.db.client(self.cid)
        self.assertEqual((c['anamnesis'], c['requests']), ('важное', ['Сон']))
        self.assertEqual(self.db.note(nid)['meeting_outcome'], 'итог')
        self.assertEqual(len(self.db.notes()), 1)  # updated in place, not re-inserted

    def test_delete_client_cascades(self):
        self.db.save_note(note(self.cid, '2026-10-01'))
        self.db.delete_client(self.cid)
        self.assertEqual(self.db.conn.execute('SELECT COUNT(*) FROM Notes').fetchone()[0], 0)
        self.assertEqual(self.db.conn.execute('SELECT COUNT(*) FROM ClientRequests').fetchone()[0], 0)

    def test_search_is_case_insensitive_for_cyrillic(self):
        self.assertEqual(len(self.db.clients('анна')), 1)
        self.db.save_note(note(self.cid, '2026-10-01', techniques_used='Техника «Пустой стул»'))
        self.assertEqual(len(self.db.notes(search='ПУСТОЙ')), 1)

    def test_dashboard_splits_upcoming_todo_recent(self):
        now = datetime(2026, 10, 24, 12, 0)
        self.db.save_note(note(self.cid, '2026-10-25'))  # upcoming
        self.db.save_note(note(self.cid, '2026-10-24', '09:00'))  # past, not written up
        self.db.save_note(note(self.cid, '2026-10-20', initial_state_score=3, final_state_score=6,
                               meeting_outcome='ok'))  # past, complete
        d = self.db.dashboard(now)
        self.assertEqual([len(d[k]) for k in ('upcoming', 'todo', 'recent')], [1, 1, 1])
        self.assertEqual(d['avg_delta'], 3)
        self.assertEqual(self.db.next_session(self.cid, now)['meeting_date'], '2026-10-25')

    def test_backup_roundtrip_and_bad_file_changes_nothing(self):
        demo.seed(self.db, date(2026, 10, 24))
        before = (len(self.db.clients()), len(self.db.notes()))
        path = os.path.join(tempfile.mkdtemp(), 'b.json')
        self.db.export_json(path)
        self.db.wipe()
        self.assertEqual(self.db.import_json(path), before)
        self.assertEqual(self.db.client(self.cid)['requests'], ['Сон'])
        with open(path, 'w', encoding='utf-8') as f:
            f.write('{"app": "PsychoNotes", "clients": [{"full_name": "без id"}], "notes": []}')
        with self.assertRaises(ValueError):
            self.db.import_json(path)
        self.assertEqual((len(self.db.clients()), len(self.db.notes())), before)  # rolled back

    def test_csv_export(self):
        self.db.save_note(note(self.cid, '2026-10-01'))
        path = os.path.join(tempfile.mkdtemp(), 's.csv')
        self.assertEqual(self.db.export_csv(path), 1)
        with open(path, encoding='utf-8-sig') as f:
            self.assertIn('Анна Соколова', f.read())


class FormatTest(unittest.TestCase):
    def test_formatting(self):
        t = date(2026, 10, 24)
        self.assertEqual([plural(n, 'а', 'б', 'в') for n in (1, 3, 5, 11, 22)], ['а', 'б', 'в', 'в', 'б'])
        self.assertEqual(human_date('2026-10-25', t), 'Завтра')
        self.assertEqual(human_date('2025-03-08', t, weekday=True), '8 марта 2025, сб')
        self.assertEqual(initials('Иванова Мария Петровна'), 'ИМ')
        self.assertEqual((delta_text(3, 7), delta_text(7, 3), delta_text(None, 3)), ('+4', '−4', ''))
        now = datetime(2026, 10, 24, 10, 0)
        self.assertEqual(time_until(datetime(2026, 10, 24, 10, 40), now), 'через 40 мин')
        self.assertEqual(time_until(datetime(2026, 10, 24, 12, 15), now), 'через 2 ч 15 мин')
        self.assertEqual(time_until(datetime(2026, 10, 27, 9, 0), now), 'через 3 дня')
        self.assertTrue(valid_time('09:05') and not valid_time('9:5') and not valid_time('25:00'))


if __name__ == '__main__':
    unittest.main()
