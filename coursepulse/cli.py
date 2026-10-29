import argparse
import json
from coursepulse.core import Data, build, now
from coursepulse.io import export, update
from coursepulse.sample import initialize


def main():
    parser=argparse.ArgumentParser(description='CoursePulse — трекер учебной группы')
    commands=parser.add_subparsers(dest='command',required=True)
    init=commands.add_parser('init');init.add_argument('--data',default='data/work');init.add_argument('--demo',action='store_true')
    report=commands.add_parser('report');report.add_argument('--data',default='data/demo');report.add_argument('--output',default='reports/current');report.add_argument('--as-of');report.add_argument('--no-excel',action='store_true')
    gui=commands.add_parser('gui');gui.add_argument('--data',default='data/demo')
    attendance=commands.add_parser('attendance');attendance.add_argument('--data',default='data/demo');attendance.add_argument('--student',required=True);attendance.add_argument('--session',required=True);attendance.add_argument('--status',choices=['present','late','absent','excused'],required=True);attendance.add_argument('--reason',default='')
    submission=commands.add_parser('submission');submission.add_argument('--data',default='data/demo');submission.add_argument('--student',required=True);submission.add_argument('--assignment',required=True);submission.add_argument('--status',choices=['submitted','accepted','revision'],required=True);submission.add_argument('--submitted-at',default=None);submission.add_argument('--comment',default='')
    args=parser.parse_args()
    try:
        if args.command=='init':
            initialize(args.data,args.demo);print('Созданы CSV:',args.data)
        elif args.command=='report':
            r=build(Data.load(args.data),args.as_of);export(r,args.output,excel=not args.no_excel)
            print(json.dumps({'students':len(r.summary),'contacts':len(r.contacts),'as_of':r.as_of,'output':args.output},ensure_ascii=False,indent=2))
        elif args.command=='attendance':
            update(args.data,'attendance',{'student_id':args.student,'session_id':args.session,'status':args.status,'reason':args.reason});print('Отметка сохранена')
        elif args.command=='submission':
            update(args.data,'submissions',{'student_id':args.student,'assignment_id':args.assignment,'submitted_at':args.submitted_at or now(),'status':args.status,'comment':args.comment});print('Статус работы сохранён')
        else:
            from coursepulse.gui import launch
            launch(args.data)
    except (ValueError,OSError) as error:
        parser.exit(1,f'Ошибка: {error}\n')


if __name__=='__main__':main()
