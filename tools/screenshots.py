"""Render README screenshots on demo data: python tools/screenshots.py [out_dir]"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'docs', 'screenshots'))
os.environ['PSYCHONOTES_DB'] = os.path.join(tempfile.mkdtemp(), 'demo.db')

from main import PsychoNotesApp  # noqa: E402  (first: it configures the window size)
import demo  # noqa: E402
from kivy.clock import Clock  # noqa: E402


class ShotApp(PsychoNotesApp):
    def export_dir(self):
        return '~/Documents/PsychoNotes'  # shown on the settings screen; keep the real home path out of the shots

    def on_start(self):
        self.prev_theme = self.config.get('ui', 'theme')
        self.set_theme('light')
        demo.seed(self.db)
        super().on_start()
        note = self.db.notes(client_id=1)[1]['note_id']  # [0] is an upcoming, unscored one
        todo = self.db.dashboard()['todo'][0]['note_id']
        self.steps = [
            ('home', lambda: self.go('home')),
            ('clients', lambda: self.go('clients')),
            ('client', lambda: self.go('client', client_id=1)),
            ('session', lambda: self.go('session', note_id=note)),
            ('session_form', lambda: self.go('session_form', note_id=note)),
            ('session_todo', lambda: self.go('session', note_id=todo)),
            ('history', lambda: self.go('history')),
            ('settings_dark', lambda: (self.go('settings'), self.set_theme('dark'))),
            ('home_dark', lambda: self.go('home')),
            ('client_dark', lambda: self.go('client', client_id=1)),
        ]
        os.makedirs(OUT, exist_ok=True)
        Clock.schedule_once(self.next_step, 1)

    def next_step(self, _dt):
        if not self.steps:
            self.set_theme(self.prev_theme)
            return self.stop()
        self.current, action = self.steps.pop(0)
        action()
        Clock.schedule_once(self.capture, .8)

    def capture(self, _dt):
        # export_to_png renders into an FBO; Window.screenshot reads whatever is in the back buffer
        target = os.path.join(OUT, f'{self.current}.png')
        self.root.export_to_png(target)
        print('saved', target)
        Clock.schedule_once(self.next_step, .2)


if __name__ == '__main__':
    ShotApp().run()
