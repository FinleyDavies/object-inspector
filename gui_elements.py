import tkinter as tk
from tkinter import ttk
from typing import List, Dict

from trackable import Observer


class GuiElement(ttk.Frame):
    """A frame, allowing interaction with an attribute of a trackable object, with different functionality depending
     on the type of attribute"""

    def __init__(self, trackable_name, attribute_name, observer: Observer, vartype=tk.Variable, master=None):
        super().__init__(master)
        self.observer = observer
        self.trackable_name = trackable_name
        self.attribute_name = attribute_name

        self.widget_value = vartype()
        self.widget_value.set(self.attribute_value)
        self.widget_value.trace_add("write", self.write_callback)
        self.trace_enabled = True

        self.type = type(self.attribute_value)
        self.widgets = self.create_widgets()
        for widget in self.widgets:
            widget.pack()

    @property
    def attribute_value(self):
        value = self.observer.get_trackable_attribute(self.trackable_name, self.attribute_name)
        return value

    @attribute_value.setter
    def attribute_value(self, value):
        self.observer.set_trackable_attribute(self.trackable_name, self.attribute_name, value, silent=True)

    def disable_trace(self):
        if not self.trace_enabled:
            return
        self.trace_enabled = False
        # self.widget_value.trace_vdelete("w", self.write_callback.__name__)

    def enable_trace(self):
        if self.trace_enabled:
            return
        self.trace_enabled = True
        # self.widget_value.trace_add("write", self.write_callback)

    def create_widgets(self):
        for widget in self.winfo_children():
            widget.destroy()

        widgets: List[tk.Widget] = list()
        widgets.append(tk.Label(self, text=self.attribute_name))
        return widgets

    def update_widget_value(self, new_value):
        self.disable_trace()
        self.widget_value.set(new_value)
        self.enable_trace()

    def write_callback(self, *args):
        if not self.trace_enabled:
            return
        self.update_attribute_value(self.widget_value.get())

    def update_attribute_value(self, new_value):
        self.attribute_value = new_value

    def button_callback(self):
        pass


class GuiElementBool(GuiElement):
    def create_widgets(self):
        widgets = super().create_widgets()
        widgets.append(tk.Checkbutton(self, variable=self.widget_value))
        return widgets


class GuiElementStr(GuiElement):
    def create_widgets(self):
        widgets = super().create_widgets()
        widgets.append(tk.Entry(self, textvariable=self.attribute_value))
        return widgets


class GuiElementInt(GuiElement):
    def __init__(self, trackable_name, attribute_name, observer: Observer, master=None):
        super().__init__(trackable_name, attribute_name, observer, tk.DoubleVar, master)
        self.min, self.max = 0, 10
        self.sign = 1

    def create_widgets(self):
        widgets = super().create_widgets()
        widgets.append(tk.Entry(self, textvariable=self.widget_value))
        widgets.append(tk.Scale(self, orient=tk.HORIZONTAL, variable=self.widget_value, to=10))
        widgets.append(tk.Button(self, text="+/-", command=self.toggle_sign))
        return widgets

    def set_range(self, min, max):
        self.min, self.max = min, max
        self.widgets[2].config(from_=min, to=max)

    def update_widget_value(self, new_value):
        self.disable_trace()
        self.widget_value.set(abs(round(new_value, 2)))
        self.set_range(0, max(new_value, self.max))
        self.enable_trace()

    def toggle_sign(self):
        self.sign *= -1
        self.update_attribute_value(self.widget_value.get())

    def update_attribute_value(self, new_value):
        self.attribute_value = new_value * self.sign


class GuiElementFloat(GuiElementInt):
    pass





class GuiElementList(GuiElement):
    def create_widgets(self):
        widgets = super().create_widgets()
        widgets.append(tk.Button(self, text="Open", command=self.callback))
        widgets.append(tk.OptionMenu(self, *self.attribute_value))
        widgets.append(tk.Label(self, text=f"Length: {len(self.attribute_value)}"))
        return widgets


class GuiElementDict(GuiElement):
    def create_widgets(self):
        widgets = super().create_widgets()
        widgets.append(tk.Button(self, text="Open", command=self.callback))
        widgets.append(tk.OptionMenu(self, *self.attribute_value))
        widgets.append(tk.Label(self, text=f"Length: {len(self.attribute_value)}"))
        return widgets


class GuiElementCallable(GuiElement):
    def __init__(self, trackable_name, attribute_name, observer: Observer, master=None):
        super().__init__(trackable_name, attribute_name, observer, master)
        self.args = None
        self.kwargs = None

    def create_widgets(self):
        widgets = super().create_widgets()
        widgets.append(tk.Button(self, text="Call", command=self.callback))
        widgets.append(tk.Label(self, text="Args:"))
        widgets.append(tk.Entry(self, textvariable=self.args))
        widgets.append(tk.Label(self, text="Kwargs:"))
        widgets.append(tk.Entry(self, textvariable=self.kwargs))
        return widgets


class GuiElementNone(GuiElement):
    def create_widgets(self):
        widgets = super().create_widgets()
        widgets.append(tk.Label(self, text="None"))
        return widgets

    def update_widget_value(self, new_value):
        # set self to new instance of GuiElement, using the new value
        super().update_widget_value(new_value)
        # self = GuiElementFactory.create(self.trackable_name, self.attribute_name, self.observer, self.master)


class GuiElementFactory:
    """A factory for creating GuiElements of different types"""
    custom_types = dict()

    @staticmethod
    def create(trackable_name, attribute_name, observer: Observer, master=None):
        attribute_value = observer.get_trackable_attributes(trackable_name)[attribute_name]
        attribute_type = type(attribute_value)
        if attribute_type == bool:
            return GuiElementBool(trackable_name, attribute_name, observer, tk.BooleanVar, master)
        elif attribute_type == str:
            return GuiElementStr(trackable_name, attribute_name, observer, tk.StringVar, master)
        elif attribute_type == int:
            return GuiElementInt(trackable_name, attribute_name, observer, master)
        elif attribute_type == float:
            return GuiElementFloat(trackable_name, attribute_name, observer, master)
        # elif attribute_type == list:
        #     return GuiElementList(trackable_name, attribute_name, observer, master=master)
        # elif attribute_type == dict:
        #     return GuiElementDict(trackable_name, attribute_name, observer, master=master)
        # elif attribute_type == callable:
        #     return GuiElementCallable(trackable_name, attribute_name, observer, master=master)
        elif attribute_type == type(None):
            return GuiElementNone(trackable_name, attribute_name, observer, master=master)

        for custom_type in GuiElementFactory.custom_types:
            if attribute_type == custom_type:
                return GuiElementFactory.custom_types[type](trackable_name, attribute_name, observer, master)

        raise TypeError(f"Type {attribute_type} not supported")

    @staticmethod
    def add_type(type_, gui_element):
        GuiElementFactory.custom_types[type_] = gui_element


class TrackableFrame(ttk.Frame):
    """A frame containing all the gui elements for a trackable object"""

    def __init__(self, trackable_name, observer: Observer, master=None):
        super().__init__(master)
        self.observer = observer
        self.trackable_name = trackable_name
        self.gui_elements: Dict[str, GuiElement] = dict()
        self.columns = 2

        self.create_widgets()

    @property
    def n_elements(self):
        return len(self.gui_elements)

    def create_widgets(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.gui_elements.clear()
        for attribute_name in self.observer.get_trackable_attributes(self.trackable_name):
            self.add_element(attribute_name)

    def add_element(self, attribute_name):
        print(f"Adding {attribute_name}, to {self.trackable_name}, elements: {self.gui_elements}")
        gui_element = GuiElementFactory.create(self.trackable_name, attribute_name, self.observer, self)
        gui_element.grid(row=self.n_elements // self.columns, column=self.n_elements % self.columns)

        self.gui_elements[attribute_name] = gui_element
        print(f"Added {attribute_name}, to {self.trackable_name}, elements: {self.gui_elements}")

    def remove_element(self, attribute_name):
        print(f"Removing {attribute_name}, from {self.trackable_name}, elements: {self.gui_elements}")
        gui_element = self.gui_elements[attribute_name]
        gui_element.destroy()
        del self.gui_elements[attribute_name]
        print(f"Removed {attribute_name}, from {self.trackable_name}, elements: {self.gui_elements}")

    def update_value(self, attribute_name, new_value):
        if attribute_name in self.gui_elements:
            if isinstance(self.gui_elements[attribute_name], GuiElementNone):
                self.remove_element(attribute_name)
                self.add_element(attribute_name)  # if the attribute was previously None, overwrite it
                self.create_widgets()

            self.gui_elements[attribute_name].update_widget_value(new_value)
        else:
            self.add_element(attribute_name)
