# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.types.list import list_for_each_entry
from crash.util.symbols import Symvals, Types

symvals = Symvals([ 'modules' ])
types = Types([ 'struct module' ])

def for_each_module():
    for module in list_for_each_entry(symvals.modules, types.module_type,
                                      'list'):
        yield module

def for_each_module_section(module):
    attrs = module['sect_attrs']

    for sec in range(0, attrs['nsections']):
        attr = attrs['attrs'][sec]
        name = attr['name'].string()
        if name == '.text':
            continue

        yield (name, int(attr['address']))
