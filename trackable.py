from __future__ import annotations
import tkinter
import time

from typing import Dict, List, Callable
import threading
import re
import logging


class EVENT_TYPES:
    SET_ATTRIBUTE = "set_attribute"
    METHOD_CALL = "method_call"
    WITHIN_THRESHOLD = "within_threshold"
    TRACKABLE_ADDED = "trackable_added"
    TRACKABLE_REMOVED = "trackable_removed"


logger = logging.getLogger(__name__)


# todo remove observer class, just use mediator, with collection of callbacks
# todo add supported primitive types to trackable
# todo use queue instead of lock for mediators - most time is probably spent waiting for lock
# todo add support for tracking methods
# todo add ability to track primitive types:
#   - maybe create a trackable and add each primitive to its dict and use inspect to replace references to primitive
#   with a reference to that trackable's attribute
#   - monkey patch, instead of using inspect
# todo add ability to track collections - recursively check if each item is trackable
# todo add tabs to tkinter gui

# todo check if its even necessary to use dynamic class inheritance, instead of using composition and monkey patching
#   - for inheriting special methods

# todo add method to automatically detect any trackables defined in file and add them to the mediator

# todo research metaclasses and how to track number of method calls from decorators


class Trackable:
    dynamic_class_cache = {}

    UPDATES_PER_SECOND = 20
    UPDATE_INTERVAL = 1 / UPDATES_PER_SECOND

    def __init__(self, obj=None, name: str = None):
        if obj is not None:
            original_class = obj.__class__
            merged_class = None
            if original_class not in self.dynamic_class_cache:
                merged_class = self.dynamic_class_cache[original_class] = type(
                    f"DynamicClass_{original_class.__name__}",
                    (original_class, Trackable), {})

            # Inherit special methods, attributes and methods from original class of obj
            self.__class__ = merged_class or self.dynamic_class_cache[original_class]
            self.__dict__.update(obj.__dict__)
            print(f"Trackable.__init__ {self.__class__} {self.__dict__})")

        self._trackable_attributes = {}
        self._trackable_methods = {}

        self._mediators = []
        self._lock = threading.Lock()

        self.name = name or self.__class__.__name__
        self.last_update: Dict[str, float] = {}

    def __setattr__(self, key, value, silent=False):
        # if key.startswith("_"):
        #     super.__setattr__(self, key, value)
        #     return
        #
        # self._trackable_attributes[key] = value

        super.__setattr__(self, key, value)
        if silent or key.startswith("_") or key == "name" or key == "particles":
            return

        if time.time() - self.last_update.get(key, 0) < self.UPDATE_INTERVAL:
            return

        if not isinstance(value, (int, float, str)):
            return

        logger.debug(f"{self} setting {key} = {value}")
        self.notify_mediators(key, value, EVENT_TYPES.SET_ATTRIBUTE)
        self.last_update[key] = time.time()

    # def __getattr__(self, item):
    # if item.startswith("_"):
    #     return super.__getattr__(self, item)
    #
    # return self._trackable_attributes.get(item)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"

    def get_lock(self):
        return self._lock

    def add_mediator(self, mediator):
        self._mediators.append(mediator)

        mediator.notify(self.name, self.name, [self.get_trackable_attributes(), self.get_trackable_methods()],
                        EVENT_TYPES.TRACKABLE_ADDED)

    def remove_mediator(self, mediator):
        self._mediators.remove(mediator)

    def notify_mediators(self, key, value, type):
        for mediator in self._mediators:
            logger.debug(f"notifying {mediator} of {self.name}.{key} = {value}")
            mediator.notify(self.name, key, value, type)

    def get_trackable_attributes(self):
        return self._trackable_attributes

    def get_trackable_methods(self):
        return self._trackable_methods

    def invoke(self, method_name, *args, **kwargs):
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(*args, **kwargs)
        else:
            raise AttributeError(f"{self} has no attribute {method_name}")

    @staticmethod
    def notify_method_call(func):

        def wrapper(self, *args, silent=False, **kwargs):
            name = func.__name__
            if name not in self._trackable_methods:
                self._trackable_methods[name] = 0
            self._trackable_methods[name] += 1

            # print(f"notifying mediators of function call: {name}(args={args}, kwargs={kwargs})")
            logger.debug(f"notifying mediators of function call: {name}(args={args}, kwargs={kwargs})")

            if not silent:
                self.notify_mediators(name, args + tuple(kwargs), EVENT_TYPES.METHOD_CALL)

            return func(self, *args, **kwargs)

        return wrapper

    @notify_method_call
    def test(self, depth):
        # print(f"test called with depth {depth}")
        logger.debug(f"test called with depth {depth}")
        if depth > 0:
            self.test(depth - 1)


class Mediator:
    def __init__(self, trackables: List[Trackable] = None, observers: List[Observer] = None):
        self._trackables: Dict[str, Trackable] = {}
        self._observers: List[Observer] = []
        self._lock = threading.RLock()

    def __repr__(self):
        return f"{self.__class__.__name__}({len(self._trackables)} trackables, {len(self._observers)} observers)"

    def add_trackable(self, trackable: Trackable):
        with self._lock and trackable.get_lock():
            new_name = trackable.name
            while new_name in self._trackables:
                if re.search(r"(\d+)$", new_name):
                    new_name = re.sub(r"(\d+)$", lambda m: str(int(m.group(1)) + 1), new_name)
                else:
                    new_name += "2"

            trackable.name = new_name

            self._trackables[new_name] = trackable
            trackable.add_mediator(self)

    def remove_trackable(self, trackable: Trackable):
        with self._lock:
            self._trackables.pop(trackable._name)
            trackable.remove_mediator(self)

    def add_observer(self, observer):
        with self._lock:
            self._observers.append(observer)

    def remove_observer(self, observer):
        with self._lock:
            self._observers.remove(observer)

    def notify(self, trackable_name, key, value, type):
        """Notify observers of a change to a trackable."""
        with self._lock:
            for observer in self._observers:
                observer.notify(trackable_name, key, value, type)

    def set_attribute(self, trackable_name, key, value):
        """Set an attribute on a trackable and notify observers."""
        trackable = self._trackables[trackable_name]
        with self._lock:
            trackable.__setattr__(key, value)

    def invoke_method(self, trackable_name, method_name, args=None, kwargs=None):
        """Invoke a method on a trackable and notify observers."""
        args = args or []
        kwargs = kwargs or {}
        trackable = self._trackables[trackable_name]
        with trackable.get_lock():
            # print(f"invoking {trackable_name}.{method_name}({args}, {kwargs})")
            logger.debug(f"invoking {trackable_name}.{method_name}({args}, {kwargs})")
            trackable.invoke(method_name, *args, **kwargs)

    def get_all_attributes(self):
        """Get all attributes of all trackables."""
        with self._lock:
            return {trackable_name: trackable.get_trackable_attributes() for trackable_name, trackable in
                    self._trackables.items()}

    def get_all_methods(self):
        """Get all methods of all trackables."""
        with self._lock:
            return {trackable_name: trackable.get_trackable_methods() for trackable_name, trackable in
                    self._trackables.items()}


class Observer:
    def __init__(self, mediator: Mediator, notify_callback: Callable = None):
        self.mediator = mediator
        self.mediator.add_observer(self)
        self.notify_callback = notify_callback

    def set_notify_callback(self, callback):
        self.notify_callback = callback

    def notify(self, trackable_name, key, value, type):
        # print(f"observer: {trackable_name}.{key} = {value} ({type})")
        logger.debug(f"observer: {trackable_name}.{key} = {value} ({type})")
        if self.notify_callback:
            self.notify_callback(trackable_name, key, value, type)

    def set_attribute(self, trackable_name, key, value):
        self.mediator.set_attribute(trackable_name, key, value)

    def invoke_method(self, trackable_name, method_name, args=None, kwargs=None):
        self.mediator.invoke_method(trackable_name, method_name, args, kwargs)

    def get_trackable_attributes(self, trackable_name=None):
        if trackable_name is None:
            return self.mediator.get_all_attributes()
        return self.mediator.get_all_attributes()[trackable_name]


def main():
    window = tkinter.Tk()

    track = Trackable(None, "test")
    track2 = Trackable(None, "test")
    track3 = Trackable(None, "test")

    mediator = Mediator()

    observer = Observer(mediator)
    observer2 = Observer(mediator)

    mediator.add_trackable(track)
    mediator.add_trackable(track2)
    mediator.add_trackable(track3)

    track.x = 0
    track.x += 1
    track2.x = 1

    mediator.set_attribute("test", "x", 2)
    mediator.invoke_method("test", "__setattr__", args=("x", 3))

    window.mainloop()


if __name__ == "__main__":
    main()
