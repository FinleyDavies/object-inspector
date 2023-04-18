from __future__ import annotations

import inspect
import logging
import re
import textwrap
import threading
import time
import tkinter
import queue
from typing import Dict, List, Callable

global_trackable_declared = False


class EVENT_TYPES:
    SET_ATTRIBUTE = "set_attribute"
    METHOD_CALL = "method_call"
    WITHIN_THRESHOLD = "within_threshold"
    TRACKABLE_ADDED = "trackable_added"
    TRACKABLE_REMOVED = "trackable_removed"


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# todo remove observer class, just use mediator, with collection of callbacks
# todo use queue instead of lock for mediators - most time is probably spent waiting for lock
# todo add support for tracking methods
# todo add ability to track collections - recursively check if each item is trackable
# todo add tabs to tkinter gui
# todo add support for graphs in tkinter gui using library like matplotlib

# todo check if its even necessary to use dynamic class inheritance, instead of using composition and monkey patching
#   - for inheriting special methods


# todo research metaclasses and how to track number of method calls from decorators
# todo research dataclasses


class Trackable:
    dynamic_class_cache = {}

    UPDATES_PER_SECOND = 20
    UPDATE_INTERVAL = 1 / UPDATES_PER_SECOND

    def __init__(self, obj=None, name: str = None):
        logger.debug(f"Trackable.__init__({obj}, {name})")
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
            logger.debug(f"Trackable.__init__ {self.__class__} {self.__dict__})")

        self._trackable_attributes = {}
        self._trackable_methods = {}

        self._mediators = []
        self._lock = threading.Lock()

        self._name = name or self.__class__.__name__
        self._last_update: Dict[str, float] = {}

        self._is_timed = False  # temporary fix to allow immediate consecutive updates (will be unneccessary when using queue)

    def __setattr__(self, key, value, silent=False):
        super.__setattr__(self, key, value)
        if silent or key.startswith("_") or key == "name":
            return

        if time.time() - self._last_update.get(key, 0) < self.UPDATE_INTERVAL and self._is_timed:
            return

        if not (isinstance(value, (int, float, str, bool)) or value is None):
            return

        logger.debug(f"{self} setting {key} = {value}")
        self.notify_mediators(key, value, EVENT_TYPES.SET_ATTRIBUTE)
        self._last_update[key] = time.time()

    def __repr__(self):
        return f"{self.__class__.__name__}({self._name})"

    def get_lock(self):
        return self._lock

    def add_mediator(self, mediator):
        self._mediators.append(mediator)

        mediator.notify(self._name, self._name, [self.get_trackable_attributes(), self.get_trackable_methods()],
                        EVENT_TYPES.TRACKABLE_ADDED)

    def remove_mediator(self, mediator):
        self._mediators.remove(mediator)

    def notify_mediators(self, key, value, type):
        for mediator in self._mediators:
            logger.debug(f"notifying {mediator} of {self._name}.{key} = {value}")
            mediator.notify(self._name, key, value, type)

    def get_trackable_attributes(self):
        # returns self.__dict__ except for private attributes
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}

    def get_trackable_methods(self):
        return self._trackable_methods

    def invoke(self, method_name, *args, **kwargs):
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(*args, **kwargs)
        else:
            raise AttributeError(f"{self} has no attribute {method_name}")

    def declare_variables(self, *variables):
        for variable in variables:
            self.__setattr__(variable, None, silent=True)

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


global_tracker = Trackable(None, "global_tracker")  # global tracker for variables that are not part of a class


class Mediator:
    def __init__(self, trackables: List[Trackable] = None, observers: List[Observer] = None):
        self._trackables: Dict[str, Trackable] = {}
        self._observers: List[Observer] = []
        self._lock = threading.RLock()

        self._queue = queue.Queue()
        self._using_queue = True  # temporary, to compare performance of queue vs lock

        if global_trackable_declared:
            self.add_trackable(global_tracker)

    def __repr__(self):
        return f"{self.__class__.__name__}({len(self._trackables)} trackables, {len(self._observers)} observers)"

    def add_trackable(self, trackable: Trackable):
        with self._lock and trackable.get_lock():
            new_name = trackable._name
            while new_name in self._trackables:
                if re.search(r"(\d+)$", new_name):
                    new_name = re.sub(r"(\d+)$", lambda m: str(int(m.group(1)) + 1), new_name)
                else:
                    new_name += "2"

            trackable._name = new_name

            self._trackables[new_name] = trackable
            trackable.add_mediator(self)
        return


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
        logger.debug(f"notifying observers of {trackable_name}.{key} = {value}, await lock")
        with self._lock:
            logger.debug(f"notifying observers of {trackable_name}.{key} = {value}, got lock")
            for observer in self._observers:
                observer.notify(trackable_name, key, value, type)

    def set_attribute(self, trackable_name, key, value, silent=False):
        """Set an attribute on a trackable and notify observers."""
        trackable = self._trackables[trackable_name]
        logger.debug(f"setting {trackable_name}.{key} = {value}, await lock")
        with self._lock:
            logger.debug(f"setting {trackable_name}.{key} = {value}, got lock")

            trackable.__setattr__(key, value, silent=silent)

    def invoke_method(self, trackable_name, method_name, args=None, kwargs=None):
        """Invoke a method on a trackable and notify observers."""
        args = args or []
        kwargs = kwargs or {}
        trackable = self._trackables[trackable_name]
        with trackable.get_lock():
            # print(f"invoking {trackable_name}.{method_name}({args}, {kwargs})")
            logger.debug(f"\tinvoking {trackable_name}.{method_name}({args}, {kwargs})")
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
        logger.debug(f"\t\tobserver invoking callback: {trackable_name}.{key} = {value} ({type})")
        if self.notify_callback:
            self.notify_callback(trackable_name, key, value, type)

    def set_trackable_attribute(self, trackable_name, key, value, silent=False):
        self.mediator.set_attribute(trackable_name, key, value, silent)

    def get_trackable_attribute(self, trackable_name, key):
        return self.mediator.get_all_attributes()[trackable_name][key]

    def invoke_method(self, trackable_name, method_name, args=None, kwargs=None):
        self.mediator.invoke_method(trackable_name, method_name, args, kwargs)

    def get_trackable_attributes(self, trackable_name=None):
        if trackable_name is None:
            return self.mediator.get_all_attributes()
        return self.mediator.get_all_attributes()[trackable_name]


def track_vars_custom(trackable: Trackable, *to_track):
    """Decorator to track variables in a function.
        Adds the variables to the trackable object and macros the variable to refer to the trackable's attribute
         instead.
        WARNING: This will break code that has string literals used for logic that contain the variable names."""

    def replace_vars(source):
        """Replace all references within the source with another"""
        for var in to_track:
            source = re.sub(rf"(?<!['\"])(\b{var}\b)(?!['\"])", f"{trackable._name}.{var}", source)

            # regex to match any occurrences of the variable name that are not within quotes
            # not a trivial problem (impossible using regex?), so just replace all occurrences of the variable name
            # if they're not directly next to quotes:
            # source = re.sub(rf"(?<!['\"])({var})(?!['\"])", f"{trackable.name}.{var}", source)
            # todo use a macro library to replace the variables instead of regex, or create own macro function
            # use ast to parse the source, and get the indices of all string literals, ignoring any occurrences that are

        return source

    def decorator(func):
        global global_trackable_declared

        trackable.declare_variables(*to_track)
        global_trackable_declared = True

        source = inspect.getsourcelines(func)[0][1:]  # exclude the decorator line (avoid recursion)
        source = textwrap.dedent("".join(source))

        source = replace_vars(source)

        print(source)

        wrapper = compile(source, f"{func.__name__}.py", "exec")
        namespace = {}
        exec(wrapper, func.__globals__, namespace)

        return namespace[func.__name__]

    return decorator


def track_vars(*to_track):
    """Decorator to track variables in a function.
        Adds the variables to the global_tracker object and macros the variable to refer to the global_tracker's
         attribute instead.
        WARNING: This will break code that has string literals used for logic that contain the variable names."""
    return track_vars_custom(global_tracker, *to_track)


def start_logging():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(console_handler)


def main():
    # set up logging
    start_logging()

    window = tkinter.Tk()

    # track = Trackable(None, "test")
    # track2 = Trackable(None, "test")
    # track3 = Trackable(None, "test")
    #
    # mediator = Mediator()
    #
    # observer = Observer(mediator)
    # observer2 = Observer(mediator)
    #
    # mediator.add_trackable(track)
    # mediator.add_trackable(track2)
    # mediator.add_trackable(track3)
    #
    # track.x = 0
    # track.x += 1
    # track2.x = 1
    #
    # mediator.set_attribute("test", "x", 2)
    # mediator.invoke_method("test", "__setattr__", args=("x", 3))

    mediator = Mediator()
    observer = Observer(mediator)

    test = "hello"
    test += " world"
    test2 = 100
    test2 += 1
    test2 += 1
    test2 = len(test)

    window.mainloop()


if __name__ == "__main__":
    main()
