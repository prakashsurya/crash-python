# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.util.symbols import Types
from crash.subsystem.storage import block_device_name
from crash.subsystem.storage.decoders import Decoder, decode_bio

class ClonedBioReqDecoder(Decoder):
    """
    Decodes a request-based device mapper cloned bio

    This decodes a cloned bio generated by request-based device mapper targets.

    Args:
        bio(gdb.Value<struct bio>): A struct bio generated by a
            request-based device mapper target

    """
    types = Types([ 'struct dm_rq_clone_bio_info *' ])
    __endio__ = 'end_clone_bio'
    description = '{:x} bio: Request-based Device Mapper on {}'

    _get_clone_bio_rq_info = None

    def __init__(self, bio):
        super(ClonedBioDecoder, self).__init__(self)
        self.bio = bio
        if cls._get_clone_bio_rq_info is None:
            if 'clone' in cls.types.dm_rq_clone_bio_info_p_type.target():
                getter = cls._get_clone_bio_rq_info_3_7
            else:
                getter = cls._get_clone_bio_rq_info_old
            cls._get_clone_bio_rq_info = getter

    def interpret(self):
        self.info = cls._get_clone_bio_rq_info(bio)
        self.tio = self.info['tio']

    def __str__(self):
        self.description.format(int(self.bio),
                                block_device_name(self.bio['bi_bdev']))

    def __next__(self):
        return decode_bio(self.info['orig'])

    @classmethod
    def _get_clone_bio_rq_info_old(cls, bio):
        return bio['bi_private'].cast(cls.types.dm_rq_clone_bio_info_p_type)

    @classmethod
    def _get_clone_bio_rq_info_3_7(cls, bio):
        return container_of(bio, cls.types.dm_rq_clone_bio_info_p_type, 'clone')

ClonedBioReqDecoder.register()

class ClonedBioDecoder(Decoder):
    """
    Decodes a bio-based device mapper cloned bio

    This method decodes a cloned bio generated by request-based
    device mapper targets.

    Args:
        bio(gdb.Value<struct bio>): A struct bio generated by a
            bio-based device mapper target

    Returns:
        dict: Contains the following items:
            - description (str): Human-readable description of the bio
            - bio (gdb.Value<struct bio>): The provided bio
            - tio (gdb.Value<struct dm_target_io>): The struct
                dm_target_tio for this bio
            - next (gdb.Value<struct bio>): The original bio that was
                the source of this one
            - decoder (method(gdb.Value<struct bio>)): The decoder for the
                original bio
    """
    types = Types([ 'struct dm_target_io *' ])
    _get_clone_bio_tio = None
    __endio__ = 'clone_endio'
    description = "{:x} bio: device mapper clone: {}[{}] -> {}[{}]"

    def __init__(self, bio):
        super(ClonedBioDecoder, self).__init__()
        self.bio = bio

        if _get_clone_bio_tio is None:
            if 'clone' in cls.types.dm_target_io_p_type.target():
                getter = cls._get_clone_bio_tio_3_15
            else:
                getter = cls._get_clone_bio_tio_old
            cls._get_clone_bio_tio = getter

    def interpret(self):
        self.tio = cls._get_clone_bio_tio(bio)
        self.next_bio = tio['io']['bio']

    def __str__(self):
        return self.description.format(
                                int(self.bio),
                                block_device_name(bself.io['bi_bdev']),
                                int(bself.io['bi_sector']),
                                block_device_name(self.next_bio['bi_bdev']),
                                int(self.next_bio['bi_sector']))

    def __next__(self):
        return decode_bio(self.next_bio)

    @classmethod
    def _get_clone_bio_tio_old(cls, bio):
        return bio['bi_private'].cast(cls.types.dm_target_io_p_type)

    @classmethod
    def _get_clone_bio_tio_3_15(cls, bio):
        return container_of(bio['bi_private'],
                            cls.types.dm_clone_bio_info_p_type, 'clone')

ClonedBioDecoder.register()
