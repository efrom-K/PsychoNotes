import os
import random
import shutil
import sys
from datetime import date, datetime, timedelta

from kivy.utils import platform
from kivy.config import Config

if platform not in ('android', 'ios'):
    Config.set('graphics', 'width', '420')
    Config.set('graphics', 'height', '860')
    Config.set('graphics', 'minimum_width', '360')
    Config.set('graphics', 'minimum_height', '560')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # no red dots on right click
Config.set('kivy', 'exit_on_escape', '0')  # Esc means "back"

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import (BooleanProperty, ColorProperty, ListProperty, NumericProperty,
                             ObjectProperty, StringProperty)
from kivy.resources import resource_add_path
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import NoTransition, Screen, SlideTransition
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex

import demo
from database import Database, parse_date, valid_time
from fmt import (MONTHS, MONTHS_GEN, MONTHS_PREP, WEEKDAYS_FULL, delta_text, human_date, initials, month_title, plural,
                 time_until)

BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

# Soft pastel, matte: milky translucent panels with grain on a flat background.
# Pastel fills always carry dark `ink` text for contrast. tint1-4 colour the avatars. 8-digit hex = RGBA.
THEMES = {
    'light': dict(
        bg='#eeeae3', tint1='#c3e6d6', tint2='#f9d6c6', tint3='#ddd6f3', tint4='#cfe2f3',
        surface='#ffffff', glass='#ffffffe0', glass_strong='#fffffff5', stroke='#2a2c2b17', shadow='#5c4a3a1a',
        surface2='#3b353012', text='#1d1f1e', muted='#555852', border='#3b35301f', ink='#1d1f1e',
        accent='#2c6a58', accent_fill='#b9e0cf', accent_soft='#2c6a581a', hero='#dcefe6f2',
        danger='#b9544a', danger_soft='#f3d4cd', warn='#9a6418', warn_soft='#f7e4c2',
        score_low='#f5c3b3', score_mid='#f4e1a6', score_high='#bfe3d3',
        series_before='#eb6834', series_after='#2a78d6'),
    'dark': dict(
        bg='#15171a', tint1='#8fc5b2', tint2='#dcb19f', tint3='#b6addc', tint4='#a5c1dc',
        surface='#1f2225', glass='#ffffff12', glass_strong='#24282bf2', stroke='#ffffff1c', shadow='#00000066',
        surface2='#ffffff10', text='#ecebe6', muted='#a6a8a2', border='#ffffff1a', ink='#16191b',
        accent='#a3d9c5', accent_fill='#a3d9c5', accent_soft='#a3d9c51f', hero='#a3d9c51c',
        danger='#f0a69a', danger_soft='#f0a69a26', warn='#f0cb8e', warn_soft='#f0cb8e24',
        score_low='#e8a998', score_mid='#e6cf8f', score_high='#a3d9c5',
        series_before='#d95926', series_after='#3987e5'),
}
TABS = ('home', 'clients', 'history', 'settings')
SCREENS = {'clients': 'ClientsScreen', 'history': 'HistoryScreen', 'settings': 'SettingsScreen',
           'client': 'ClientScreen', 'client_form': 'ClientFormScreen', 'session': 'SessionScreen',
           'session_form': 'SessionFormScreen'}  # built on first visit; only home exists at startup
LOCATIONS = ['Кабинет', 'Онлайн']


def app():
    return App.get_running_app()


def sheen_texture():
    """Vertical white gradient, opaque at the top: the soft highlight on glass and buttons."""
    tex = Texture.create(size=(1, 64), colorfmt='rgba')
    tex.blit_buffer(bytes(c for y in range(64) for c in (255, 255, 255, y * 4)), colorfmt='rgba', bufferfmt='ubyte')
    return tex


def grain_texture(size=1024):
    """Grey noise, used 1:1 via get_region: at a few percent opacity it turns translucency into frosted glass."""
    tex = Texture.create(size=(size, size), colorfmt='luminance')
    tex.blit_buffer(random.Random(7).randbytes(size * size), colorfmt='luminance', bufferfmt='ubyte')
    return tex


def tone(before, after):
    if before is None or after is None:
        return ''
    return 'good' if after > before else 'bad' if after < before else 'flat'


def session_item(n, todo=False):
    d = parse_date(n['meeting_date'])
    item = dict(viewclass='SessionRow', height=dp(72), note_id=n['note_id'],
                day=str(d.day) if d else '?', mon=MONTHS_GEN[d.month - 1][:3] if d else '',
                title=n['full_name'],
                subtitle=' · '.join(filter(None, [n['meeting_time'], n.get('request')])),
                badge=delta_text(n['initial_state_score'], n['final_state_score']),
                tone=tone(n['initial_state_score'], n['final_state_score']), target='session')
    if todo:
        item.update(badge='Заполнить', tone='warn', target='session_form')
    return item


def make(name, **attrs):
    """Instantiate a kv dynamic class: its kv-declared properties can't be passed to __init__."""
    widget = getattr(Factory, name)()
    for key, value in attrs.items():
        setattr(widget, key, value)
    return widget


def fill(box, items):
    """Put RecycleView-style dicts into a plain layout (for short, non-scrolling lists)."""
    box.clear_widgets()
    for item in items:
        item = dict(item)
        box.add_widget(make(item.pop('viewclass'), **item))


# ---------- widgets ----------

class Glass(BoxLayout):
    """Base panel (styled in ui.kv). A panel collapsed to height 0 still lays its children
    out past its bounds, so it must not take touches meant for the widgets underneath."""

    def on_touch_down(self, touch):
        return self.height > 0 and super().on_touch_down(touch)


class ChipGroup(StackLayout):
    """Single-choice chips; tapping the active chip clears the value."""
    options = ListProperty()
    value = StringProperty('')

    def on_options(self, *_):
        self.clear_widgets()
        for opt in self.options:
            chip = make('Chip', text=opt, active=opt == self.value)
            chip.bind(on_release=lambda c: setattr(self, 'value', '' if self.value == c.text else c.text))
            self.add_widget(chip)

    def on_value(self, *_):
        for chip in self.children:
            chip.active = chip.text == self.value


class ScoreSelector(BoxLayout):
    """0-10 scale tinted from peach (bad) to mint (good); -1 means not rated."""
    value = NumericProperty(-1)

    def __init__(self, **kw):
        super().__init__(**kw)
        for i in range(11):
            pill = make('ScorePill', text=str(i))
            pill.bind(on_release=lambda p: setattr(self, 'value', -1 if self.value == int(p.text) else int(p.text)))
            self.add_widget(pill)
        self.on_value()

    def on_value(self, *_):
        for pill in self.children:
            pill.active = int(pill.text) == self.value


class ProgressChart(Widget):
    """Line chart of state scores before/after each session, with tap/hover tooltip."""
    points = ListProperty()  # dicts from Database.progress()
    selected = NumericProperty(-1)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.redraw, size=self.redraw, points=self.redraw, selected=self.redraw)
        app().bind(theme=self.redraw)
        Window.bind(mouse_pos=self.on_mouse)

    def _xy(self, i, v):
        left, right, bottom, top = dp(26), dp(10), dp(24), dp(12)
        n = len(self.points)
        x = self.x + left + (self.width - left - right) * (i / (n - 1) if n > 1 else .5)
        return x, self.y + bottom + (self.height - bottom - top) * v / 10

    def _text(self, text, size=12, bold=False):
        label = CoreLabel(text=text, font_size=sp(size), bold=bold)
        label.refresh()
        return label.texture

    def redraw(self, *_):
        a = app()
        self.canvas.clear()
        if not self.points:
            return
        with self.canvas:
            for v in (0, 5, 10):  # recessive grid
                _, y = self._xy(0, v)
                Color(*a.border)
                Line(points=[self.x + dp(26), y, self.right - dp(10), y], width=1)
                Color(*a.muted)
                t = self._text(str(v))
                Rectangle(texture=t, size=t.size, pos=(self.x + dp(20) - t.width, y - t.height / 2))
            for i in {0, len(self.points) - 1}:
                d = parse_date(self.points[i]['meeting_date'])
                t = self._text(f'{d.day} {MONTHS_GEN[d.month - 1][:3]}')
                x, _ = self._xy(i, 0)
                x = min(max(x - t.width / 2, self.x), self.right - t.width)
                Rectangle(texture=t, size=t.size, pos=(x, self.y))
            if self.selected >= 0:
                x, y0 = self._xy(self.selected, 0)
                Line(points=[x, y0, x, self._xy(0, 10)[1]], width=1, dash_length=4, dash_offset=4)
            for key, color in (('initial_state_score', a.series_before), ('final_state_score', a.series_after)):
                pts = [(i, p[key]) for i, p in enumerate(self.points) if p[key] is not None]
                Color(*color)
                if len(pts) > 1:
                    Line(points=[c for i, v in pts for c in self._xy(i, v)], width=dp(1.2))
                for i, v in pts:
                    x, y = self._xy(i, v)
                    r = dp(5) if i == self.selected else dp(4)
                    Color(*a.surface)
                    Ellipse(pos=(x - r - dp(2), y - r - dp(2)), size=(2 * r + dp(4),) * 2)
                    Color(*color)
                    Ellipse(pos=(x - r, y - r), size=(2 * r, 2 * r))
            if self.selected >= 0:
                self._tooltip(a)

    def _tooltip(self, a):
        p = self.points[self.selected]
        fmt = lambda v: '—' if v is None else str(v)
        t = self._text(f"{human_date(p['meeting_date'])}   до {fmt(p['initial_state_score'])}"
                       f"   после {fmt(p['final_state_score'])}", 13, True)
        x, _ = self._xy(self.selected, 0)
        w, h = t.width + dp(20), t.height + dp(12)
        x = min(max(x - w / 2, self.x), self.right - w)
        y = self.top - h + dp(6)
        Color(*a.surface)
        RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(10)])
        Color(*a.text)
        Rectangle(texture=t, size=t.size, pos=(x + dp(10), y + dp(6)))

    def _nearest(self, x):
        return min(range(len(self.points)), key=lambda i: abs(self._xy(i, 0)[0] - x))

    def on_touch_down(self, touch):
        if self.points and self.collide_point(*touch.pos) and not touch.is_mouse_scrolling:
            i = self._nearest(touch.x)
            self.selected = -1 if i == self.selected else i
            return True
        return super().on_touch_down(touch)

    def on_mouse(self, _win, pos):
        if not self.points or not self.get_root_window():
            return
        local = self.to_widget(*pos)
        self.selected = self._nearest(local[0]) if self.collide_point(*local) else -1


class Dialog(ModalView):
    title = StringProperty('')
    text = StringProperty('')
    ok_text = StringProperty('Удалить')
    danger = BooleanProperty(True)
    callback = ObjectProperty(None)


class ClientPicker(ModalView):
    callback = ObjectProperty(None)

    def on_open(self):
        self.ids.query.text = ''
        self.search('')
        Clock.schedule_once(lambda _: setattr(self.ids.query, 'focus', True), .1)

    def search(self, text):
        box = self.ids.list
        box.clear_widgets()
        clients = app().db.clients(text)
        name = ' '.join(text.split())
        if name and not any(c['full_name'].casefold() == name.casefold() for c in clients):
            btn = make('SoftBtn', icon='add', text=f'Новый клиент «{name}»')
            btn.bind(on_release=lambda _: self.pick(app().db.save_client({'full_name': name}), name))
            box.add_widget(btn)
        for c in clients:
            row = make('PickRow', text=c['full_name'], initials=initials(c['full_name']))
            row.bind(on_release=lambda r, c=c: self.pick(c['client_id'], c['full_name']))
            box.add_widget(row)

    def pick(self, client_id, name):
        self.dismiss()
        self.callback(client_id, name)


class DatePicker(ModalView):
    title = StringProperty('')
    callback = ObjectProperty(None)

    def show(self, iso):
        self.value = parse_date(iso) or date.today()
        self.month = self.value.replace(day=1)
        self.render()
        self.open()

    def shift(self, months):
        m = self.month.month - 1 + months
        self.month = date(self.month.year + m // 12, m % 12 + 1, 1)
        self.render()

    def render(self):
        self.title = f'{MONTHS[self.month.month - 1]} {self.month.year}'
        grid = self.ids.grid
        grid.clear_widgets()
        start = self.month - timedelta(days=self.month.weekday())
        for k in range(42):
            d = start + timedelta(days=k)
            btn = make('DayCell', text=str(d.day), active=d == self.value, today=d == date.today(),
                       dim=d.month != self.month.month)
            btn.bind(on_release=lambda _, d=d: self.pick(d))
            grid.add_widget(btn)

    def pick(self, d):
        self.dismiss()
        self.callback(d.isoformat())


class Root(FloatLayout):
    def toast(self, text):
        t = self.ids.toast
        t.text = text
        Animation.cancel_all(t)
        anim = Animation(opacity=1, duration=.15) + Animation(duration=2.2) + Animation(opacity=0, duration=.3)
        anim.start(t)


# ---------- screens ----------

class Page(Screen):
    kw = {}

    def on_pre_enter(self, *_):
        if self.ids:  # the first screen is entered before its kv rule is applied
            self.refresh()

    def refresh(self):
        pass


class FormPage(Page):
    """A form that warns before its unsaved edits are thrown away."""
    editing = BooleanProperty(False)
    _snapshot = None

    def collect(self):
        raise NotImplementedError

    def mark_clean(self):
        self._snapshot = self.collect()

    def is_dirty(self):
        return self._snapshot is not None and self.collect() != self._snapshot


class HomeScreen(Page):
    greeting = StringProperty('')
    today = StringProperty('')
    stats = ListProperty([0, 0, '—'])
    stat_labels = ListProperty(['', '', ''])
    empty = BooleanProperty(False)
    next = ObjectProperty({}, rebind=True)
    next_when = StringProperty('')
    next_until = StringProperty('')

    def refresh(self):
        now = datetime.now()
        self.greeting = ('Доброй ночи' if now.hour < 5 else 'Доброе утро' if now.hour < 12
                         else 'Добрый день' if now.hour < 18 else 'Добрый вечер')
        self.today = f'{WEEKDAYS_FULL[now.weekday()]}, {now.day} {MONTHS_GEN[now.month - 1]}'
        d = app().db.dashboard()
        self.empty = d['clients'] == 0
        avg = '—' if d['avg_delta'] is None else f"{d['avg_delta']:+.1f}".replace('-', '−')
        self.stats = [d['clients'], d['month'], avg]
        self.stat_labels = [plural(d['clients'], 'клиент', 'клиента', 'клиентов'),
                            f"{plural(d['month'], 'сессия', 'сессии', 'сессий')} в {MONTHS_PREP[now.month - 1]}",
                            'средний сдвиг за сессию']
        upcoming = d['upcoming']
        self.next = upcoming[0] if upcoming else {}
        if upcoming:
            n = upcoming[0]
            self.next_when = f"{human_date(n['meeting_date'])}, {n['meeting_time']}"
            self.next_until = time_until(datetime.fromisoformat(f"{n['meeting_date']}T{n['meeting_time']}"), now)
        fill(self.ids.upcoming, map(session_item, upcoming[1:]))
        fill(self.ids.todo, (session_item(n, todo=True) for n in d['todo']))
        fill(self.ids.recent, map(session_item, d['recent']))

    def load_demo(self):
        demo.seed(app().db)
        app().toast('Демо-данные загружены')
        self.refresh()


class ClientsScreen(Page):
    def refresh(self):
        self.ids.rv.data = [dict(
            viewclass='ClientRow', height=dp(72), client_id=c['client_id'], name=c['full_name'],
            initials=initials(c['full_name']),
            subtitle=(f"{c['session_count']} {plural(c['session_count'], 'сессия', 'сессии', 'сессий')}"
                      + (f" · последняя {human_date(c['last_session']).lower()}" if c['last_session'] else '')))
            for c in app().db.clients(self.ids.query.text)]


class HistoryScreen(Page):
    def refresh(self):
        data, month = [], None
        for n in app().db.notes(search=self.ids.query.text):
            if n['meeting_date'][:7] != month:
                month = n['meeting_date'][:7]
                data.append(dict(viewclass='MonthHeader', height=dp(40), text=month_title(n['meeting_date'])))
            data.append(session_item(n))
        self.ids.rv.data = data


class ClientScreen(Page):
    client = ObjectProperty({}, rebind=True)
    meta = StringProperty('')
    next_text = StringProperty('')
    progress_text = StringProperty('')

    def refresh(self):
        db = app().db
        c = db.client(self.kw['client_id'])
        if c is None:  # deleted while we were further down the stack
            return Clock.schedule_once(lambda _: app().back(force=True))
        self.client = c
        age = f"{c['age']} {plural(c['age'], 'год', 'года', 'лет')}" if c['age'] is not None else ''
        self.meta = ' · '.join(filter(None, [age, c['phone_number']]))
        nxt = db.next_session(c['client_id'])
        self.next_text = f"Следующая встреча: {human_date(nxt['meeting_date']).lower()}, {nxt['meeting_time']}" if nxt else ''
        for box, values in ((self.ids.traits, [c['temperament'], c['perception_type'], c['character_type']]),
                            (self.ids.requests, c['requests'])):
            box.clear_widgets()
            for v in filter(None, values):
                box.add_widget(make('Tag', text=v))
        points = db.progress(c['client_id'])
        finals = [p['final_state_score'] for p in points if p['final_state_score'] is not None]
        if len(finals) >= 2:
            first, last = finals[0], finals[-1]
            verb = 'выросло' if last > first else 'снизилось' if last < first else 'не изменилось'
            tail = f' с {first} до {last}' if last != first else f', {last} из 10'
            self.progress_text = f'Состояние после сессий {verb}{tail}'
        else:
            self.progress_text = ''
        self.ids.chart.selected = -1
        self.ids.chart.points = points
        notes = db.notes(client_id=c['client_id'])
        self.ids.sessions_title.text = f"Сессии · {len(notes)}" if notes else 'Сессий пока нет'
        fill(self.ids.sessions, map(session_item, notes))


class ClientFormScreen(FormPage):
    def refresh(self):
        cid = self.kw.get('client_id')
        self.editing = cid is not None
        c = app().db.client(cid) if cid else {}
        ids = self.ids
        ids.name.text = c.get('full_name') or ''
        ids.age.text = '' if c.get('age') is None else str(c['age'])
        ids.phone.text = c.get('phone_number') or ''
        ids.temperament.value = c.get('temperament') or ''
        ids.perception.value = c.get('perception_type') or ''
        ids.character.text = c.get('character_type') or ''
        ids.anamnesis.text = c.get('anamnesis') or ''
        ids.plan.text = c.get('help_plan') or ''
        ids.requests.clear_widgets()
        for r in c.get('requests') or ['']:
            self.add_request(r)
        ids.scroll.scroll_y = 1
        self.mark_clean()

    def add_request(self, text=''):
        row = Factory.RequestRow()
        row.ids.field.text = text
        row.ids.remove_btn.bind(on_release=lambda _: self.ids.requests.remove_widget(row))
        self.ids.requests.add_widget(row)
        return row

    def collect(self):
        ids = self.ids
        return dict(
            full_name=' '.join(ids.name.text.split()), age=ids.age.text.strip(), phone_number=ids.phone.text.strip(),
            temperament=ids.temperament.value, perception_type=ids.perception.value,
            character_type=ids.character.text.strip(), anamnesis=ids.anamnesis.text.strip(),
            help_plan=ids.plan.text.strip(),
            requests=[r for r in (row.ids.field.text.strip() for row in reversed(ids.requests.children)) if r])

    def save(self):
        data = self.collect()
        if not data['full_name']:
            return app().toast('Укажите имя клиента')
        age = data['age']
        if age and not (age.isdigit() and int(age) <= 120):
            return app().toast('Возраст — число от 0 до 120')
        data['age'] = int(age) if age else None
        cid = app().db.save_client(data, self.kw.get('client_id'))
        app().toast('Клиент сохранён')
        app().back(force=True)
        if not self.editing:
            app().go('client', client_id=cid)

    def delete(self):
        def do():
            app().db.delete_client(self.kw['client_id'])
            app().toast('Клиент и его сессии удалены')
            app().go('clients')
        app().confirm('Удалить клиента?', 'Карточка и все сессии будут удалены без возможности восстановления.', do)


class SessionScreen(Page):
    note = ObjectProperty({}, rebind=True)
    when = StringProperty('')
    delta = StringProperty('')
    tone = StringProperty('')
    summary = StringProperty('')
    complete = BooleanProperty(True)

    def refresh(self):
        n = app().db.note(self.kw['note_id'])
        if n is None:
            return Clock.schedule_once(lambda _: app().back(force=True))
        self.note = n
        self.when = f"{human_date(n['meeting_date'], weekday=True)} · {n['meeting_time']}"
        before, after = n['initial_state_score'], n['final_state_score']
        self.delta, self.tone = delta_text(before, after), tone(before, after)
        d = abs(after - before) if self.tone else 0
        self.summary = {
            'good': f"Состояние улучшилось на {d} {plural(d, 'балл', 'балла', 'баллов')}",
            'bad': f"Состояние ухудшилось на {d} {plural(d, 'балл', 'балла', 'баллов')}",
            'flat': 'Состояние не изменилось',
        }.get(self.tone, 'Оценки не указаны')
        upcoming = datetime.fromisoformat(f"{n['meeting_date']}T{n['meeting_time']}") > datetime.now()
        self.complete = upcoming or (after is not None and bool(n['meeting_outcome']))
        box = self.ids.details
        box.clear_widgets()
        for title, key in (('Запрос', 'request'), ('Ход встречи', 'meeting_progress'),
                           ('Техники', 'techniques_used'), ('Итог', 'meeting_outcome')):
            if n[key]:
                box.add_widget(make('InfoCard', title=title, text=n[key]))


class SessionFormScreen(FormPage):
    client_id = NumericProperty(0)
    client_name = StringProperty('')
    meeting_date = StringProperty('')

    def refresh(self):
        nid = self.kw.get('note_id')
        self.editing = nid is not None
        n = app().db.note(nid) if nid else {}
        ids = self.ids
        if nid:
            self.set_client(n['client_id'], n['full_name'])
        else:
            cid = self.kw.get('client_id')
            c = app().db.client(cid) if cid else None
            self.set_client(cid or 0, c['full_name'] if c else '')
        self.meeting_date = n.get('meeting_date') or date.today().isoformat()
        ids.time.text = n.get('meeting_time') or datetime.now().strftime('%H:%M')
        ids.location.text = n.get('meeting_location') or ''
        ids.location_chips.options = list(dict.fromkeys(LOCATIONS + app().db.known_locations()))
        ids.weather.value = n.get('weather') or ''
        ids.initial_state.text = n.get('initial_state') or ''
        ids.before.value = -1 if n.get('initial_state_score') is None else n['initial_state_score']
        ids.request.text = n.get('request') or ''
        ids.progress.text = n.get('meeting_progress') or ''
        ids.techniques.text = n.get('techniques_used') or ''
        ids.outcome.text = n.get('meeting_outcome') or ''
        ids.final_state.text = n.get('final_state') or ''
        ids.after.value = -1 if n.get('final_state_score') is None else n['final_state_score']
        ids.scroll.scroll_y = 1
        self.mark_clean()

    def set_client(self, client_id, name):
        self.client_id, self.client_name = client_id, name
        c = app().db.client(client_id) if client_id else None
        self.ids.request_chips.options = c['requests'] if c else []

    def pick_client(self):
        Factory.ClientPicker(callback=self.set_client).open()

    def pick_date(self):
        Factory.DatePicker(callback=lambda iso: setattr(self, 'meeting_date', iso)).show(self.meeting_date)

    def collect(self):
        ids = self.ids
        score = lambda v: None if v < 0 else int(v)
        return dict(
            client_id=self.client_id, meeting_date=self.meeting_date, meeting_time=ids.time.text.strip(),
            meeting_location=ids.location.text.strip(), weather=ids.weather.value,
            initial_state=ids.initial_state.text.strip(), initial_state_score=score(ids.before.value),
            request=ids.request.text.strip(), meeting_progress=ids.progress.text.strip(),
            techniques_used=ids.techniques.text.strip(), meeting_outcome=ids.outcome.text.strip(),
            final_state=ids.final_state.text.strip(), final_state_score=score(ids.after.value))

    def save(self):
        data = self.collect()
        if not data['client_id']:
            return app().toast('Выберите клиента')
        t = data['meeting_time']
        if len(t) == 4 and t[1] == ':':
            data['meeting_time'] = t = '0' + t
        if not valid_time(t):
            return app().toast('Время в формате ЧЧ:ММ, например 14:30')
        app().db.save_note(data, self.kw.get('note_id'))
        app().toast('Сессия сохранена')
        app().back(force=True)

    def delete(self):
        def do():
            app().db.delete_note(self.kw['note_id'])
            app().toast('Сессия удалена')
            app().back(force=True)
        app().confirm('Удалить сессию?', 'Запись о встрече будет удалена без возможности восстановления.', do)


class SettingsScreen(Page):
    info = StringProperty('')
    folder = StringProperty('')

    def refresh(self):
        d = app().db.dashboard()
        self.info = (f"{d['clients']} {plural(d['clients'], 'клиент', 'клиента', 'клиентов')} · "
                     f"{d['sessions']} {plural(d['sessions'], 'сессия', 'сессии', 'сессий')}")
        self.folder = app().export_dir()

    def _stamp(self):
        return datetime.now().strftime('%Y-%m-%d_%H-%M')

    def export_json(self):
        path = os.path.join(app().export_dir(), f'psychonotes_{self._stamp()}.json')
        app().db.export_json(path)
        app().toast(f'Копия сохранена: {os.path.basename(path)}')

    def export_csv(self):
        path = os.path.join(app().export_dir(), f'sessions_{self._stamp()}.csv')
        count = app().db.export_csv(path)
        app().toast(f'{count} {plural(count, "сессия", "сессии", "сессий")} → {os.path.basename(path)}')

    def import_json(self):
        folder = app().export_dir()
        files = sorted((f for f in os.listdir(folder) if f.endswith('.json')),
                       key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)
        if not files:
            return app().toast('Положите файл .json в папку резервных копий')
        picker = Factory.BackupPicker()
        for f in files[:8]:
            row = make('PickRow', text=f)
            row.bind(on_release=lambda _, f=f: (picker.dismiss(), self._restore(os.path.join(folder, f))))
            picker.ids.list.add_widget(row)
        picker.open()

    def _restore(self, path):
        def do():
            try:
                clients, notes = app().db.import_json(path)
            except (OSError, ValueError) as e:
                return app().toast(str(e))
            app().toast(f'Восстановлено: {clients} клиентов, {notes} сессий')
            self.refresh()
        app().confirm('Восстановить из копии?', 'Текущие данные будут заменены данными из файла.', do,
                      ok_text='Восстановить')

    def load_demo(self):
        demo.seed(app().db)
        app().toast('Демо-данные добавлены')
        self.refresh()

    def wipe(self):
        def do():
            app().db.wipe()
            app().toast('Все данные удалены')
            self.refresh()
        app().confirm('Удалить все данные?', 'Все клиенты и сессии будут удалены. Сначала сделайте резервную копию.', do)


# ---------- app ----------

class PsychoNotesApp(App):
    title = 'PsychoNotes'
    theme = StringProperty('light')
    nav = BooleanProperty(True)
    tab = StringProperty('home')
    (bg, tint1, tint2, tint3, tint4, surface, glass, glass_strong, stroke, shadow, surface2, text, muted, border,
     ink, accent, accent_fill, accent_soft, hero, danger, danger_soft, warn, warn_soft, score_low, score_mid,
     score_high, series_before, series_after) = (ColorProperty() for _ in range(28))
    sheen = ObjectProperty(None)
    grain = ObjectProperty(None)

    def get_application_config(self):
        return super().get_application_config(os.path.join(self.user_data_dir, '%(appname)s.ini'))

    def build_config(self, config):
        config.setdefaults('ui', {'theme': 'light'})

    def build(self):
        self.icon = os.path.join(BASE_DIR, 'assets', 'icon.png')
        self.db = Database(self.db_path())
        self.set_theme(self.config.get('ui', 'theme'))
        self.stack = []
        self.sheen = sheen_texture()
        self.grain = grain_texture()
        resource_add_path(BASE_DIR)
        Builder.load_file(os.path.join(BASE_DIR, 'ui.kv'))
        Window.softinput_mode = 'below_target'
        Window.bind(on_keyboard=self.on_key)
        return Root()

    def on_start(self):
        self.root.ids.sm.get_screen('home').refresh()

    def on_stop(self):
        self.db.close()

    def db_path(self):
        if os.environ.get('PSYCHONOTES_DB'):
            return os.environ['PSYCHONOTES_DB']
        path = os.path.join(self.user_data_dir, 'psychologist_notes.db')
        legacy = os.path.join(BASE_DIR, 'psychologist_notes.db')  # where v1 kept it
        if not os.path.exists(path) and os.path.exists(legacy):
            shutil.copy2(legacy, path)
        return path

    def export_dir(self):
        path = None
        if platform == 'android':  # app-specific external dir: visible in file managers, no permission needed
            try:
                from jnius import autoclass
                path = autoclass('org.kivy.android.PythonActivity').mActivity.getExternalFilesDir(None).getAbsolutePath()
            except Exception:
                path = self.user_data_dir
        path = path or os.path.join(os.path.expanduser('~'), 'Documents', 'PsychoNotes')
        os.makedirs(path, exist_ok=True)
        return path

    def set_theme(self, name):
        name = name if name in THEMES else 'light'
        for key, value in THEMES[name].items():
            setattr(self, key, get_color_from_hex(value))
        Window.clearcolor = self.bg
        self.theme = name
        self.config.set('ui', 'theme', name)
        self.config.write()

    # navigation: tabs reset the stack, everything else pushes onto it
    def go(self, name, **kw):
        sm = self.root.ids.sm
        if name in TABS:
            self.stack.clear()
            self.tab = name
            sm.transition = NoTransition()  # tab bars switch instantly; also avoids FBO-based fades
        else:
            self.stack.append((sm.current, sm.current_screen.kw))
            sm.transition = SlideTransition(direction='left', duration=.18)
        self._show(name, kw)

    def back(self, force=False):
        if not self.stack:
            return False
        screen = self.root.ids.sm.current_screen
        if not force and isinstance(screen, FormPage) and screen.is_dirty():
            self.confirm('Выйти без сохранения?', 'Внесённые изменения будут потеряны.',
                         lambda: self.back(force=True), ok_text='Выйти')
            return True
        self.root.ids.sm.transition = SlideTransition(direction='right', duration=.18)
        self._show(*self.stack.pop())
        return True

    def _show(self, name, kw):
        sm = self.root.ids.sm
        if not sm.has_screen(name):
            sm.add_widget(getattr(Factory, SCREENS[name])(name=name))
        screen = sm.get_screen(name)
        screen.kw = kw
        self.nav = name in TABS
        if sm.current == name:
            screen.refresh()
        sm.current = name

    def on_key(self, _win, key, *_):
        if key == 27:  # Esc / Android back
            return self.back()

    def toast(self, text):
        self.root.toast(text)

    def confirm(self, title, text, on_ok, ok_text='Удалить'):
        Dialog(title=title, text=text, callback=on_ok, ok_text=ok_text, danger=ok_text == 'Удалить').open()


if __name__ == '__main__':
    PsychoNotesApp().run()
