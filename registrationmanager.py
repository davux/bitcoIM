# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from common import debug
from sql import SQL

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