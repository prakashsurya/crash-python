# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import sys
import os
import os.path
import configparser
import gzip
import shutil

config = configparser.ConfigParser()
config.read(os.environ['CRASH_PYTHON_TESTFILE'])
vmlinux = config['test']['kernel']
vmcore = config['test']['vmcore']

roots = config['test'].get('root', None)
vmlinux_debuginfo = config['test'].get('vmlinux_debuginfo', None)
module_path = config['test'].get('module_path', None)
module_debuginfo_path = config['test'].get('module_debuginfo_path', None)

if vmlinux.endswith(".gz"):
    vmlinux_gz = vmlinux
    testdir = os.environ['CRASH_PYTHON_TESTDIR']
    base = os.path.basename(vmlinux)[:-3]
    vmlinux = os.path.join(testdir, base)

    with gzip.open(vmlinux_gz, 'r') as f_in, open(vmlinux, 'wb') as f_out:
      shutil.copyfileobj(f_in, f_out)

    f_out.close()
    f_in.close()

gdb.execute(f"file {vmlinux}")

from kdump.target import Target
target = Target(debug=False)

gdb.execute(f"target kdumpfile {vmcore}")
