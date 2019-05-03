# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.util import container_of, get_typed_pointer, decode_flags
from crash.util.symbols import Types, Symvals
from crash.infra.lookup import DelayedSymval, DelayedType
from crash.types.list import list_for_each_entry
from crash.subsystem.storage import block_device_name

types = Types('struct super_block')
symvals = Symvals('super_blocks')

MS_RDONLY       = 1
MS_NOSUID       = 2
MS_NODEV        = 4
MS_NOEXEC       = 8
MS_SYNCHRONOUS  = 16
MS_REMOUNT      = 32
MS_MANDLOCK     = 64
MS_DIRSYNC      = 128
MS_NOATIME      = 1024
MS_NODIRATIME   = 2048
MS_BIND         = 4096
MS_MOVE         = 8192
MS_REC          = 16384
MS_VERBOSE      = 32768
MS_SILENT       = 32768
MS_POSIXACL     = (1<<16)
MS_UNBINDABLE   = (1<<17)
MS_PRIVATE      = (1<<18)
MS_SLAVE        = (1<<19)
MS_SHARED       = (1<<20)
MS_RELATIME     = (1<<21)
MS_KERNMOUNT    = (1<<22)
MS_I_VERSION    = (1<<23)
MS_STRICTATIME  = (1<<24)
MS_LAZYTIME     = (1<<25)
MS_NOSEC        = (1<<28)
MS_BORN         = (1<<29)
MS_ACTIVE       = (1<<30)
MS_NOUSER       = (1<<31)

SB_FLAGS = {
    MS_RDONLY       : "MS_RDONLY",
    MS_NOSUID       : "MS_NOSUID",
    MS_NODEV        : "MS_NODEV",
    MS_NOEXEC       : "MS_NOEXEC",
    MS_SYNCHRONOUS  : "MS_SYNCHRONOUS",
    MS_REMOUNT      : "MS_REMOUNT",
    MS_MANDLOCK     : "MS_MANDLOCK",
    MS_DIRSYNC      : "MS_DIRSYNC",
    MS_NOATIME      : "MS_NOATIME",
    MS_NODIRATIME   : "MS_NODIRATIME",
    MS_BIND         : "MS_BIND",
    MS_MOVE         : "MS_MOVE",
    MS_REC          : "MS_REC",
    MS_SILENT       : "MS_SILENT",
    MS_POSIXACL     : "MS_POSIXACL",
    MS_UNBINDABLE   : "MS_UNBINDABLE",
    MS_PRIVATE      : "MS_PRIVATE",
    MS_SLAVE        : "MS_SLAVE",
    MS_SHARED       : "MS_SHARED",
    MS_RELATIME     : "MS_RELATIME",
    MS_KERNMOUNT    : "MS_KERNMOUNT",
    MS_I_VERSION    : "MS_I_VERSION",
    MS_STRICTATIME  : "MS_STRICTATIME",
    MS_LAZYTIME     : "MS_LAZYTIME",
    MS_NOSEC        : "MS_NOSEC",
    MS_BORN         : "MS_BORN",
    MS_ACTIVE       : "MS_ACTIVE",
    MS_NOUSER       : "MS_NOUSER",
}

def super_fstype(sb):
    """
    Returns the file system type's name for a given superblock.

    Args:
        sb (gdb.Value<struct super_block>): The struct super_block for
            which to return the file system type's name

    Returns:
        str: The file system type's name
    """
    return sb['s_type']['name'].string()

def super_flags(sb):
    """
    Returns the flags associated with the given superblock.

    Args:
        sb (gdb.Value<struct super_block>): The struct super_block for
            which to return the flags.

    Returns:
        str: The flags field in human-readable form.

    """
    return decode_flags(sb['s_flags'], SB_FLAGS)

def for_each_super_block():
    """
    Iterate over the list of super blocks and yield each one.

    Args:
        None

    Yields:
        gdb.Value<struct super_block>
    """
    for sb in list_for_each_entry(symvals.super_blocks,
                                  types.super_block_type, 's_list'):
        yield sb

def get_super_block(desc):
    """
    Given an address description return a gdb.Value that contains
    a struct super_block at that address.

    Args:
        desc (gdb.Value, str, or int): The address for which to provide
            a casted pointer

    Returns:
        gdb.Value<struct super_block>: The super_block at the requested
            location
    """
    sb = get_typed_pointer(desc, types.super_block_type)
    try:
        x = sb['s_id'].string()
    except gdb.error:
        raise ValueError(f"`{desc}' does not describe a valid superblock")
    return sb
