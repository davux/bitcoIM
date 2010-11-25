# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from bitcoim.address import Address
from bitcoin.controller import Controller
from common import debug
from conf import bitcoin as bitcoin_conf
from db import SQL
from xmpp.protocol import JID

FIELD_ID = 'id'
FIELD_JID = 'registered_jid'
TABLE_REG = 'registrations'
TABLE_ADDR = 'bitcoin_addresses'
FIELD_ADDRESS = 'address'

class UserAccount(object):
    '''Represents a user that's registered on the gateway.
       This class has a unique field: jid, which is the string
       representation of the user's bare JID.
    '''

    cache = {}

    def __new__(cls, jid):
        '''Create the UserAccount instance, based on their JID.
           The jid variable must be of type JID. The resource is
           ignored, only the bare JID is taken into account.'''
        jid = jid.getStripped()
        if jid not in cls.cache:
            debug("Creating new UserAccount in cache for %s" % jid)
            cls.cache[jid] = object.__new__(cls)
            cls.cache[jid].jid = jid
            cls.cache[jid].resources = set()
        debug("Returning UserAccount(%s)" % jid)
        return cls.cache[jid]

    def __str__(self):
        '''The textual representation of a UserAccount is the bare JID.'''
        return self.jid

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
            req = "delete from %s where %s=?" % (TABLE_ADDR, FIELD_JID)
            SQL().execute(req, (self.jid,))

    def resourceConnects(self, resource):
        self.resources.add(resource)

    def resourceDisconnects(self, resource):
        try:
            self.resources.remove(resource)
        except KeyError:
            pass # An "unavailable" presence is sent twice. Ignore.

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
        address.label = label
        req = "insert into %s (%s, %s) values (?, ?)" % (TABLE_ADDR, FIELD_ADDRESS, FIELD_JID)
        SQL().execute(req, (str(address), self.jid))
        #TODO: Check that the creation went well before returning the address
        return address

    def ownsAddress(self, address):
        req = "select %s from %s where %s=? and %s=?" % (FIELD_ID, TABLE_ADDR, FIELD_ADDR, FIELD_JID)
        SQL().execute(req, (str(address), self.jid))
        return SQL().fetchone() is not None

class AlreadyRegisteredError(Exception):
    '''A JID is already registered at the gateway.'''
    pass

class AlreadyUnregisteredError(Exception):
    '''An unregisration was asked but the JID wasn't registered at the gateway.'''
    pass
