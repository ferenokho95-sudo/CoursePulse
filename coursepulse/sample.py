from pathlib import Path
import csv
from coursepulse.core import SCHEMAS


def initialize(directory, demo=False):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    if any((directory/f'{name}.csv').exists() for name in SCHEMAS):
        raise ValueError('В папке уже есть данные. Выберите другую папку; файлы не перезаписаны.')
    records = {name: [] for name in SCHEMAS}
    if demo:
        names = ['Анна Демонстрационная','Борис Примеров','Вера Учебная','Глеб Тестовый','Дарья Примерная','Егор Учебный']
        for i, name in enumerate(names,1):
            records['students'].append([f'S{i:03}', name, 'AI-01', f'student{i}@example.com', '2026-10-01T00:00:00+03:00', ''])
        for i, day in enumerate([5,12,19,26,31],1):
            records['sessions'].append([f'L{i:02}','AI-01',f'Занятие {i}',f'2026-10-{day:02}T19:00:00+03:00'])
        for sid in range(1,7):
            for lesson in range(1,5):
                if sid==4 and lesson==3: continue
                status, reason = 'present', ''
                if sid==2 and lesson in [2,3]: status,reason='absent','Рабочая смена' if lesson==2 else ''
                if sid==3 and lesson==2: status,reason='excused','Предупредила куратора'
                if sid==5 and lesson==4: status='late'
                records['attendance'].append([f'S{sid:03}',f'L{lesson:02}',status,reason])
        records['assignments'] = [
            ['HW01','AI-01','Python и pandas','2026-10-05T20:00:00+03:00','2026-10-15T23:59:00+03:00'],
            ['HW02','AI-01','Анализ датасета','2026-10-19T20:00:00+03:00','2026-10-28T23:59:00+03:00'],
            ['HW03','AI-01','Метрики классификации','2026-10-26T20:00:00+03:00','2026-10-30T23:59:00+03:00'],
        ]
        for sid in range(1,7):
            if sid!=2:
                records['submissions'].append([f'S{sid:03}','HW01','2026-10-14T17:00:00+03:00','accepted','Зачтено'])
            if sid in [1,5,6]:
                records['submissions'].append([f'S{sid:03}','HW02','2026-10-27T17:00:00+03:00','accepted','Зачтено'])
            if sid==3:
                records['submissions'].append(['S003','HW02','2026-10-28T17:00:00+03:00','revision','Добавить объяснение выводов'])
            if sid==4:
                records['submissions'].append(['S004','HW02','2026-10-28T21:00:00+03:00','submitted','Ожидает проверки'])
            if sid==1:
                records['submissions'].append(['S001','HW03','2026-10-29T10:00:00+03:00','accepted','Сдано заранее'])
    for name, columns in SCHEMAS.items():
        with (directory/f'{name}.csv').open('w', encoding='utf-8-sig',newline='') as handle:
            writer=csv.writer(handle);writer.writerow(columns);writer.writerows(records[name])
