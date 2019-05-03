# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.util import array_size, struct_has_member
from crash.util.symbols import Types, Symvals, MinimalSymvals, MinimalSymbols
from crash.util.symbols import MinimalSymbolCallbacks, SymbolCallbacks
from crash.types.list import list_for_each_entry
from crash.types.module import for_each_module
from crash.exceptions import DelayedAttributeError
from crash.types.bitmap import find_first_set_bit, find_last_set_bit
from crash.types.bitmap import find_next_set_bit, find_next_zero_bit
from crash.types.page import Page
from crash.types.cpu import highest_possible_cpu_nr

class PerCPUError(TypeError):
    fmt = "{} does not correspond to a percpu pointer."
    def __init__(self, var):
        super().__init__(self.fmt.format(var))

types = Types([ 'void *', 'char *', 'struct pcpu_chunk',
                'struct percpu_counter' ])
symvals = Symvals([ '__per_cpu_offset', 'pcpu_base_addr', 'pcpu_slot',
                    'pcpu_nr_slots', 'pcpu_group_offsets' ])
msymvals = MinimalSymvals( ['__per_cpu_start', '__per_cpu_end' ])

class PerCPUState(object):
    dynamic_offset_cache = None
    static_ranges = dict()
    module_ranges = dict()
    last_cpu = None

    @classmethod
    def setup_per_cpu_size(cls, symbol):
        try:
            size = msymvals['__per_cpu_end'] - msymvals['__per_cpu_start']
        except DelayedAttributeError:
            pass

        cls.static_ranges = { 0 : size }
        if msymvals['__per_cpu_start'] != 0:
            cls.static_ranges[msymvals['__per_cpu_start']] = size

        cls.module_ranges = {}

        try:
            # This is only an optimization so we don't return NR_CPUS values
            # when there are far fewer CPUs on the system.
            cls.last_cpu = highest_possible_cpu_nr()
        except DelayedAttributeError:
            pass

    @classmethod
    def setup_nr_cpus(cls, ignored):
        cls.nr_cpus = array_size(symvals['__per_cpu_offset'])

        if cls.last_cpu is None:
            cls.last_cpu = cls.nr_cpus

    @classmethod
    def setup_module_ranges(cls, modules):
        for module in for_each_module():
            start = int(module['percpu'])
            if start == 0:
                continue

            size = int(module['percpu_size'])
            cls.module_ranges[start] = size

    def __add_to_offset_cache(self, base, start, end):
        self.dynamic_offset_cache.append((base + start, base + end))

    def dump_ranges(cls):
        for (start, size) in cls.static_ranges.items():
            print(f"static start={start:#x}, size={size:#x}")
        for (start, size) in self.module_ranges.items():
            print(f"module start={start:#x}, size={size:#x}")
        if cls.dynamic_offset_cache is not None:
            for (start, end) in cls.dynamic_offset_cache:
                print(f"dynamic start={start:#x}, end={end:#x}")

    def __setup_dynamic_offset_cache_area_map(self, chunk):
        used_is_negative = None
        chunk_base = int(chunk["base_addr"]) - int(symvals.pcpu_base_addr)

        off = 0
        start = None
        _map = chunk['map']
        map_used = int(chunk['map_used'])

        # Prior to 3.14 commit 723ad1d90b56 ("percpu: store offsets
        # instead of lengths in ->map[]"), negative values in map
        # meant the area is used, and the absolute value is area size.
        # After the commit, the value is area offset for unused, and
        # offset | 1 for used (all offsets have to be even). The value
        # at index 'map_used' is a 'sentry' which is the total size |
        # 1. There is no easy indication of whether kernel includes
        # the commit, unless we want to rely on version numbers and
        # risk breakage in case of backport to older version. Instead
        # employ a heuristic which scans the first chunk, and if no
        # negative value is found, assume the kernel includes the
        # commit.
        if used_is_negative is None:
            used_is_negative = False
            for i in range(map_used):
                val = int(_map[i])
                if val < 0:
                    used_is_negative = True
                    break

        if used_is_negative:
            for i in range(map_used):
                val = int(_map[i])
                if val < 0:
                    if start is None:
                        start = off
                else:
                    if start is not None:
                        self.__add_to_offset_cache(chunk_base, start, off)
                        start = None
                off += abs(val)
            if start is not None:
                self.__add_to_offset_cache(chunk_base, start, off)
        else:
            for i in range(map_used):
                off = int(_map[i])
                if off & 1 == 1:
                    off -= 1
                    if start is None:
                        start = off
                else:
                    if start is not None:
                        self.__add_to_offset_cache(chunk_base, start, off)
                        start = None
            if start is not None:
                off = int(_map[map_used]) - 1
                self.__add_to_offset_cache(chunk_base, start, off)


    def __setup_dynamic_offset_cache_bitmap(self, chunk):
        group_offset = int(symvals.pcpu_group_offsets[0])
        size_in_bytes = int(chunk['nr_pages']) * Page.PAGE_SIZE
        size_in_bits = size_in_bytes << 3
        start = -1
        end = 0

        chunk_base = int(chunk["base_addr"]) - int(symvals.pcpu_base_addr)
        self.__add_to_offset_cache(chunk_base, 0, size_in_bytes)

    def __setup_dynamic_offset_cache(self):
        self.dynamic_offset_cache = list()

        # TODO: interval tree would be more efficient, but this adds no 3rd
        # party module dependency...
        use_area_map = struct_has_member(types.pcpu_chunk_type, 'map')
        for slot in range(symvals.pcpu_nr_slots):
            for chunk in list_for_each_entry(symvals.pcpu_slot[slot], types.pcpu_chunk_type, 'list'):
                if use_area_map:
                    self.__setup_dynamic_offset_cache_area_map(chunk)
                else:
                    self.__setup_dynamic_offset_cache_bitmap(chunk)

    def __is_percpu_var_dynamic(self, var):
        try:
            if self.dynamic_offset_cache is None:
                self.__setup_dynamic_offset_cache()

            var = int(var)
            # TODO: we could sort the list...
            for (start, end) in self.dynamic_offset_cache:
                if var >= start and var < end:
                    return True

            return False
        except DelayedAttributeError:
            # This can happen with the testcases or in kernels prior to 2.6.30
            pass

    # The resolved percpu address
    def _is_static_percpu_address(self, addr):
        for start in self.static_ranges:
            size = self.static_ranges[start]
            for cpu in range(0, self.last_cpu):
                offset = int(symvals['__per_cpu_offset'][cpu]) + start
                if addr >= offset and addr < offset + size:
                    return True
        return False

    # The percpu virtual address
    def is_static_percpu_var(self, addr):
        for start in self.static_ranges:
            for cpu in range(0, self.last_cpu):
                size = self.static_ranges[start]
                if addr >= start and addr < start + size:
                    return True
        return False

    # The percpu range should start at offset 0 but gdb relocation
    # treats 0 as a special value indicating it should just be after
    # the previous section.  It's possible to override this while
    # loading debuginfo but not when debuginfo is embedded.
    def relocated_offset(self, var):
        addr=int(var)
        start = msymvals['__per_cpu_start']
        size = self.static_ranges[start]
        if addr >= start and addr < start + size:
            return addr - start
        return addr

    # The percpu virtual address
    def is_module_percpu_var(self, addr):
        for start in self.module_ranges:
            for cpu in range(0, self.last_cpu):
                size = self.module_ranges[start]
                if addr >= start and addr < start + size:
                    return True
        return False

    def is_percpu_var(self, var):
        if isinstance(var, gdb.Symbol):
            var = var.value().address
        if self.is_static_percpu_var(var):
            return True
        if self.is_module_percpu_var(var):
            return True
        if self.__is_percpu_var_dynamic(var):
            return True
        return False

    def get_percpu_var_nocheck(self, var, cpu=None, nr_cpus=None):
        if nr_cpus is None:
            nr_cpus = self.last_cpu
        if cpu is None:
            vals = {}
            for cpu in range(0, nr_cpus):
                vals[cpu] = self.get_percpu_var_nocheck(var, cpu, nr_cpus)
            return vals

        addr = symvals['__per_cpu_offset'][cpu]
        if addr > 0:
            addr += self.relocated_offset(var)

        val = gdb.Value(addr).cast(var.type)
        if var.type != types.void_p_type:
            val = val.dereference()
        return val

    # Per-cpus come in a few forms:
    # - "Array" of objects
    # - "Array" of pointers to objects
    # - Pointers to either of those
    #
    # If we want to get the typing right, we need to recognize each one
    # and figure out what type to pass back.  We do want to dereference
    # pointer to a percpu but we don't want to dereference a percpu
    # pointer.
    def get_percpu_var(self, var, cpu=None, nr_cpus=None):
        orig_var = var
        # Percpus can be:
        # - actual objects, where we'll need to use the address.
        # - pointers to objects, where we'll need to use the target
        # - a pointer to a percpu object, where we'll need to use the
        #   address of the target
        if isinstance(var, gdb.Symbol) or isinstance(var, gdb.MinSymbol):
            var = var.value()
        if not isinstance(var, gdb.Value):
            raise TypeError("Argument must be gdb.Symbol or gdb.Value")

        if var.type.code == gdb.TYPE_CODE_PTR:
            # The percpu contains pointers
            if var.address is not None and self.is_percpu_var(var.address):
                var = var.address
            # Pointer to a percpu
            elif self.is_percpu_var(var):
                if var.type != types.void_p_type:
                        var = var.dereference().address
                assert(self.is_percpu_var(var))
            else:
                raise PerCPUError(orig_var)
        # object is a percpu
        elif self.is_percpu_var(var.address):
                var = var.address
        else:
            raise PerCPUError(orig_var)

        return self.get_percpu_var_nocheck(var, cpu, nr_cpus)

msym_cbs = MinimalSymbolCallbacks([ ('__per_cpu_start',
                                     PerCPUState.setup_per_cpu_size),
                                    ('__per_cpu_end',
                                     PerCPUState.setup_per_cpu_size) ])
symbol_cbs = SymbolCallbacks([ ('__per_cpu_offset', PerCPUState.setup_nr_cpus),
                               ('modules', PerCPUState.setup_module_ranges) ])

_state = PerCPUState()

def is_percpu_var(var):
    return _state.is_percpu_var()

def get_percpu_var(var, cpu=None, nr_cpus=None):
    return _state.get_percpu_var(var, cpu, nr_cpus)

def percpu_counter_sum(var):
    if isinstance(var, gdb.Symbol):
        var = var.value()

    if not (var.type == types.percpu_counter_type or
            (var.type.code == gdb.TYPE_CODE_PTR and
             var.type.target() == types.percpu_counter_type)):
        raise TypeError("var must be gdb.Symbol or gdb.Value describing `{}' not `{}'"
                            .format(types.percpu_counter_type, var.type))

    total = int(var['count'])

    v = get_percpu_var(var['counters'])
    for cpu in v:
        total += int(v[cpu])

    return total
