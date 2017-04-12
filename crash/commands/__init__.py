#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

import gdb

import os
import glob
import importlib
import argparse

class CommandRuntimeError(RuntimeError):
    pass

class CrashCommand(gdb.Command):
    commands = {}
    def __init__(self, name, parser=None):
        name = "py" + name
        gdb.Command.__init__(self, name, gdb.COMMAND_USER)
        if parser is None:
            parser = argparse.ArgumentParser(prog=name)

        nl = ""
        if self.__doc__[-1] != '\n':
            nl = "\n"
        parser.format_help = lambda: self.__doc__ + nl
        self.parser = parser
        self.commands[name] = self

    def invoke(self, argstr, from_tty):
        argv = gdb.string_to_argv(argstr)
        try:
            args = self.parser.parse_args(argv)
            self.execute(args)
        except SystemExit:
            return
        except KeyboardInterrupt:
            return
        except CommandRuntimeError as e:
            print(str(e))

    def execute(self, argv):
        raise NotImplementedError("CrashCommand should not be called directly")

def discover():
    modules = glob.glob(os.path.dirname(__file__)+"/[A-Za-z]*.py")
    __all__ = [ os.path.basename(f)[:-3] for f in modules]

    mods = __all__
    for mod in mods:
        x = importlib.import_module("crash.commands.%s" % mod)