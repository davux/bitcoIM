# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from common import debug
from conf import bitcoin as bitcoin_conf
from jsonrpc import ServiceProxy
from sql import SQL
from xmpp.protocol import JID

FIELD_ID = 'id'
FIELD_JID = 'registered_jid'
TABLE_REG = 'registrations'

class UserAccount(JID):
    '''Represents a user that's registered on the gateway.'''

    bitcoin = ServiceProxy("http://%s:%s@127.0.0.1:8332" % (bitcoin_conf['user'], bitcoin_conf['password']))
    bitcoin.getinfo() # Testing the connection early, so that an exception can be raised if it doesn't work

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

    def getBalance(self):
        '''Return the user's current balance'''
        #XXX: This is wrong. The user's balance is only a fraction of the whole wallet's.
        return self.bitcoin.getbalance()

class AlreadyRegisteredError(Exception):
    '''A JID is already registered at the gateway.'''
    pass

class AlreadyUnregisteredError(Exception):
    '''An unregisration was asked but the JID wasn't registered at the gateway.'''
    pass
