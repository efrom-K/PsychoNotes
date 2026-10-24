"""SQLite storage. Pure stdlib, no Kivy: importable from tests and tools."""
import csv
import json
import sqlite3
from datetime import date, datetime

CLIENT_FIELDS = ('full_name', 'age', 'phone_number', 'temperament', 'character_type',
                 'perception_type', 'anamnesis', 'help_plan')
NOTE_FIELDS = ('client_id', 'meeting_date', 'meeting_time', 'meeting_location', 'weather',
               'initial_state', 'initial_state_score', 'request', 'meeting_progress',
               'techniques_used', 'meeting_outcome', 'final_state', 'final_state_score')
BACKUP_VERSION = 1

# Schema is unchanged from v1, so databases created by older releases open as is.
SCHEMA = '''
CREATE TABLE IF NOT EXISTS Clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    age INTEGER,
    phone_number TEXT,
    temperament TEXT,
    character_type TEXT,
    perception_type TEXT,
    anamnesis TEXT,
    help_plan TEXT
);
CREATE TABLE IF NOT EXISTS ClientRequests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    request_text TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES Clients(client_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS Notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    meeting_date TEXT NOT NULL, -- YYYY-MM-DD
    meeting_time TEXT NOT NULL, -- HH:MM
    meeting_location TEXT,
    weather TEXT,
    initial_state TEXT,
    initial_state_score INTEGER,
    request TEXT,
    meeting_progress TEXT,
    techniques_used TEXT,
    meeting_outcome TEXT,
    final_state TEXT,
    final_state_score INTEGER,
    FOREIGN KEY (client_id) REFERENCES Clients(client_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_notes_client ON Notes(client_id);
CREATE INDEX IF NOT EXISTS idx_notes_when ON Notes(meeting_date, meeting_time);
CREATE INDEX IF NOT EXISTS idx_requests_client ON ClientRequests(client_id);
'''

NOTE_SELECT = '''
    SELECT n.*, c.full_name FROM Notes n JOIN Clients c ON c.client_id = n.client_id
'''


UPCOMING = '(n.meeting_date > ? OR (n.meeting_date = ? AND n.meeting_time >= ?))'


def _now(now=None):
    now = now or datetime.now()
    return now.strftime('%Y-%m-%d'), now.strftime('%H:%M')


def _casefold(s):
    return s.casefold() if s else s


class Database:
    def __init__(self, path=':memory:'):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        # SQLite's LIKE/lower() only fold ASCII; this makes Cyrillic search case-insensitive.
        self.conn.create_function('casefold', 1, _casefold, deterministic=True)
        self.conn.executescript(SCHEMA)

    def close(self):
        self.conn.close()

    def _rows(self, sql, args=()):
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---- clients ----

    def clients(self, search=''):
        return self._rows('''
            SELECT c.client_id, c.full_name, c.age, c.phone_number,
                   COUNT(n.note_id) AS session_count, MAX(n.meeting_date) AS last_session
            FROM Clients c LEFT JOIN Notes n ON n.client_id = c.client_id
            WHERE casefold(c.full_name) LIKE ?
            GROUP BY c.client_id ORDER BY casefold(c.full_name)
        ''', (f'%{search.strip().casefold()}%',))

    def client(self, client_id):
        row = self.conn.execute('SELECT * FROM Clients WHERE client_id = ?', (client_id,)).fetchone()
        if row is None:
            return None
        client = dict(row)
        client['requests'] = [r[0] for r in self.conn.execute(
            'SELECT request_text FROM ClientRequests WHERE client_id = ? ORDER BY request_id',
            (client_id,))]
        return client

    def save_client(self, data, client_id=None):
        """Insert (client_id=None) or update a client; `data['requests']` replaces the list."""
        values = [data.get(f) for f in CLIENT_FIELDS]
        with self.conn:
            if client_id is None:
                cur = self.conn.execute(
                    f'INSERT INTO Clients ({", ".join(CLIENT_FIELDS)}) VALUES ({", ".join("?" * len(CLIENT_FIELDS))})',
                    values)
                client_id = cur.lastrowid
            else:
                self.conn.execute(
                    f'UPDATE Clients SET {", ".join(f + " = ?" for f in CLIENT_FIELDS)} WHERE client_id = ?',
                    values + [client_id])
                self.conn.execute('DELETE FROM ClientRequests WHERE client_id = ?', (client_id,))
            self.conn.executemany(
                'INSERT INTO ClientRequests (client_id, request_text) VALUES (?, ?)',
                [(client_id, r.strip()) for r in data.get('requests') or [] if r.strip()])
        return client_id

    def delete_client(self, client_id):
        with self.conn:  # notes and requests go with it via ON DELETE CASCADE
            self.conn.execute('DELETE FROM Clients WHERE client_id = ?', (client_id,))

    # ---- notes (sessions) ----

    def notes(self, client_id=None, search=''):
        """Newest first. `search` matches client name and the free-text fields."""
        q = f'%{search.strip().casefold()}%'
        sql = NOTE_SELECT + '''
            WHERE (? IS NULL OR n.client_id = ?)
              AND (casefold(c.full_name) LIKE ? OR casefold(n.request) LIKE ?
                   OR casefold(n.techniques_used) LIKE ? OR casefold(n.meeting_outcome) LIKE ?)
            ORDER BY n.meeting_date DESC, n.meeting_time DESC
        '''
        return self._rows(sql, (client_id, client_id, q, q, q, q))

    def note(self, note_id):
        row = self.conn.execute(NOTE_SELECT + ' WHERE n.note_id = ?', (note_id,)).fetchone()
        return dict(row) if row else None

    def save_note(self, data, note_id=None):
        values = [data.get(f) for f in NOTE_FIELDS]
        with self.conn:
            if note_id is None:
                cur = self.conn.execute(
                    f'INSERT INTO Notes ({", ".join(NOTE_FIELDS)}) VALUES ({", ".join("?" * len(NOTE_FIELDS))})',
                    values)
                return cur.lastrowid
            self.conn.execute(
                f'UPDATE Notes SET {", ".join(f + " = ?" for f in NOTE_FIELDS)} WHERE note_id = ?',
                values + [note_id])
            return note_id

    def delete_note(self, note_id):
        with self.conn:
            self.conn.execute('DELETE FROM Notes WHERE note_id = ?', (note_id,))

    def progress(self, client_id):
        """Scored sessions oldest first, for the progress chart."""
        return self._rows('''
            SELECT note_id, meeting_date, initial_state_score, final_state_score FROM Notes
            WHERE client_id = ? AND (initial_state_score IS NOT NULL OR final_state_score IS NOT NULL)
            ORDER BY meeting_date, meeting_time
        ''', (client_id,))

    def known_locations(self):
        return [r[0] for r in self.conn.execute('''
            SELECT meeting_location FROM Notes WHERE meeting_location <> ''
            GROUP BY meeting_location ORDER BY COUNT(*) DESC LIMIT 6''')]

    def dashboard(self, now=None):
        """Counters plus three lists: upcoming, past sessions still missing a result (todo), recent."""
        today, clock = _now(now)
        one = lambda sql, args=(): self.conn.execute(sql, args).fetchone()[0]
        past = f'NOT {UPCOMING}'
        todo = "(n.final_state_score IS NULL OR COALESCE(n.meeting_outcome, '') = '')"
        return {
            'clients': one('SELECT COUNT(*) FROM Clients'),
            'sessions': one('SELECT COUNT(*) FROM Notes'),
            'month': one('SELECT COUNT(*) FROM Notes WHERE meeting_date LIKE ?', (today[:7] + '%',)),
            'avg_delta': one('''SELECT AVG(final_state_score - initial_state_score) FROM Notes
                                WHERE final_state_score IS NOT NULL AND initial_state_score IS NOT NULL'''),
            'upcoming': self._rows(NOTE_SELECT + f' WHERE {UPCOMING} ORDER BY n.meeting_date, n.meeting_time LIMIT 4',
                                   (today, today, clock)),
            'todo': self._rows(NOTE_SELECT + f' WHERE {past} AND {todo} ORDER BY n.meeting_date DESC, n.meeting_time DESC LIMIT 5',
                               (today, today, clock)),
            'recent': self._rows(NOTE_SELECT + f' WHERE {past} AND NOT {todo} ORDER BY n.meeting_date DESC, n.meeting_time DESC LIMIT 5',
                                 (today, today, clock)),
        }

    def next_session(self, client_id, now=None):
        today, clock = _now(now)
        row = self.conn.execute(NOTE_SELECT + f' WHERE n.client_id = ? AND {UPCOMING} ORDER BY n.meeting_date, n.meeting_time',
                                (client_id, today, today, clock)).fetchone()
        return dict(row) if row else None

    # ---- backup ----

    def export_json(self, path):
        clients = [self.client(c['client_id']) for c in self.clients()]
        notes = self._rows('SELECT * FROM Notes ORDER BY note_id')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'app': 'PsychoNotes', 'version': BACKUP_VERSION,
                       'exported_at': datetime.now().isoformat(timespec='seconds'),
                       'clients': clients, 'notes': notes}, f, ensure_ascii=False, indent=1)

    def import_json(self, path):
        """Replace all data with a backup. Validates first; on any error nothing changes."""
        with open(path, encoding='utf-8') as f:
            backup = json.load(f)
        if not isinstance(backup, dict) or backup.get('app') != 'PsychoNotes':
            raise ValueError('Это не резервная копия PsychoNotes')
        clients, notes = backup.get('clients'), backup.get('notes')
        if not isinstance(clients, list) or not isinstance(notes, list):
            raise ValueError('Файл повреждён')
        try:
            with self.conn:
                self.conn.execute('DELETE FROM Clients')
                for c in clients:
                    self.conn.execute(
                        f'INSERT INTO Clients (client_id, {", ".join(CLIENT_FIELDS)}) VALUES (?{", ?" * len(CLIENT_FIELDS)})',
                        [c['client_id']] + [c.get(f) for f in CLIENT_FIELDS])
                    self.conn.executemany(
                        'INSERT INTO ClientRequests (client_id, request_text) VALUES (?, ?)',
                        [(c['client_id'], r) for r in c.get('requests') or []])
                for n in notes:
                    self.conn.execute(
                        f'INSERT INTO Notes (note_id, {", ".join(NOTE_FIELDS)}) VALUES (?{", ?" * len(NOTE_FIELDS)})',
                        [n['note_id']] + [n.get(f) for f in NOTE_FIELDS])
        except (KeyError, TypeError, sqlite3.Error) as e:
            raise ValueError(f'Файл повреждён: {e}') from e
        return len(clients), len(notes)

    def export_csv(self, path):
        rows = self._rows(NOTE_SELECT + ' ORDER BY n.meeting_date, n.meeting_time')
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:  # BOM so Excel reads Cyrillic
            writer = csv.DictWriter(f, fieldnames=['full_name', *NOTE_FIELDS[1:]], extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        return len(rows)

    def wipe(self):
        with self.conn:
            self.conn.execute('DELETE FROM Clients')


def parse_date(text):
    """'YYYY-MM-DD' -> date, or None if invalid."""
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def valid_time(text):
    try:
        return datetime.strptime(text, '%H:%M').strftime('%H:%M') == text
    except (TypeError, ValueError):
        return False
