# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import overload, List, Tuple, Callable

from crash.infra.lookup import DelayedType, DelayedSymbol, DelayedSymval
from crash.infra.lookup import DelayedValue, DelayedMinimalSymbol
from crash.infra.lookup import DelayedMinimalSymval
from crash.infra.lookup import ObjfileEventCallback, TypeCallback
from crash.infra.lookup import SymbolCallback, MinimalSymbolCallback
from crash.exceptions import DelayedAttributeError

class DelayedCollection(object):
    @overload
    def __init__(self, cls: DelayedValue, names: List[str]): ...
    @overload
    def __init__(self, cls: DelayedValue, names: str): ...

    def __init__(self, cls, names):
        self.attrs = {}
        self.sym = {}

        if isinstance(names, str):
            names = [ names ]

        for name in names:
            t = cls(name)
            if hasattr(t, 'attrname'):
                self.attrs[t.attrname] = t
            else:
                self.attrs[t.name] = t

    def get(self, name):
        if name not in self.attrs:
            raise NameError(f"'{self.__class__}' object has no '{name}'")

        if self.attrs[name].value is not None:
            setattr(self, name, self.attrs[name].value)
            return self.attrs[name].value

        raise DelayedAttributeError(name)

    def __getitem__(self, name):
        try:
            return self.get(name)
        except NameError as e:
            raise KeyError(str(e))

    def __getattr__(self, name):
        try:
            return self.get(name)
        except NameError as e:
            raise AttributeError(str(e))

class Types(DelayedCollection):
    def __init__(self, names):
        super(Types, self).__init__(DelayedType, names)

class Symbols(DelayedCollection):
    def __init__(self, names):
        super(Symbols, self).__init__(DelayedSymbol, names)

class Symvals(DelayedCollection):
    def __init__(self, names):
        super(Symvals, self).__init__(DelayedSymval, names)

class MinimalSymbols(DelayedCollection):
    def __init__(self, names):
        super(MinimalSymbols, self).__init__(DelayedMinimalSymbol, names)

class MinimalSymvals(DelayedCollection):
    def __init__(self, names):
        super(MinimalSymvals, self).__init__(DelayedMinimalSymval, names)

class DelayedValues(DelayedCollection):
    def __init__(self, names):
        super(DelayedValues, self).__init__(DelayedDelayedValue, names)

class CallbackCollection(object):
    @overload
    def __init__(self, cls: ObjfileEventCallback, cbs: Tuple[str, Callable]):
        ...
    @overload
    def __init__(self, cls: ObjfileEventCallback,
                 cbs: List[Tuple[str, Callable]]):
        ...

    def __init__(self, cls, cbs):
        if isinstance(cbs, tuple):
            cbs = [ cbs ]

        for cb in cbs:
            t = cls(cb[0], cb[1])
            if hasattr(t, 'attrname'):
                setattr(self, t.attrname, t)
            else:
                setattr(self, t.name, t)

class TypeCallbacks(CallbackCollection):
    def __init__(self, cbs):
        super().__init__(TypeCallback, cbs)

class SymbolCallbacks(CallbackCollection):
    def __init__(self, cbs):
        super().__init__(SymbolCallback, cbs)

class MinimalSymbolCallbacks(CallbackCollection):
    def __init__(self, cbs):
        super().__init__(MinimalSymbolCallback, cbs)

