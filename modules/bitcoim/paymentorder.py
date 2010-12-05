from common import debug
from datetime import datetime
from db import SQL
import random

class PaymentOrder(object):
    '''A payment order.'''

    def __init__(self, from_jid, address=None, amount=None, comment='', fee=0, code=None):
        self.jid = from_jid
        if code is None:
            self.address = address
            self.amount = amount
            self.comment = comment
            self.fee = fee
            self.date = None
        else:
            self.code = code
            condition = 'from_jid=? and code=?'
            values = [from_jid, code]
            if address is not None:
                condition += ' and recipient=?'
                values.append(address)
            if amount is not None:
                condition += ' and amount=?'
                values.append(amount)
            if comment is not None:
                condition += ' and comment=?'
                values.append(comment)
            if fee is not None:
                condition += ' and fee=?'
                values.append(fee)
            req = 'select %s, %s, %s, %s, %s from %s where %s' % \
                  ('date', 'recipient', 'amount', 'comment', 'fee', \
                   'payments', condition)
            SQL().execute(req, tuple(values))
            paymentOrder = SQL().fetchone()
            if paymentOrder is None:
                raise PaymentNotFoundError
            else:
                (self.date, self.address, self.amount, \
                 self.comment, self.fee) = tuple(paymentOrder)

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

class PaymentNotFoundError(Exception):
    '''The requested payment was not found.'''
