# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from controller import Controller

class Address(object):
    '''A Bitcoin address.'''

    def __init__(self, address=None):
        '''Constructor. If address is empty, generate one.'''
        if address is None:
            address = Controller().getnewaddress()
        if not Controller().validateaddress(address)['isvalid']:
            raise InvalidBitcoinAddressError(address)
        self.address = address

    def __str__(self):
        return self.address

    def getLabel(self):
        return Controller().getlabel(self.address)

    def setLabel(self, label=None):
        if label is None:
            Controller().setlabel(self.address)
        else:
            Controller().setlabel(self.address, label)

class InvalidBitcoinAddressError(Exception):
    '''The Bitcoin address is invalid.'''
    pass
