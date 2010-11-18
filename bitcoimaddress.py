from conf import component
from bitcoin.address import Address
from xmpp.protocol import JID

class BitcoIMAddress(Address):
    '''A Bitcoin address, but with some xmpp-specific capabilities.'''

    ENCODING_SEP = '-'

    def __init__(self, address=None):
        '''Constructor. Initialize a bitcoin address normally.
           If the argument is a JID object, though, decode it first.
        '''
        if 'JID' == address.__class__.__name__:
            address = address.getNode()
            parts = address.partition(self.ENCODING_SEP)
            if len(parts[2]):
                positions = int(parts[2], 36)
                address = ''
                for c in reversed(parts[0]):
                    if c.isalpha():
                        if (positions % 2):
                            c = c.upper()
                        positions //= 2
                    address = c + address
        Address.__init__(self, address)

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
            digit = mask % 36
            suffix = "0123456789abcdefghijklmnopqrstuvwxyz"[digit] + suffix
            mask /= 36
        if ("" != suffix):
            suffix = self.ENCODING_SEP + suffix
        return JID(node=self.address.lower() + suffix, domain=component['jid'])

