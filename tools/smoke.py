"""GUI smoke test: drives real user flows in a live window and checks the results.

.venv/bin/python tools/smoke.py    prints SMOKE OK / SMOKE FAIL, exit code 0 / 1
"""
import glob
import os
import sys
import tempfile
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
TMP = tempfile.mkdtemp()
os.environ['PSYCHONOTES_DB'] = os.path.join(TMP, 'smoke.db')

from main import ClientPicker, DatePicker, Dialog, PsychoNotesApp  # noqa: E402  (first: configures the window)
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.base import EventLoop  # noqa: E402
from kivy.input.motionevent import MotionEvent  # noqa: E402


class Tap(MotionEvent):
    """A finger tap at window coords, routed like real input (grab, collisions, disabled)."""

    def __init__(self, x, y):
        super().__init__('smoke', 1, (x / Window.width, y / Window.height), is_touch=True)

    def depack(self, args):
        self.sx, self.sy = args
        super().depack(args)

    def __call__(self):
        EventLoop.post_dispatch_input('begin', self)
        EventLoop.post_dispatch_input('end', self)


def modals():
    return [w for w in Window.children
            if isinstance(w, (Dialog, DatePicker, ClientPicker)) or type(w).__name__ == 'BackupPicker']


class Smoke(PsychoNotesApp):
    failed = False

    def export_dir(self):
        path = os.path.join(TMP, 'exports')
        os.makedirs(path, exist_ok=True)
        return path

    def on_start(self):
        super().on_start()
        self.steps = [self.unsaved_edits_prompt, self.save_client, self.session_from_client,
                      self.pick_date_and_save, self.open_client_picker, self.create_client_inline,
                      self.backup_then_delete, self.confirm_delete, self.open_restore,
                      self.pick_backup, self.confirm_restore, self.empty_home,
                      self.tap_demo_button]
        Clock.schedule_once(self.run_next, .5)

    def run_next(self, _dt=None):
        if not self.steps:
            print('SMOKE OK')
            return self.stop()
        step = self.steps.pop(0)
        try:
            step()
        except Exception:
            traceback.print_exc()
            print('SMOKE FAIL at', step.__name__)
            self.failed = True
            return self.stop()
        Clock.schedule_once(self.run_next, .6)  # let transitions and modals settle

    def screen(self, name=None):
        sm = self.root.ids.sm
        return sm.get_screen(name or sm.current)

    def unsaved_edits_prompt(self):
        assert self.screen('home').empty
        self.go('client_form')
        self.screen().ids.name.text = 'Тест Тестов'
        self.back()
        assert 'сохранения' in modals()[0].title

    def save_client(self):
        modals()[0].dismiss()
        assert self.root.ids.sm.current == 'client_form'
        form = self.screen()
        form.ids.age.text = '33'
        form.ids.temperament.value = 'Холерик'
        form.add_request('Запрос А')
        form.save()
        assert self.root.ids.sm.current == 'client'
        self.cid = self.screen().kw['client_id']
        assert self.db.client(self.cid)['requests'] == ['Запрос А']

    def session_from_client(self):
        self.go('session_form', client_id=self.cid)
        form = self.screen()
        assert form.client_name == 'Тест Тестов'
        assert form.ids.request_chips.options == ['Запрос А']
        form.pick_date()

    def pick_date_and_save(self):
        picker = modals()[0]
        picker.shift(-1)
        picker.pick(picker.month.replace(day=15))
        form = self.screen()
        assert form.meeting_date.endswith('-15')
        form.ids.time.text = '9:30'
        form.ids.before.value, form.ids.after.value = 3, 7
        form.ids.request_chips.value = 'Запрос А'
        form.ids.outcome.text = 'итог'
        form.save()
        notes = self.db.notes(client_id=self.cid)
        assert len(notes) == 1 and notes[0]['meeting_time'] == '09:30' and notes[0]['request'] == 'Запрос А'
        assert self.root.ids.sm.current == 'client' and self.screen().ids.chart.points

    def open_client_picker(self):
        self.go('home')
        self.go('session_form')
        self.screen().pick_client()

    def create_client_inline(self):
        picker = modals()[0]
        picker.ids.query.text = 'Новый Человек'
        picker.ids.list.children[-1].dispatch('on_release')  # top item: "create new client"
        form = self.screen()
        assert form.client_name == 'Новый Человек' and form.client_id
        form.ids.time.text = '25:99'
        form.save()
        assert self.root.ids.sm.current == 'session_form'  # invalid time rejected
        form.ids.time.text = '18:00'
        form.save()
        assert self.root.ids.sm.current == 'home'

    def backup_then_delete(self):
        self.go('settings')
        assert self.screen().folder  # first visit must refresh even though the rule has no ids
        self.screen().export_json()
        assert glob.glob(os.path.join(self.export_dir(), '*.json'))
        self.go('client', client_id=self.cid)
        self.go('client_form', client_id=self.cid)
        self.screen().delete()

    def confirm_delete(self):
        dialog = modals()[0]
        dialog.dismiss()
        dialog.callback()
        assert self.db.client(self.cid) is None and not self.db.notes(client_id=self.cid)
        assert self.root.ids.sm.current == 'clients'

    def open_restore(self):
        self.go('settings')
        self.screen().import_json()

    def pick_backup(self):
        modals()[0].ids.list.children[-1].dispatch('on_release')

    def confirm_restore(self):
        dialog = modals()[0]
        dialog.dismiss()
        dialog.callback()
        assert self.db.client(self.cid)['full_name'] == 'Тест Тестов'
        assert len(self.db.notes()) == 2
        self.go('history')
        assert len(self.screen().ids.rv.data) >= 2

    def empty_home(self):
        self.db.wipe()
        self.go('home')

    def tap_demo_button(self):
        # a real touch: the hidden "next session" card used to swallow taps on this button
        btn = next(w for w in self.screen().walk() if getattr(w, 'text', '') == 'Посмотреть на демо-данных')
        Tap(*btn.to_window(*btn.center))()
        assert self.db.clients(), 'tap on the demo button did nothing'


if __name__ == '__main__':
    app = Smoke()
    app.run()
    sys.exit(1 if app.failed else 0)
