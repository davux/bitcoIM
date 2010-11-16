# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from bitcoin.address import Address
from bitcoin.controller import Controller
from common import debug
from conf import bitcoin as bitcoin_conf
from sql import SQL
from xmpp.protocol import JID

FIELD_ID = 'id'
FIELD_JID = 'registered_jid'
TABLE_REG = 'registrations'
TABLE_ADDR = 'bitcoin_addresses'
FIELD_ADDRESS = 'address'

class UserAccount(JID):
    '''Represents a user that's registered on the gateway.'''

    def __init__(self, jid=None, node='', domain='', resource=''):
        '''Constructor. Initializes an account based on their JID.'''
        JID.__init__(self, jid, node, domain, resource)
        self.jid = self.__str__(0)

    @staticmethod
    def getAllContacts():
        '''Return the list of all JIDs that are registered on the component.'''
        req = "select %s from %s" % (FIELD_JID, TABLE_REG)
        SQL().execute(req)
        result = SQL().fetchall()
        return [result[i][0] for i in range(len(result))]

    def isRegistered(self):
        '''Return whether a given JID is already registered.'''
        req = "select %s from %s where %s=?" % (FIELD_ID, TABLE_REG, FIELD_JID)
        SQL().execute(req, (unicode(self.jid),))
        return SQL().fetchone() is not None

    def register(self):
        '''Add given JID to subscribers if possible. Raise exception otherwise.'''
        if self.isRegistered():
            raise AlreadyRegisteredError
        req = "insert into %s (%s) values (?)" % (TABLE_REG, FIELD_JID)
        SQL().execute(req, (self.jid,))

    def unregister(self):
        '''Remove given JID from subscribers if it exists. Raise exception otherwise.'''
        req = "delete from %s where %s=?" % (TABLE_REG, FIELD_JID)
        curs = SQL().execute(req, (self.jid,))
        if curs:
            count = curs.rowcount
            debug("%s rows deleted." % count)
            if 0 == count:
                raise AlreadyUnregisteredError
            elif 1 != count:
                debug("We deleted %s rows when unregistering %s. This is not normal." % (count, jid))

    def getAddresses(self):
        '''Return the set of all user's addresses'''
        req = "select %s from %s where %s=?" % (FIELD_ADDRESS, TABLE_ADDR, FIELD_JID)
        SQL().execute(req, (self.jid,))
        result = SQL().fetchall()
        return [result[i][0] for i in range(len(result))]

    def getBalance(self):
        '''Return the user's current balance'''
        total_received = 0
        for address in self.getAddresses():
            total_received += Controller().getreceivedbyaddress(address)
        #TODO: Substract payments made by this user, when they can made them
        return total_received

    def createAddress(self, label=None):
        '''Create a new bitcoin address, associate it with the user, and return it'''
        address = Address()
        if label is not None:
            address.setLabel(label)
        req = "insert into %s (%s, %s) values (?, ?)" % (TABLE_ADDR, FIELD_ADDRESS, FIELD_JID)
        SQL().execute(req, (str(address), self.jid))
        #TODO: Check that the creation went well before returning the address
        return address

    def ownsAddress(self, address):
        address = str(address)
        return True #TODO: Check whether the user really owns this address

class AlreadyRegisteredError(Exception):
    '''A JID is already registered at the gateway.'''
    pass

class AlreadyUnregisteredError(Exception):
    '''An unregisration was asked but the JID wasn't registered at the gateway.'''
    pass
