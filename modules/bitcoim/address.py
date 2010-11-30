from conf import component
from bitcoin.address import Address as BCAddress
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
           by the same user.'''
        from useraccount import UserAccount
        user = UserAccount(JID(self.getOwner()))
        if user is None: # Shouldn't happen: we normally only care about addresses with an owner
            total = self.getReceived() # This way we always return 100%. TODO: use an exception
        else:
            total = user.getTotalReceived()
        return self.getReceived() * 100 / total
