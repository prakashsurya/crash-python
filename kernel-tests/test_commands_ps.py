# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

import crash.commands.ps

class TestCommandsPs(unittest.TestCase):
    def test_ps(self):
        output = gdb.execute("pyps", to_string=True)
        self.assertTrue(len(output.split("\n")) > 2)

    def test_ps_regex(self):
        output = gdb.execute("pyps *worker*", to_string=True)
        self.assertTrue(len(output.split("\n")) > 2)
