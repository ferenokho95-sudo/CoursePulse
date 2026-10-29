from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd

MOSCOW = timezone(timedelta(hours=3))
SCHEMAS = {
    'students': ['student_id', 'name', 'group', 'contact', 'enrolled_at', 'ended_at'],
    'sessions': ['session_id', 'group', 'title', 'start_at'],
    'attendance': ['student_id', 'session_id', 'status', 'reason'],
    'assignments': ['assignment_id', 'group', 'title', 'released_at', 'due_at'],
    'submissions': ['student_id', 'assignment_id', 'submitted_at', 'status', 'comment'],
}
KEYS = {'students': ['student_id'], 'sessions': ['session_id'],
        'attendance': ['student_id', 'session_id'], 'assignments': ['assignment_id'],
        'submissions': ['student_id', 'assignment_id']}
ATTENDANCE = {'present', 'late', 'absent', 'excused'}
SUBMISSIONS = {'submitted', 'accepted', 'revision'}


def instant(value):
    try:
        result = pd.Timestamp(value)
    except Exception as error:
        raise ValueError(f'Некорректная дата: {value!r}') from error
    if pd.isna(result) or result.tzinfo is None:
        raise ValueError('У даты должен быть часовой пояс, например 2026-10-29T18:00:00+03:00')
    return result.tz_convert('UTC')


def now():
    return datetime.now(MOSCOW).isoformat(timespec='seconds')


@dataclass
class Data:
    tables: dict

    @classmethod
    def load(cls, directory):
        tables = {}
        for name, columns in SCHEMAS.items():
            frame = pd.read_csv(Path(directory)/f'{name}.csv', dtype=str, keep_default_na=False)
            if frame.columns.tolist() != columns:
                raise ValueError(f'{name}.csv: ожидаются столбцы {columns}')
            if frame.duplicated(KEYS[name]).any():
                raise ValueError(f'{name}.csv: повтор ключа {KEYS[name]}')
            for key in KEYS[name]:
                if frame[key].str.strip().eq('').any():
                    raise ValueError(f'{name}.csv: пустой {key}')
            tables[name] = frame
        data = cls(tables)
        data.validate()
        return data

    def validate(self):
        t = self.tables
        students = t['students'].set_index('student_id')
        for student in t['students'].itertuples(index=False):
            if not student.name.strip() or not student.group.strip():
                raise ValueError('У слушателя должны быть имя и группа')
            if student.ended_at and instant(student.ended_at) <= instant(student.enrolled_at):
                raise ValueError('Дата выхода должна быть позже даты зачисления')
            instant(student.enrolled_at)
        for session in t['sessions'].itertuples(index=False):
            instant(session.start_at)
            if not session.group.strip() or not session.title.strip():
                raise ValueError('У занятия должны быть группа и тема')
        for task in t['assignments'].itertuples(index=False):
            if instant(task.due_at) < instant(task.released_at):
                raise ValueError('Дедлайн раньше выдачи задания')
            if not task.group.strip() or not task.title.strip():
                raise ValueError('У задания должны быть группа и название')
        for name, foreign, target, statuses in [
            ('attendance', 'session_id', 'sessions', ATTENDANCE),
            ('submissions', 'assignment_id', 'assignments', SUBMISSIONS),
        ]:
            entities = t[target].set_index(foreign)
            for record in t[name].itertuples(index=False):
                if record.student_id not in students.index or getattr(record, foreign) not in entities.index:
                    raise ValueError(f'{name}: неизвестный слушатель или объект')
                person = students.loc[record.student_id]
                entity = entities.loc[getattr(record, foreign)]
                if person['group'] != entity['group']:
                    raise ValueError(f'{name}: слушатель из другой группы')
                eligible_at = entity['start_at'] if name == 'attendance' else entity['released_at']
                if not active(person, instant(eligible_at)):
                    raise ValueError(f'{name}: запись вне периода обучения слушателя')
                if record.status not in statuses:
                    raise ValueError(f'{name}: недопустимый статус {record.status}')
                if name == 'submissions' and instant(record.submitted_at) < instant(entity['released_at']):
                    raise ValueError('Работа сдана раньше выдачи задания')


def active(person, point):
    return instant(person['enrolled_at']) <= point and (not person['ended_at'] or point < instant(person['ended_at']))


@dataclass
class Report:
    as_of: str
    summary: pd.DataFrame
    contacts: pd.DataFrame
    attendance: pd.DataFrame
    homework: pd.DataFrame


def build(data, as_of=None, attendance_threshold=0.7):
    cutoff = instant(as_of or now())
    if not 0 <= attendance_threshold <= 1:
        raise ValueError('Порог посещаемости должен быть от 0 до 1')
    t = data.tables
    attendance_index = {(r.student_id, r.session_id): r for r in t['attendance'].itertuples(index=False)}
    submission_index = {(r.student_id, r.assignment_id): r for r in t['submissions'].itertuples(index=False)}
    summary, contact, attendance_rows, task_rows = [], [], [], []
    for _, person in t['students'].sort_values(['group', 'name']).iterrows():
        sid = person.student_id
        if instant(person.enrolled_at) > cutoff:
            continue
        counts = {status: 0 for status in [*sorted(ATTENDANCE), 'unknown']}
        missing_reasons = 0
        for session in t['sessions'].itertuples(index=False):
            point = instant(session.start_at)
            if session.group != person['group'] or point > cutoff or not active(person, point):
                continue
            record = attendance_index.get((sid, session.session_id))
            status = record.status if record else 'unknown'
            reason = record.reason if record else ''
            counts[status] += 1
            if status in {'absent', 'excused'} and not reason.strip():
                missing_reasons += 1
            attendance_rows.append({'student_id': sid, 'name': person['name'], 'session_id': session.session_id,
                                    'title': session.title, 'start_at': session.start_at, 'status': status, 'reason': reason})
        expected = sum(counts.values())
        denominator = expected-counts['excused']
        # Missing marks are unknown, never silently counted as absences.
        rate = (counts['present']+counts['late'])/denominator if denominator and not counts['unknown'] else None
        due = accepted = overdue = revision = waiting = upcoming = 0
        for task in t['assignments'].itertuples(index=False):
            release, deadline = instant(task.released_at), instant(task.due_at)
            if task.group != person['group'] or release > cutoff or not active(person, release):
                continue
            record = submission_index.get((sid, task.assignment_id))
            if record and instant(record.submitted_at) > cutoff:
                record = None
            state = record.status if record else ('overdue' if deadline < cutoff else 'not_started')
            is_due = deadline < cutoff
            due += int(is_due)
            accepted += int(is_due and state == 'accepted')
            overdue += int(state == 'overdue')
            revision += int(state == 'revision')
            waiting += int(state == 'submitted')
            if state == 'not_started' and deadline <= cutoff+pd.Timedelta(hours=48):
                upcoming += 1
            task_rows.append({'student_id': sid, 'name': person['name'], 'assignment_id': task.assignment_id,
                              'title': task.title, 'due_at': task.due_at, 'state': state,
                              'submitted_at': record.submitted_at if record else '',
                              'late': bool(record and instant(record.submitted_at) > deadline),
                              'comment': record.comment if record else ''})
        reasons, actions = [], []
        if overdue:
            reasons.append(f'Просрочено работ: {overdue}'); actions.append('Уточнить сложности и согласовать срок сдачи')
        if revision:
            reasons.append(f'Работ на доработке: {revision}'); actions.append('Уточнить, понятна ли обратная связь преподавателя')
        if counts['absent'] >= 2 or (rate is not None and denominator >= 3 and rate < attendance_threshold):
            reasons.append(f'Пропусков: {counts["absent"]}'); actions.append('Уточнить причины пропусков и предложить план возвращения')
        if upcoming:
            reasons.append(f'Дедлайн в ближайшие 48 часов: {upcoming}'); actions.append('Напомнить о дедлайне и доступных материалах')
        is_active = active(person, cutoff)
        priority = 'высокий' if overdue or counts['absent'] >= 2 else ('обычный' if reasons else 'не требуется')
        if reasons and is_active:
            message = (f'Здравствуйте, {person["name"]}! Хочу уточнить, как продвигается обучение. '
                       f'{"; ".join(reasons)}. Подскажите, нужна ли помощь и когда будет удобно вернуться к заданиям?')
            contact.append({'student_id': sid, 'name': person['name'], 'group': person['group'], 'contact': person.contact,
                            'priority': priority, 'reason': '; '.join(reasons), 'action': '; '.join(dict.fromkeys(actions)),
                            'draft': message})
        summary.append({'student_id': sid, 'name': person['name'], 'group': person['group'], 'active': is_active,
                        'expected': expected, 'attended': counts['present']+counts['late'], 'absent': counts['absent'],
                        'excused': counts['excused'], 'unknown': counts['unknown'], 'attendance_rate': rate,
                        'due': due, 'accepted': accepted, 'overdue': overdue, 'revision': revision,
                        'waiting_review': waiting, 'completion_rate': accepted/due if due else None,
                        'missing_reasons': missing_reasons, 'priority': priority if is_active else 'завершил обучение'})
    summary_cols = ['student_id','name','group','active','expected','attended','absent','excused','unknown',
                    'attendance_rate','due','accepted','overdue','revision','waiting_review','completion_rate','missing_reasons','priority']
    contact_cols = ['student_id','name','group','contact','priority','reason','action','draft']
    contacts = pd.DataFrame(contact, columns=contact_cols)
    if not contacts.empty:
        contacts['_rank'] = contacts.priority.map({'высокий': 0, 'обычный': 1})
        contacts = contacts.sort_values(['_rank','group','name']).drop(columns='_rank').reset_index(drop=True)
    return Report(cutoff.tz_convert(MOSCOW).isoformat(), pd.DataFrame(summary, columns=summary_cols), contacts,
                  pd.DataFrame(attendance_rows, columns=['student_id','name','session_id','title','start_at','status','reason']),
                  pd.DataFrame(task_rows, columns=['student_id','name','assignment_id','title','due_at','state','submitted_at','late','comment']))
