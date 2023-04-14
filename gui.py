import tkinter as tk
from object_observer import Trackable, Mediator, Observer, EVENT_TYPES
from typing import Dict, Callable

import time

from tkinter import ttk

import threading


class ObserverTab(ttk.Frame):
    def __init__(self):
        pass


class ObserverApp(tk.Frame):
    """A tkinter app that observes multiple objects and dynamically creates widgets to edit and display their attributes"""

    def __init__(self, observer: Observer, master=None):
        super().__init__()
        self.observer = observer
        self.trackable_attributes = observer.get_trackable_attributes()

        self.choices = self.get_trackable_names()
        self.choice = tk.StringVar()
        self.last_choice = None
        self.dropdown = self.create_dropdown()

        self.info_frames: Dict[str, tk.Frame] = {}
        self.initialise_info_frames()

        self.observer.set_notify_callback(self.update_widgets)

    def initialise_info_frames(self):
        for trackable_name in self.trackable_attributes.keys():
            self.create_info_frame(trackable_name)
            self.hide_info_frame(trackable_name)

    def update_info_frame(self, trackable_name, key=None, value=None):
        if key is not None and value is not None:
            self.info_frames[trackable_name][key].delete(0, tk.END)
            self.info_frames[trackable_name][key].insert(0, value)
            return

        print("destroying info frame")
        for widget in self.info_frames[trackable_name]["frame"].winfo_children():
            widget.destroy()
        self.create_info_frame(trackable_name)

    def create_info_frame(self, trackable_name, attributes=None):
        attributes = attributes or self.trackable_attributes[trackable_name]
        frame = tk.Frame(self, name=trackable_name, borderwidth=1, relief=tk.RAISED)
        self.info_frames[trackable_name] = {}
        self.info_frames[trackable_name]["frame"] = frame
        for i, (key, value) in enumerate(attributes.items()):
            cols = 4
            self.info_frames[trackable_name][f"{key}_label"] = tk.Label(frame, text=key)
            self.info_frames[trackable_name][key] = tk.Entry(frame)
            self.info_frames[trackable_name][key].insert(0, str(value))
            self.info_frames[trackable_name][f"{key}_label"].grid(column=i%cols, row=i//cols * 2)
            self.info_frames[trackable_name][key].grid(column=i%cols, row=i//cols * 2 + 1)

    def display_info_frame(self, trackable_name):
        self.info_frames[trackable_name]["frame"].grid(row=1, column=0)

    def hide_info_frame(self, trackable_name):
        self.info_frames[trackable_name]["frame"].grid_forget()

    def create_dropdown(self):
        self.dropdown = tk.OptionMenu(self, self.choice, *self.choices, command=self.dropdown_callback)
        self.dropdown.grid(row=0, column=0)

        return self.dropdown

    def dropdown_callback(self, name):
        if self.last_choice:
            self.hide_info_frame(self.last_choice)
        self.display_info_frame(name)
        print(f"last choice: {self.last_choice}, current choice: {name}")
        self.last_choice = name

    def get_trackable_names(self):
        return [trackable_name for trackable_name in self.trackable_attributes.keys()]

    def get_trackable_attributes(self, trackable_name):
        return [attribute for attribute in self.trackable_attributes[trackable_name].keys()]

    def update_widgets(self, trackable_name, key, value, type):
        if type == EVENT_TYPES.TRACKABLE_ADDED:
            self.trackable_attributes[trackable_name] = value[0]
            self.choices = self.get_trackable_names()
            self.create_info_frame(trackable_name)
            self.dropdown.destroy()
            self.create_dropdown()

        elif type == EVENT_TYPES.SET_ATTRIBUTE:
            if key not in self.info_frames[trackable_name].keys():
                self.update_info_frame(trackable_name)
                self.display_info_frame(self.choice.get())

            else:
                self.update_info_frame(trackable_name, key, value)

            self.trackable_attributes[trackable_name][key] = value




def main():
    root = tk.Tk()
    # notebook = ttk.Notebook(root)
    # main_tab = ttk.Frame(notebook)

    t = Trackable("test")
    m = Mediator()
    m.add_trackable(t)
    t.x = 0
    t.y = 100

    # notebook.add(main_tab, text="Main")
    o = Observer(m)
    thread1_observer = Observer(m)
    thread2_observer = Observer(m)
    app = ObserverApp(o, master=root)

    def input_thread():
        user_input = ""
        while user_input != "quit":
            user_input = input(">>>")
            try:
                if user_input == "add":
                    m.add_trackable(Trackable("test"))
                else:
                    name, key, value = user_input.split(" ")
                    thread1_observer.set_attribute(name, key, eval(value))
            except Exception as e:
                print(e)

            print(thread1_observer.get_trackable_attributes())

    def increment_thread():
        while True:
            trackables = thread2_observer.get_trackable_attributes()
            for trackable, attributes in trackables.items():
                for key, value in attributes.items():
                    if "timer" in key:
                        thread2_observer.set_attribute(trackable, key, value + 1)
            time.sleep(0.05)

    thread = threading.Thread(target=input_thread)
    thread.start()

    thread2 = threading.Thread(target=increment_thread)
    thread2.start()

    app.pack()
    # notebook.pack()
    root.mainloop()

    thread.join()
    thread2.join()


if __name__ == "__main__":
    main()
