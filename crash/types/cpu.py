#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.util.symbols import SymbolCallbacks
from crash.types.bitmap import for_each_set_bit
from crash.exceptions import DelayedAttributeError

# this wraps no particular type, rather it's a placeholder for
# functions to iterate over online cpu's etc.
class TypesCPUClass(object):

    cpus_online = None
    cpus_possible = None

    @classmethod
    def setup_online_mask(cls, symbol):
        cls.cpu_online_mask = symbol.value()
        bits = cls.cpu_online_mask["bits"]
        cls.cpus_online = list(for_each_set_bit(bits))

    @classmethod
    def setup_possible_mask(cls, symbol):
        cls.cpu_possible_mask = symbol.value()
        bits = cls.cpu_possible_mask["bits"]
        cls.cpus_possible = list(for_each_set_bit(bits))

def for_each_online_cpu():
    for cpu in TypesCPUClass.cpus_online:
        yield cpu

def highest_online_cpu_nr():
    if TypesCPUClass.cpus_online is None:
        raise DelayedAttributeError('cpus_online')
    return TypesCPUClass.cpus_online[-1]

def for_each_possible_cpu():
    for cpu in TypesCPUClass.cpus_possible:
        yield cpu

def highest_possible_cpu_nr():
    if TypesCPUClass.cpus_possible is None:
        raise DelayedAttributeError('cpus_possible')
    return TypesCPUClass.cpus_possible[-1]

symbol_cbs = SymbolCallbacks([ ('cpu_online_mask',
                                TypesCPUClass.setup_online_mask),
                               ('__cpu_online_mask',
                                TypesCPUClass.setup_online_mask),
                               ('cpu_possible_mask',
                                TypesCPUClass.setup_possible_mask),
                               ('__cpu_possible_mask',
                                TypesCPUClass.setup_possible_mask) ])
