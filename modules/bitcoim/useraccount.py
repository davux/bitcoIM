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
        #TODO: Simply check whether this user has an address
        req = "select %s from %s where %s=?" % (FIELD_ID, TABLE_REG, FIELD_JID)
        SQL().execute(req, (unicode(self.jid),))
        return SQL().fetchone() is not None

    def register(self):
        '''Add given JID to subscribers if possible. Raise exception otherwise.'''
        #TODO: Simply create an address for them
        if self.isRegistered():
            raise AlreadyRegisteredError
        req = "insert into %s (%s) values (?)" % (TABLE_REG, FIELD_JID)
        SQL().execute(req, (self.jid,))

    def unregister(self):
        '''Remove given JID from subscribers if it exists. Raise exception otherwise.'''
        #TODO: Simply delete or change the account information on the user's address(es)
        req = "delete from %s where %s=?" % (TABLE_REG, FIELD_JID)
        curs = SQL().execute(req, (self.jid,))
        if curs:
            count = curs.rowcount
            debug("%s rows deleted." % count)
            if 0 == count:
                raise AlreadyUnregisteredError
            elif 1 != count:
                debug("We deleted %s rows when unregistering %s. This is not normal." % (count, jid))

    def resourceConnects(self, resource):
        self.resources.add(resource)

    def resourceDisconnects(self, resource):
        try:
            self.resources.remove(resource)
        except KeyError:
            pass # An "unavailable" presence is sent twice. Ignore.

    def getAddresses(self):
        '''Return the set of all addresses the user has control over'''
        return Controller().getaddressesbyaccount(self.jid)

    def getTotalReceived(self):
        '''Returns the total amount received on all addresses the user has control over.'''
        return Controller().getreceivedbyaccount(self.jid)

    def getRoster(self):
        '''Return the set of all the address JIDs the user has in her/his roster.
           This is different from the addresses the user has control over:
             - the user might want to ignore one of their own addresses,
               because there's no need to see them.
             - the user might want to see some addresses s/he doesn't own, in
               order to be able to easily send bitcoins to them.
             - they are JIDs, not bitcoin addresses.
        '''
        #TODO: Make it an independant list. As a placeholder, it's currently
        #      equivalent to getAddresses().
        roster = set()
        for addr in self.getAddresses():
            roster.add(Address(addr).jid)
        return roster

    def getBalance(self):
        '''Return the user's current balance'''
        #TODO: Substract payments made by this user, when they can made them
        return self.getTotalReceived()

    def createAddress(self):
        '''Create a new bitcoin address, associate it with the user, and return it'''
        address = Address()
        Controller().setaccount(address.address, self.jid)
        return address

    def ownsAddress(self, address):
        return self.jid == address.account

    def command(self, cmd, address=None):
        '''Interpret a command sent as a message. Return a line to show to the user.
           The 'address' argument is the bitcoin address the command is about.
           If address is None, the command was sent to the gateway itself.'''
        cmd = cmd.split(None, 1)
        if 0 == len(cmd):
            return None
        verb = cmd.pop(0).lower()
        try:
            args = cmd[0]
        except IndexError:
            args = ''
        # Now parsing can begin: args is a string, ready to be split in a variable number
        # of parts, depending on the verb.
        if 'pay' == verb:
            if address is None:
                raise CommandTargetError
            args = args.split(None, 1)
            try:
                amount = int(args.pop(0))
            except IndexError:
                raise CommandSyntaxError, 'You must specify an amount.'
            except ValueError:
                raise CommandSyntaxError, 'The amount must be a number.'
            if amount <= 0:
                raise CommandSyntaxError, 'The amount must be positive.'
            try:
                comment = args.pop(0)
            except IndexError:
                comment = ''
            order = PaymentOrder(self.jid, address, amount, comment)
            order.queue()
            reply = "You want to pay BTC %s to address %s" % (amount, order.address)
            if 0 != len(comment):
                reply += ' (%s)' % comment
            reply += ". Please confirm by typing: confirm %s" % order.code
        elif 'help' == verb:
            args = args.lower()
            if 'help' == args:
                reply = 'Usage: help [<command>]'
            elif 'pay' == args:
                reply = 'Usage: pay <amount> [<reason>]\n - <amount> must be a positive number\n - <reason> is a free-form text'
            elif '' == args:
                if address is None:
                    reply = 'Possible commands: help. Type \'help <command>\' for details. You can also type a bitcoin address directly to start a chat.'
                else:
                    reply = 'Possible commands: pay, help. Type \'help <command>\' for details.'
            else:
                raise CommandSyntaxError, 'help: No such command \'%s\'' % args
        else:
            raise CommandSyntaxError, 'Unknown command \'%s\'' % verb
        return reply


class AlreadyRegisteredError(Exception):
    '''A JID is already registered at the gateway.'''
    pass

class AlreadyUnregisteredError(Exception):
    '''An unregisration was asked but the JID wasn't registered at the gateway.'''
    pass

class CommandError(Exception):
    '''Generic error in command.'''

class CommandSyntaxError(CommandError):
    '''There was a syntax in the command.'''
    pass

class CommandTargetError(CommandError):
    '''The target of the command is wrong (address instead of gateway or viceversa).'''
    pass
