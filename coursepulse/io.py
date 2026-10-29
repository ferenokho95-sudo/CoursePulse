from pathlib import Path
from tempfile import NamedTemporaryFile
import html
import json
import pandas as pd
from coursepulse.core import Data, SCHEMAS, KEYS


def update(directory, name, record):
    """Single-user atomic upsert; validate the whole data set before replacing a CSV."""
    directory = Path(directory)
    data = Data.load(directory)
    frame = data.tables[name]
    if set(record) != set(SCHEMAS[name]):
        raise ValueError(f'Нужны поля: {SCHEMAS[name]}')
    mask = pd.Series(True, index=frame.index)
    for key in KEYS[name]:
        mask &= frame[key].eq(record[key])
    frame = pd.concat([frame.loc[~mask], pd.DataFrame([record], columns=SCHEMAS[name])], ignore_index=True)
    if frame.duplicated(KEYS[name]).any():
        raise ValueError('Повтор ключа')
    data.tables[name] = frame
    data.validate()
    path = directory/f'{name}.csv'
    with NamedTemporaryFile(mode='w', encoding='utf-8-sig', newline='', suffix='.csv', dir=directory, delete=False) as handle:
        temporary = Path(handle.name)
        frame.to_csv(handle, index=False)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def safe(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'"+value
    return value


def frames(report):
    return {'Сводка': report.summary, 'Связаться': report.contacts,
            'Посещаемость': report.attendance, 'Домашние работы': report.homework}


def export(report, output, excel=True):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    for name, frame in [('summary',report.summary),('contacts',report.contacts),('attendance',report.attendance),('homework',report.homework)]:
        frame.map(safe).to_csv(output/f'{name}.csv', index=False, encoding='utf-8-sig')
    payload = {'as_of': report.as_of, **{name: json.loads(frame.to_json(orient='records', force_ascii=False))
                                      for name, frame in frames(report).items()}}
    (output/'report.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    data_issues = report.summary[(report.summary.unknown>0) | (report.summary.missing_reasons>0)]
    content = f'''<!doctype html><html lang="ru"><meta charset="utf-8"><title>CoursePulse</title>
    <style>body{{font:15px system-ui;color:#22334b;margin:35px;background:#f4f6fa}}section{{background:white;padding:24px;border-radius:12px;margin:18px 0;overflow:auto}}table{{border-collapse:collapse;white-space:nowrap}}th,td{{padding:9px 12px;border-bottom:1px solid #ddd;text-align:left}}th{{background:#233e60;color:white}}h1{{margin-bottom:5px}}</style>
    <h1>CoursePulse</h1><p>Состояние на {html.escape(report.as_of)}. Отчёт обновляется при повторном запуске.</p>
    <section><h2>Сводка группы</h2>{report.summary.to_html(index=False,na_rep='нет данных',escape=True)}</section>
    <section><h2>Связаться со слушателями</h2>{report.contacts.drop(columns=['draft']).to_html(index=False,escape=True)}</section>
    <section><h2>Уточнить данные у куратора</h2><p>Неизвестные отметки не считаются пропусками. Уточните также причины отсутствия.</p>{data_issues[['student_id','name','unknown','missing_reasons']].to_html(index=False,escape=True)}</section></html>'''
    (output/'report.html').write_text(content, encoding='utf-8')
    drafts = ['# Черновики сообщений', '', 'Проверьте информацию перед отправкой. Программа не отправляет сообщения.', '']
    for row in report.contacts.itertuples(index=False):
        drafts.extend([f'## {row.name} ({row.student_id})', '', f'Контакт: {row.contact}', '', row.draft, ''])
    (output/'message_drafts.md').write_text('\n'.join(drafts), encoding='utf-8')
    if excel:
        from coursepulse.xlsx import write_excel
        write_excel(report, output/'course_report.xlsx')
    return output
