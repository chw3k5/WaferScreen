from tkinter import *
from tkinter import ttk


def mouse_over_label():
    root = Tk()
    l = ttk.Label(root, text="Starting...")
    l.grid()
    l.bind('<Enter>', lambda e: l.configure(text='Moved mouse inside'))
    l.bind('<Leave>', lambda e: l.configure(text='Moved mouse outside'))
    l.bind('<1>', lambda e: l.configure(text='Clicked left mouse button'))
    l.bind('<Double-1>', lambda e: l.configure(text='Double clicked'))
    l.bind('<B3-Motion>', lambda e: l.configure(text=F"right button drag to {'%d' % e.x}, {'%d' % e.y}"))
    root.mainloop()


class FeetToMeters:
    resolution = 10000.0

    def __init__(self, root, length=300, width=500):
        # create a frame to hold the contents of the application
        root.title("Feet to Meters")

        mainframe = ttk.Frame(root, padding="3 3 12 12")  # (left, top, right, bottom)
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        self.feet = StringVar()
        self.meters = StringVar()

        feet_entry = ttk.Entry(mainframe, width=7, textvariable=self.feet)
        feet_entry.grid(column=2, row=1, sticky=(W, E))

        ttk.Label(mainframe, textvariable=self.meters).grid(column=2, row=2, sticky=(W, E))
        ttk.Button(mainframe, text="Calculate", command=self.calculate).grid(column=3, row=3, sticky=W)

        ttk.Label(mainframe, text="feet").grid(column=3, row=1, sticky=W)
        ttk.Label(mainframe, text="is equivalent to").grid(column=1, row=2, sticky=E)
        ttk.Label(mainframe, text="meters").grid(column=3, row=2, sticky=W)

        for child in mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

        feet_entry.focus()
        root.bind("<Return>", self.calculate)

    def calculate(self):
        try:
            value = float(self.feet.get())
            self.meters.set(int(0.3048 * value * self.resolution + 0.5) / self.resolution)
        except ValueError:
            pass


if __name__ == "__main__":
    a_root = Tk()
    vac_interface = FeetToMeters(root=a_root)
    a_root.mainloop()