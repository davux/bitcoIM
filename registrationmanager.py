# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from common import debug
from sql import SQL

FIELD_ID = 'id'
FIELD_JID = 'registered_jid'
TABLE_REG = 'registrations'

class RegistrationManager:
    '''Handling of registrations.'''
    #TODO: Make sure how to behave with empty result sets (for isRegistered).

    def getAllContacts(self):
        '''Return the list of all JIDs that are registered on the component.'''
        req = "select %s from %s" % (FIELD_JID, TABLE_REG)
        debug('About to execute: [%s]' % req)
        SQL().execute(req)
        SQL().commit()
        result = SQL().fetchall()
        return [result[i][0] for i in range(len(result))]

    def isRegistered(self, jid):
        '''Return whether a given JID is already registered.'''
        debug('We want to know whether %s is registered.' % jid)
        req = "select %s from %s where %s=%s" % (FIELD_ID, TABLE_REG, FIELD_JID, '%s')
        debug('About to execute: [%s]' % req)
        SQL().execute(req, (jid,))
        SQL().commit()
        result = SQL().fetchall()
        return (0 != len(result))

    def registerJid(self, jid):
        '''Add given JID to subscribers if possible. Raise exception otherwise.'''
        if self.isRegistered:
            raise AlreadyRegisteredError
        req = "insert into %s (%s) values (%s)" % (TABLE_REG, FIELD_JID, '%s')
        SQL().execute(req, (jid,))
        SQL().commit()

class AlreadyRegisteredError(Exception):
    '''A JID is already registered at the gateway.'''
    pass
