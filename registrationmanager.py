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

    def unregisterJid(self, jid):
        '''Remove given JID from subscribers if it exists. Raise exception otherwise.'''
        req = "delete from %s where %s=%s" % (TABLE_REG, FIELD_JID, '%s')
        curs = SQL().execute(req, (jid,))
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
