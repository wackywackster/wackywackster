import tkinter as tk
import random
from tkinter import *
score = 0


num = [1, 2, 3, 4, 5, 6, 7, 8, 9]


def submit():
    if entry1.get() == str(resultPLUS()):
        global score
       
        indicator.config(text="Correct!", fg="green", font=("Courier", 18))
        entry1.delete("0", 'end')
        score = score + 1
        try_again()
    else:
        indicator.config(text="Wrong!", fg="red", font=("Courier", 18))
        entry1.delete("0", 'end')
        try_again()


def try_again():
    canvas.delete(btn)
    indicator.config(text="")
    try_again.num1update = random.choice(num)
    try_again.num2update = random.choice(num)
    question = tk.Label(app, text=f"{try_again.num1update}+{try_again.num2update}")
    question.config(font=('helvetica', 40))
    canvas.create_window(400, 300, window=question)


def resultPLUS():
    try_again
    return try_again.num1update + try_again.num2update


app = Tk()
app.title("Math For Kids")
canvas = Canvas(app, width=800, height=600)
canvas.pack()

title = tk.Label(app, text='Math Quiz')
title.config(font=('helvetica', 40))
canvas.create_window(400, 50, window=title)

app.resizable(False, False)
start = tk.Button(text='Start', command=try_again, bg='brown', fg='white', font=('helvetica', 15, 'bold'))
btn = canvas.create_window(400, 150, window=start)

entry1 = tk.Entry (app, width=30, font=('helvetica', 20))
canvas.create_window(400, 450, window=entry1)

submit = tk.Button(text='Submit', command=submit, bg='brown', fg='white', font=('helvetica', 15, 'bold'))
canvas.create_window(400, 500, window=submit)

indicator = tk.Label(app, text='')
title.config(font=('helvetica', 40))
canvas.create_window(400, 350, window=indicator)

scores = tk.Label(app, text=score)
title.config(font=('helvetica', 30))
canvas.create_window(50, 50, window=scores)


trydagain = tk.Button(text='Try Again', command=try_again, bg='brown', fg='white', font=('helvetica', 15, 'bold'))
canvas.create_window(400, 550, window=trydagain)
app.mainloop()

