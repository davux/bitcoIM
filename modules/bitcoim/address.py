from conf import component
from bitcoin.address import Address as BCAddress
from paymentorder import PaymentOrder
from xmpp.protocol import JID

ENCODING_SEP = '-'
ENCODING_BASE = 36 # Any value from 2 to 36 would work - smaller values produce longer suffixes

class Address(BCAddress):
    '''A Bitcoin address, but with some xmpp-specific capabilities.'''

    def __init__(self, address=None):
        '''Constructor. Initialize a bitcoin address normally.
           If the argument is a JID object, though, decode it first.
        '''
        if 'JID' == address.__class__.__name__:
            address = address.getNode()
            parts = address.partition(ENCODING_SEP)
            if len(parts[2]):
                positions = int(parts[2], ENCODING_BASE)
                address = ''
                for c in reversed(parts[0]):
                    if c.isalpha():
                        if (positions % 2):
                            c = c.upper()
                        positions //= 2
                    address = c + address
        BCAddress.__init__(self, address)

    def asJID(self):
        '''
        1DXFn72VHrXRVYJTTxjbmNXyXpYXmgiWfw
        1dxfn72vhrxrvyjttxjbmnxyxpyxmgiwfw (lowercase)
         1110  110111111100001101011000100 (mask on uppercase)
        -> mask in base36 (should return x0l0p0)
        '''
        mask = long(0)
        gaps = 0
        for i, char in enumerate(reversed(self.address)):
            if char.isupper():
                mask += 2 ** (i - gaps)
            elif char.isdigit():
                gaps += 1
        suffix = ""
        while mask > 0:
            suffix = "0123456789abcdefghijklmnopqrstuvwxyz"[mask % ENCODING_BASE] + suffix
            mask //= ENCODING_BASE
        if ("" != suffix):
            suffix = ENCODING_SEP + suffix
        return JID(node=self.address.lower() + suffix, domain=component['jid'])

    def getOwner(self):
        from db import SQL
        req = "select %s from %s where %s=?" % ('registered_jid', 'bitcoin_addresses', 'address')
        SQL().execute(req, (self.address,))
        row = SQL().fetchone()
        if row:
            return row[0]
        else:
            return None

    def getPercentageReceived(self):
        '''Returns the percentage of bitcoins received on this address over the total received
           by the same user. If nothing was received yet, return None.'''
        from useraccount import UserAccount
        user = UserAccount(JID(self.getOwner()))
        if user is None: # Shouldn't happen: we normally only care about addresses with an owner
            total = self.getReceived() # This way we always return 100%. TODO: use an exception
        else:
            total = user.getTotalReceived()
        if 0 != total:
            return self.getReceived() * 100 / total
        else:
            return None

    def command(self, userJID, cmd):
        '''Interpret a command sent as a message. Return a line to show to the user.
           NOTE: This function might not stay here.'''
        words = cmd.split(None, 2)
        if 0 == len(words):
            return None
        if 'pay' == words[0]:
            try:
                amount = int(words[1])
            except IndexError:
                raise CommandSyntaxError, 'You must specify an amount.'
            except ValueError:
                raise CommandSyntaxError, 'The amount must be a number.'
            if amount <= 0:
                raise CommandSyntaxError, 'The amount must be positive.'
            try:
                comment = words[2]
            except IndexError:
                comment = ''
            order = PaymentOrder(userJID, self.address, amount, comment)
            order.queue()
            reply = "You want to pay BTC %s to address %s" % (amount, order.address)
            if 0 != len(comment):
                reply += ' (%s)' % comment
            reply += ". Please confirm by typing: confirm %s" % order.code
            return reply
        else:
            raise CommandSyntaxError, 'Unknown command \'%s\'' % words[0]

class CommandSyntaxError(Exception):
    '''There was a syntax in the command.'''
    pass
