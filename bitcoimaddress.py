from conf import component
from bitcoin.address import Address
from xmpp.protocol import JID

class BitcoIMAddress(Address):
    '''A Bitoin address, but with some boosted capacities.'''

    def __init__(self, address=None):
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
            suffix = '-' + suffix
        return JID(node=self.address.lower() + suffix, domain=component['jid'])

