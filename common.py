# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

"""Common functions."""

import conf
import sys

def problem(desc='A problem occurred.', fatal=False, errorcode=1):
    sys.stderr.write(desc + '\n')
    if fatal:
        sys.exit(errorcode)


#TODO: Refine the debugging
def debug(message, precise=0):
    if (precise <= conf.max_verbosity):
        sys.stderr.write("Debuglevel %s: %s\n" % (precise, message))
