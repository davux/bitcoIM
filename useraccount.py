# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from common import debug
from sql import SQL
from xmpp.protocol import JID

FIELD_ID = 'id'
FIELD_JID = 'registered_jid'
TABLE_REG = 'registrations'

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
        debug('About to execute: [%s]' % req)
        SQL().execute(req)
        result = SQL().fetchall()
        return [result[i][0] for i in range(len(result))]

    def isRegistered(self):
        '''Return whether a given JID is already registered.'''
        debug('We want to know whether %s is registered.' % self.jid)
        req = "select %s from %s where %s=?" % (FIELD_ID, TABLE_REG, FIELD_JID)
        debug('About to execute: [%s]' % req)
        SQL().execute(req, (unicode(self.jid),))
        result = SQL().fetchall()
        return (0 != len(result))

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
        debug("Executed %s on the database." % req)
        if curs:
            count = curs.rowcount
            debug("%s rows deleted." % count)
            if 0 == count:
                raise AlreadyUnregisteredError
            elif 1 != count:
                debug("We deleted %s rows when unregistering %s. This is not normal." % (count, jid))
        else:
            debug("Strange. Curs is %s." % curs)


class AlreadyRegisteredError(Exception):
    '''A JID is already registered at the gateway.'''
    pass

class AlreadyUnregisteredError(Exception):
    '''An unregisration was asked but the JID wasn't registered at the gateway.'''
    pass
