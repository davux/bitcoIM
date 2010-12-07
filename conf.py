# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

"""Configuration file management."""

from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

FILE = '/etc/bitcoim/bitcoim.conf'

class Config(SafeConfigParser):
    def __init__(self, filename=None):
        if filename is None:
            filename = FILE
        SafeConfigParser.__init__(self)
        self.read(filename)
