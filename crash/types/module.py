# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.infra import CrashBaseClass, export
from crash.types.list import list_for_each_entry

class Module(CrashBaseClass):
    __symvals__ = [ 'modules']
    __types__ = [ 'struct module' ]

    @classmethod
    @export
    def for_each_module(cls):
        for module in list_for_each_entry(cls.modules, cls.module_type,
                                          'list'):
            yield module

    @classmethod
    @export
    def for_each_module_section(cls, module):
        attrs = module['sect_attrs']

        for sec in range(0, attrs['nsections']):
            attr = attrs['attrs'][sec]
            name = attr['name'].string()
            if name == '.text':
                continue

            yield (name, int(attr['address']))
