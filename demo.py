"""Fictional sample data, so the app can be explored without entering anything."""
from datetime import date, timedelta

CLIENTS = [
    dict(full_name='Анна Соколова', age=29, phone_number='+7 900 123-45-67', temperament='Меланхолик',
         character_type='Тревожно-мнительный', perception_type='Аудиал',
         anamnesis='Повышенная тревожность последние полгода, связывает с переходом на новую работу. '
                   'Нарушения сна, сложности с концентрацией.',
         help_plan='1. Психоэдукация о тревоге.\n2. Дыхательные техники и ведение дневника.\n'
                   '3. Работа с катастрофизацией (КПТ).',
         requests=['Тревога на работе', 'Нарушения сна']),
    dict(full_name='Михаил Орлов', age=41, phone_number='+7 911 555-01-02', temperament='Холерик',
         character_type='Эпилептоидный', perception_type='Кинестетик',
         anamnesis='Вспышки раздражительности в семье, конфликт с сыном-подростком.',
         help_plan='Осознавание триггеров, навыки саморегуляции, совместная сессия с сыном.',
         requests=['Контроль гнева', 'Отношения с сыном']),
    dict(full_name='Елена Ким', age=34, phone_number='+7 925 777-88-99', temperament='Сангвиник',
         character_type='Демонстративный', perception_type='Визуал',
         anamnesis='Эмоциональное выгорание, потеря интереса к профессии дизайнера.',
         help_plan='Ресурсное состояние, ревизия ценностей, план восстановления.',
         requests=['Выгорание', 'Поиск смысла в работе']),
    dict(full_name='Дмитрий Волков', age=23, phone_number='', temperament='Флегматик',
         character_type='Шизоидный', perception_type='Дигитал',
         anamnesis='Трудности в общении, социальная изоляция после переезда.',
         help_plan='Постепенная экспозиция, социальные навыки.',
         requests=['Социальная тревожность']),
]

TECHNIQUES = ['Дыхание 4-7-8, когнитивное реструктурирование', 'Работа с метафорическими картами',
              'Техника «пустого стула»', 'Сканирование тела, заземление', 'Сократовский диалог',
              'Арт-терапия: рисунок состояния', 'Домашнее задание: дневник мыслей']
OUTCOMES = ['Клиент сформулировал ресурсные убеждения', 'Снижение напряжения к концу сессии',
            'Найдена связь между триггером и реакцией', 'Договорились о домашнем задании',
            'Появился план действий на неделю']
WEATHER = ['Ясно', 'Облачно', 'Дождь', 'Снег', 'Ветрено']


def seed(db, today=None):
    today = today or date.today()
    for i, c in enumerate(CLIENTS):
        cid = db.save_client(c)
        sessions = 7 - i
        for k in range(sessions):
            day = today - timedelta(days=7 * (sessions - k) + i)
            before = min(9, 2 + k // 2 + i % 2)
            db.save_note(dict(
                client_id=cid, meeting_date=day.isoformat(), meeting_time=f'{10 + i * 2}:00',
                meeting_location='Онлайн' if (k + i) % 3 == 0 else 'Кабинет',
                weather=WEATHER[(k + i) % len(WEATHER)],
                initial_state='Напряжение, усталость' if before < 5 else 'Спокойнее, чем обычно',
                initial_state_score=before, request=c['requests'][k % len(c['requests'])],
                meeting_progress='Обсудили события недели, разобрали ключевую ситуацию.',
                techniques_used=TECHNIQUES[(k + i) % len(TECHNIQUES)],
                meeting_outcome=OUTCOMES[(k * 2 + i) % len(OUTCOMES)],
                final_state='Легче, появилась ясность', final_state_score=min(10, before + 2 + k % 2)))
        if i == 2:  # yesterday's session, not written up yet
            db.save_note(dict(client_id=cid, meeting_date=(today - timedelta(days=1)).isoformat(),
                              meeting_time='17:00', meeting_location='Кабинет', initial_state='Усталость',
                              initial_state_score=4, request=c['requests'][0]))
        if i < 2:  # an upcoming appointment
            db.save_note(dict(client_id=cid, meeting_date=(today + timedelta(days=i + 1)).isoformat(),
                              meeting_time=f'{11 + i * 3}:30', meeting_location='Кабинет',
                              request=c['requests'][0]))
