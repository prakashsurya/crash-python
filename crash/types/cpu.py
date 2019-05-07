#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.infra import CrashBaseClass, export
from crash.types.bitmap import for_each_set_bit
from crash.exceptions import DelayedAttributeError

# this wraps no particular type, rather it's a placeholder for
# functions to iterate over online cpu's etc.
class TypesCPUClass(CrashBaseClass):
    __symbol_callbacks__ = [ ('cpu_online_mask', 'setup_online_mask'),
                             ('__cpu_online_mask', 'setup_online_mask'),
                             ('cpu_possible_mask', 'setup_possible_mask'),
                             ('__cpu_possible_mask', 'setup_possible_mask') ]

    cpus_online = None
    cpus_possible = None

    @classmethod
    def setup_online_mask(cls, symbol):
        cls.cpu_online_mask = symvol.value()
        bits = cls.cpu_online_mask.value()["bits"]
        cls.cpus_online = list(for_each_set_bit(bits))

    @export
    def for_each_online_cpu(self):
        for cpu in self.cpus_online:
            yield cpu

    @export
    def highest_online_cpu_nr(self):
        if self.cpus_possible is None:
            raise DelayedAttributeError(self.__class__.__name__, 'cpus_online')
        return self.cpus_online[-1]

    @classmethod
    def setup_possible_mask(cls, cpu_mask):
        cls.cpu_possible_mask = symvol.value()
        bits = cls.cpu_possible_mask.value()["bits"]
        cls.cpus_possible = list(for_each_set_bit(bits))

    @export
    def for_each_possible_cpu(self):
        for cpu in self.cpus_possible:
            yield cpu

    @export
    def highest_possible_cpu_nr(self):
        if self.cpus_possible is None:
            raise DelayedAttributeError(self.__class__.__name__,
                                        'cpus_possible')
        return self.cpus_possible[-1]
