import tkinter as tk
from tkinter import messagebox
import pygubu

import sys
import os

class Application:
    def __init__(self, master):
        self.master = master

        self.builder = builder = pygubu.Builder()

        builder.add_from_file(os.path.dirname(__file__)+'/tk.ui')

        self.mainwindow = builder.get_object('mainframe', master)

        #connect callbacks
        builder.connect_callbacks(self)

    def on_next(self):
        messagebox.showinfo('Clicked', 'The Next Button')

    def on_quit(self):
        self.master.quit()

if __name__ == '__main__':
    root = tk.Tk()
    app = Application(root)

    root.mainloop()

