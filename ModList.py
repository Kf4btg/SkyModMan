import tkinter as tk
from tkinter import N,W,E,S
import os

class ModList(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.grid(column=0, row=0, sticky=(N,W,E,S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=4)
        self.rowconfigure(2, weight=1)
        self.createWidgets()

    def createWidgets(self):
        # making the window stretchable - boilerplate
        top=self.winfo_toplevel()
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)


        self.updateView = tk.Button(self)
        self.updateView["text"] = "Refresh"
        self.updateView["command"] = root.destroy
        self.updateView.grid(row=0)

        self.createListWidget()


        self.QUIT = tk.Button(self, text="QUIT", fg="red", command = root.destroy)
        self.QUIT.grid(row=2)

    def createListWidget(self):
        self.modlist = tk.StringVar() #os.listdir('/home/datadir/games/skyrim/mod-dls')
        # self.modlist.set(self.populateModList())
        self.modlist.set(tuple(os.listdir('/home/datadir/games/skyrim/mod-dls')))
        self.mlistbox = tk.Listbox(self, height=20, fg="black")
        self.mlistbox["listvariable"] = self.modlist
        self.mlistbox.grid(row=1, sticky=(N,W,E,S))

    def populateModList(self):
        mlist = os.listdir('/home/datadir/games/skyrim/mod-dls')
        return "'(" + "', '".join(mlist) + ")'"




root = tk.Tk()
app = ModList(master=root)
app.mainloop()
