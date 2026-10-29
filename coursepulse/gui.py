from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from coursepulse.core import Data, build, now
from coursepulse.io import export, update


def launch(directory):
    root=tk.Tk();root.title('CoursePulse — учебная группа');root.geometry('1080x720')
    style=ttk.Style();style.theme_use('clam');style.configure('Treeview',rowheight=28)
    data=Data.load(directory)
    header=ttk.Frame(root,padding=16);header.pack(fill='x')
    ttk.Label(header,text='CoursePulse',font=('Arial',22,'bold')).pack(anchor='w')
    ttk.Label(header,text='Посещаемость, домашние задания и поддержка слушателей').pack(anchor='w')
    notebook=ttk.Notebook(root);notebook.pack(fill='both',expand=True,padx=16,pady=10)
    summary=ttk.Frame(notebook,padding=12);form=ttk.Frame(notebook,padding=18)
    notebook.add(summary,text='Сводка');notebook.add(form,text='Внести отметку')
    tree=ttk.Treeview(summary,columns=('name','attendance','overdue','revision','unknown','priority'),show='headings')
    for key,title,width in [('name','Слушатель',230),('attendance','Посещаемость',135),('overdue','Просрочено',100),('revision','Доработка',100),('unknown','Нет отметок',110),('priority','Приоритет',130)]:
        tree.heading(key,text=title);tree.column(key,width=width)
    tree.pack(fill='both',expand=True)
    info=tk.StringVar();ttk.Label(summary,textvariable=info).pack(anchor='w',pady=8)
    as_of=tk.StringVar(value=now())
    controls=ttk.Frame(summary);controls.pack(fill='x')
    ttk.Label(controls,text='Срез на дату').pack(side='left');ttk.Entry(controls,textvariable=as_of,width=34).pack(side='left',padx=8)
    def refresh():
        report=build(Data.load(directory),as_of.get())
        tree.delete(*tree.get_children())
        for r in report.summary.itertuples(index=False):
            rate='нет данных' if r.attendance_rate is None or r.attendance_rate!=r.attendance_rate else f'{r.attendance_rate:.0%}'
            tree.insert('', 'end',iid=r.student_id,values=(r.name,rate,r.overdue,r.revision,r.unknown,r.priority))
        info.set(f'Слушателей: {len(report.summary)}. Требуется связь: {len(report.contacts)}. Данные: {Path(directory).resolve()}')
        return report
    def guarded(function):
        def action():
            try:function()
            except Exception as error:messagebox.showerror('Ошибка',str(error))
        return action
    def report_file():
        result=export(refresh(),'reports/current');webbrowser.open((result/'report.html').resolve().as_uri())
    ttk.Button(controls,text='Сейчас',command=guarded(lambda:(as_of.set(now()),refresh()))).pack(side='left')
    ttk.Button(controls,text='Обновить',command=guarded(refresh)).pack(side='left',padx=8)
    ttk.Button(controls,text='Excel и отчёт',command=guarded(report_file)).pack(side='left')
    ttk.Label(form,text='Все изменения сохраняются в CSV. Отчёт обновляется после сохранения.').grid(row=0,column=0,columnspan=3,sticky='w',pady=10)
    ids=data.tables['students'].student_id.tolist();lessons=data.tables['sessions'].session_id.tolist();tasks=data.tables['assignments'].assignment_id.tolist()
    user=tk.StringVar(value=ids[0] if ids else '');lesson=tk.StringVar(value=lessons[0] if lessons else '');state=tk.StringVar(value='present');reason=tk.StringVar()
    task=tk.StringVar(value=tasks[0] if tasks else '');task_state=tk.StringVar(value='submitted');submitted=tk.StringVar(value=now());comment=tk.StringVar()
    fields=[('Слушатель',user,ids),('Занятие',lesson,lessons),('Статус посещения',state,['present','late','absent','excused']),('Причина пропуска',reason,None),('Домашнее задание',task,tasks),('Статус работы',task_state,['submitted','accepted','revision']),('Время сдачи',submitted,None),('Комментарий преподавателя',comment,None)]
    for i,(label,variable,values) in enumerate(fields,1):
        ttk.Label(form,text=label).grid(row=i,column=0,sticky='w',pady=8)
        widget=ttk.Entry(form,textvariable=variable,width=60) if values is None else ttk.Combobox(form,textvariable=variable,values=values,state='readonly',width=57)
        widget.grid(row=i,column=1,sticky='w',padx=16)
    def save_attendance():
        update(directory,'attendance',{'student_id':user.get(),'session_id':lesson.get(),'status':state.get(),'reason':reason.get()});refresh();messagebox.showinfo('Готово','Посещаемость сохранена')
    def save_submission():
        update(directory,'submissions',{'student_id':user.get(),'assignment_id':task.get(),'submitted_at':submitted.get(),'status':task_state.get(),'comment':comment.get()});refresh();messagebox.showinfo('Готово','Работа сохранена')
    ttk.Button(form,text='Сохранить посещаемость',command=guarded(save_attendance)).grid(row=10,column=0,pady=18)
    ttk.Button(form,text='Сохранить домашнюю работу',command=guarded(save_submission)).grid(row=10,column=1,sticky='w',padx=16)
    guarded(refresh)();root.mainloop()
