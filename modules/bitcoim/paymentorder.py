from common import debug
from datetime import datetime
from db import SQL
import random

class PaymentOrder(object):
    '''A payment order.'''

    def __init__(self, from_jid, address, amount, comment='', fee=0, code=None, date=None):
        self.jid = from_jid
        self.address = address
        self.amount = amount
        self.comment = comment
        self.fee = fee
        self.code = code
        self.date = date

    @staticmethod
    def genConfirmationCode(length=4, alphabet='abcdefghjkmnpqrstuvwxyz23456789'):
        '''Generate a random confirmation code of variable length, taken from a
           given set of characters. By default, the length is 6 and the possible
           characters are lowercase letters (except o, i and l to avoid confusion)
           and numbers (except 0 and 1, for the same reason).
        '''
        debug("Trying to pick a %s-char word out of %s" % (length, alphabet))
        return ''.join(random.sample(alphabet, length)) 

    def queue(self):
        '''Insert a payment order into the database.'''
        self.code = PaymentOrder.genConfirmationCode()
        self.date = datetime.now()
        req = 'insert into %s (%s, %s, %s, %s, %s, %s, %s) values (?, ?, ?, ?, ?, ?, ?)' % \
              ('payments', 'from_jid', 'date', 'recipient', 'amount', 'comment', 'confirmation_code', 'fee')
        SQL().execute(req, (self.jid, self.date, self.address, self.amount, self.comment, self.code, self.fee))
