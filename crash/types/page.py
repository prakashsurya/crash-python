#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from math import log, ceil
import gdb
import types
from crash.infra import CrashBaseClass, export
from crash.util import container_of, find_member_variant
from crash.cache.syscache import config

#TODO debuginfo won't tell us, depends on version?
PAGE_MAPPING_ANON = 1

class Page(CrashBaseClass):
    __types__ = [ 'unsigned long', 'struct page', 'enum pageflags',
                    'enum zone_type', 'struct mem_section']
    __type_callbacks__ = [ ('struct page', 'setup_page_type' ),
                           ('enum pageflags', 'setup_pageflags' ),
                           ('enum zone_type', 'setup_zone_type' ),
                           ('struct mem_section', 'setup_mem_section') ]
    __symvals__ = [ 'mem_section' ]
    # TODO: this should better be generalized to some callback for
    # "config is available" without refering to the symbol name here
    __symbol_callbacks__ = [ ('kernel_config_data', 'setup_nodes_width' ),
                             ('vmemmap_base', 'setup_vmemmap_base' ),
                             ('page_offset_base', 'setup_directmap_base' ) ]

    slab_cache_name = None
    slab_page_name = None
    compound_head_name = None
    vmemmap_base = 0xffffea0000000000
    vmemmap = None
    directmap_base = 0xffff880000000000
    pageflags = dict()

    PG_tail = None
    PG_slab = None
    PG_lru = None

    setup_page_type_done = False
    setup_pageflags_done = False
    setup_pageflags_finish_done = False

    ZONES_WIDTH = None
    NODES_WIDTH = None
    # TODO have arch provide this?
    BITS_PER_LONG = None

    sparsemem = False

    @classmethod
    def setup_page_type(cls, gdbtype):
        # TODO: should check config, but that failed to work on ppc64, hardcode
        # 64k for now
        if gdb.current_target().arch.ident == "powerpc:common64":
            cls.PAGE_SHIFT = 16
            # also a config
            cls.directmap_base = 0xc000000000000000

            cls.sparsemem = True
            cls.SECTION_SIZE_BITS = 24
        else:
            cls.PAGE_SHIFT = 12
            cls.PAGE_SIZE = 4096

        cls.PAGE_SIZE = 1 << cls.PAGE_SHIFT

        cls.slab_cache_name = find_member_variant(gdbtype, ('slab_cache', 'lru'))
        cls.slab_page_name = find_member_variant(gdbtype, ('slab_page', 'lru'))
        cls.compound_head_name = find_member_variant(gdbtype, ('compound_head', 'first_page' ))
        cls.vmemmap = gdb.Value(cls.vmemmap_base).cast(gdbtype.pointer())

        cls.setup_page_type_done = True
        if cls.setup_pageflags_done and not cls.setup_pageflags_finish_done:
            cls.setup_pageflags_finish()

    @classmethod
    def setup_mem_section(cls, gdbtype):
        # TODO assumes SPARSEMEM_EXTREME
        cls.SECTIONS_PER_ROOT = cls.PAGE_SIZE / gdbtype.sizeof

    @classmethod
    def pfn_to_page(cls, pfn):
        if cls.sparsemem:
            section_nr = pfn >> (cls.SECTION_SIZE_BITS - cls.PAGE_SHIFT)
            root_idx = section_nr / cls.SECTIONS_PER_ROOT
            offset = section_nr & (cls.SECTIONS_PER_ROOT - 1)
            section = cls.mem_section[root_idx][offset]

            pagemap = section["section_mem_map"] & ~3L
            return (pagemap.cast(cls.page_type.pointer()) + pfn).dereference()
        else:
            return cls.vmemmap[pfn]

    @classmethod
    def setup_pageflags(cls, gdbtype):
        for field in gdbtype.fields():
            cls.pageflags[field.name] = field.enumval

        cls.setup_pageflags_done = True
        if cls.setup_page_type_done and not cls.setup_pageflags_finish_done:
            cls.setup_pageflags_finish()

        cls.PG_slab = 1L << cls.pageflags['PG_slab']
        cls.PG_lru = 1L << cls.pageflags['PG_lru']

    @classmethod
    def setup_vmemmap_base(cls, symbol):
        cls.vmemmap_base = long(symbol.value())
        # setup_page_type() was first and used the hardcoded initial value,
        # we have to update
        if cls.vmemmap is not None:
            cls.vmemmap = gdb.Value(cls.vmemmap_base).cast(cls.page_type.pointer())

    @classmethod
    def setup_directmap_base(cls, symbol):
        cls.directmap_base = long(symbol.value())

    @classmethod
    def setup_zone_type(cls, gdbtype):
        max_nr_zones = gdbtype['__MAX_NR_ZONES'].enumval
        cls.ZONES_WIDTH = int(ceil(log(max_nr_zones)))

    @classmethod
    def setup_nodes_width(cls, symbol):
        # TODO: handle kernels with no space for nodes in page flags
        try:
            cls.NODES_WIDTH = int(config['NODES_SHIFT'])
        except:
            # XXX
            print("Unable to determine NODES_SHIFT from config, trying 8")
            cls.NODES_WIDTH = 8
        # piggyback on this callback because type callback doesn't seem to work
        # for unsigned long
        cls.BITS_PER_LONG = cls.unsigned_long_type.sizeof * 8

    @classmethod
    def setup_pageflags_finish(cls):
        cls.setup_pageflags_finish_done = True
        if 'PG_tail' in cls.pageflags.keys():
            cls.PG_tail = 1L << cls.pageflags['PG_tail']
            cls.is_tail = cls.__is_tail_flag

        if cls.compound_head_name == 'first_page':
            cls.__compound_head = cls.__compound_head_first_page
            if cls.PG_tail is None:
                cls.PG_tail = 1L << cls.pageflags['PG_compound'] | 1L << cls.pageflags['PG_reclaim']
                cls.is_tail = cls.__is_tail_flagcombo

    @staticmethod
    def from_page_addr(addr):
        page_ptr = gdb.Value(addr).cast(Page.page_type.pointer())
        pfn = (addr - Page.vmemmap_base) / Page.page_type.sizeof
        return Page(page_ptr.dereference(), pfn)

    def __is_tail_flagcombo(self):
        return bool((self.flags & self.PG_tail) == self.PG_tail)

    def __is_tail_flag(self):
        return bool(self.flags & self.PG_tail)

    def is_tail(self):
        return bool(self.gdb_obj['compound_head'] & 1)

    def is_slab(self):
        return bool(self.flags & self.PG_slab)

    def is_lru(self):
        return bool(self.flags & self.PG_lru)

    def is_anon(self):
        mapping = long(self.gdb_obj["mapping"])
        return (mapping & PAGE_MAPPING_ANON) != 0

    def get_slab_cache(self):
        if Page.slab_cache_name == "lru":
            return self.gdb_obj["lru"]["next"]
        return self.gdb_obj[Page.slab_cache_name]

    def get_slab_page(self):
        if Page.slab_page_name == "lru":
            return self.gdb_obj["lru"]["prev"]
        return self.gdb_obj[Page.slab_page_name]

    def get_nid(self):
        return self.flags >> (self.BITS_PER_LONG - self.NODES_WIDTH)

    def get_zid(self):
        shift = self.BITS_PER_LONG - self.NODES_WIDTH - self.ZONES_WIDTH
        zid = self.flags >> shift & ((1 << self.ZONES_WIDTH) - 1)
        return zid

    def __compound_head_first_page(self):
        return long(self.gdb_obj['first_page'])

    def __compound_head(self):
        return long(self.gdb_obj['compound_head']) - 1

    def compound_head(self):
        if not self.is_tail():
            return self

        return Page.from_page_addr(self.__compound_head())
        
    def __init__(self, obj, pfn):
        self.gdb_obj = obj
        self.pfn = pfn
        self.flags = long(obj["flags"])

class Pages(CrashBaseClass):

    @export
    def pfn_to_page(cls, pfn):
        return Page(Page.pfn_to_page(pfn), pfn)

    @export
    def page_from_addr(cls, addr):
        pfn = (addr - Page.directmap_base) / Page.PAGE_SIZE
        return pfn_to_page(pfn)

    @export
    def page_from_gdb_obj(cls, gdb_obj):
        pfn = (long(gdb_obj.address) - Page.vmemmap_base) / Page.page_type.sizeof
        return Page(gdb_obj, pfn)

    @export
    def for_each_page():
        # TODO works only on x86?
        max_pfn = long(gdb.lookup_global_symbol("max_pfn").value())
        for pfn in range(max_pfn):
            try:
                yield Page.pfn_to_page(pfn)
            except gdb.error, e:
                # TODO: distinguish pfn_valid() and report failures for those?
                pass


