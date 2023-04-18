import threading
import time
import tkinter as tk

from trackable import *
from gui_elements import *


class ObserverApp(tk.Frame):
    """A tkinter frame that represents the state of a trackable object"""

    def __init__(self, observer: Observer, master=None):
        super().__init__()
        self.observer = observer
        observer.notify_callback = self.update_widgets
        self.pages: Dict[str, TrackableFrame] = dict()
        self.initialize_elements()

        self.choice = tk.StringVar()
        self.last_choice = None
        self.options = tk.OptionMenu(self, self.choice, *self.pages.keys(), command=self.change_page)
        self.options.grid(row=0, column=0)

    def __repr__(self):
        return f"ObserverApp(Trackables: {self.pages.values()})"

    def add_trackable(self, trackable_name):
        """Adds a trackable page to the app"""
        if trackable_name not in self.pages:
            self.pages[trackable_name] = TrackableFrame(trackable_name, self.observer, self)

    def initialize_elements(self):
        """If trackables are added before the app is initialized, this will add them to the app"""
        for trackable_name in self.observer.get_trackable_attributes():
            self.add_trackable(trackable_name)

    def update_widgets(self, trackable_name, key, value, event_type):
        """automatically called when a trackable attribute is changed"""
        if event_type == EVENT_TYPES.SET_ATTRIBUTE:
            self.pages[trackable_name].update_value(key, value)
        elif event_type == EVENT_TYPES.TRACKABLE_ADDED:
            # todo pass attributes into children, see if its faster than getting them within each child
            if not self.pages.get(trackable_name):
                self.add_trackable(trackable_name)

    def change_page(self, trackable_name):
        """Changes the page to the one specified by trackable_name"""
        print(f"last choice: {self.last_choice}, current choice: {trackable_name}")
        if self.last_choice:
            self.pages[self.last_choice].grid_forget()
        self.pages[trackable_name].grid(row=1, column=0)
        self.last_choice = trackable_name


@track_vars("test_var", "timer", "timer2")
def main():
    start_logging()
    root = tk.Tk()
    # notebook = ttk.Notebook(root)
    # main_tab = ttk.Frame(notebook)

    t = Trackable(None, "test")
    m = Mediator()
    m.add_trackable(t)
    # m.add_trackable(global_tracker)
    t.x = 0
    t.y = 100

    # notebook.add(main_tab, text="Main")
    o = Observer(m)
    print(o.get_trackable_attributes())
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
                    thread1_observer.set_trackable_attribute(name, key, eval(value))
            except Exception as e:
                print(e)

            print(thread1_observer.get_trackable_attributes())

    def increment_thread():
        while True:
            trackables = thread2_observer.get_trackable_attributes()
            for trackable, attributes in trackables.items():
                for key, value in attributes.items():
                    if "timer" in key and value is not None:
                        thread2_observer.set_trackable_attribute(trackable, key, value + 1)
            time.sleep(0.05)

    thread = threading.Thread(target=input_thread)
    thread.start()
    test_var = 100
    # timer = 0
    # timer2 = 100

    thread2 = threading.Thread(target=increment_thread)
    thread2.start()

    app.pack()
    # notebook.pack()
    root.mainloop()

    thread.join()
    thread2.join()


if __name__ == "__main__":
    main()
