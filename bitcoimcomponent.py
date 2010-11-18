# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

import app
from bitcoimaddress import BitcoIMAddress
from bitcoin.address import InvalidBitcoinAddressError
from bitcoin.controller import Controller, BitcoinServerIOError
from common import problem, debug
from conf import bitcoin as bitcoin_conf
from useraccount import UserAccount, AlreadyRegisteredError
from xmpp.client import Component
from xmpp.protocol import JID, Iq, Presence, Error, NodeProcessed, \
                          NS_IQ, NS_MESSAGE, NS_PRESENCE, NS_DISCO_INFO, \
                          NS_DISCO_ITEMS, NS_REGISTER, NS_VERSION
from protocol import NS_NICK
from xmpp.simplexml import Node
from xmpp.browser import Browser

class BitcoIMComponent:
    '''The component itself.'''

    def __init__(self, jid, password, server, port=5347):
        '''Constructor.
           - Establish a session
           - Declare handlers
        '''
        self.bye = False
        Controller(bitcoin_conf['user'], bitcoin_conf['password']).getinfo() # This will raise an exception if there's a connection problem
        self.cnx = Component(jid, port, debug=['socket'])
        self.jid = jid
        if not self.cnx.connect([server, port]):
            raise Exception('Unable to connect to %s:%s' % (server, port))
        if not self.cnx.auth(jid, password):
            raise Exception('Unable to authenticate as %s' % (jid))
        self.cnx.RegisterHandler(NS_MESSAGE, self.messageReceived)
        self.cnx.RegisterHandler(NS_PRESENCE, self.presenceReceived)
        self.cnx.RegisterHandler(NS_IQ, self.iqReceived)
        self.handleDisco(self.cnx)
        for jid in UserAccount.getAllContacts():
            self.cnx.send(Presence(to=jid, frm=self.jid, typ='probe'))

    def handleDisco(self, cnx):
        '''Define the Service Discovery information for automatic handling
           by the xmpp library.
        '''
        browser = Browser()
        browser.PlugIn(cnx)
        ids = [{'category': 'gateway', 'type': 'bitcoin',
               'name':app.description}]
        info = {'ids': ids, 'features': [NS_DISCO_INFO, NS_DISCO_ITEMS, NS_REGISTER, NS_VERSION]}
        items = [{'jid': self.jid, 'name': app.description}]
        browser.setDiscoHandler({'items': items, 'info': info})

    def loop(self, timeout=0):
        '''Main loop. Listen to incoming stanzas.'''
        while not self.bye:
            self.cnx.Process(timeout)

    def sayGoodbye(self):
        '''Ending method. Doesn't do anything interesting yet.'''
        for jid in UserAccount.getAllContacts():
            self.cnx.send(Presence(to=jid, frm=self.jid, typ='unavailable',
                          status='Service is shutting down. See you later.'))
        debug("Bye.")

    def sendBitcoinPresence(self, cnx, user, address=None):
        if not user.isRegistered():
            return
        #TODO: If address exists, don't show any status message, and change the "from"
        prs = Presence(to=user, typ='available', show='online', frm=self.jid,
                       status='Current balance: %s' % user.getBalance())
        cnx.send(prs)

    def addAddressToRoster(self, cnx, address, user):
        msg = 'Hi! I\'m your new Bitcoin address'
        label = address.label
        if 0 != len(label):
            msg += ' (%s)' % label
        pres = Presence(typ='subscribe', status=msg, frm=address.asJID(), to=user)
        nick = Node('nick')
        nick.setNamespace(NS_NICK)
        nick.setData(label)
        pres.addChild(node=nick)
        cnx.send(pres)

    def messageReceived(self, cnx, msg):
        '''Message received'''
        if not UserAccount(msg.getFrom()).isRegistered():
            return
        debug("Message received from subscriber %s" % msg.getBody())

    # If any presence stanza is received from an unregistered user, don't
    # even look at it. They should register first.
    def presenceReceived(self, cnx, prs):
        '''Presence received'''
        frm = UserAccount(prs.getFrom())
        to = prs.getTo().getStripped()
        if not frm.isRegistered():
            return #TODO: Send a registration-required error
        typ = prs.getType()
        if to == self.jid:
            if typ == 'subscribe':
                cnx.send(Presence(typ='subscribed', frm=to, to=frm))
            elif typ == 'subscribed':
                debug('We were allowed to see %s\'s presence.' % frm)
            elif typ == 'unsubscribe':
                debug('Just received an "unsubscribe" presence stanza. What does that mean?')
            elif typ == 'unsubscribed':
                debug('Unsubscribed. Any interest in this information?')
            elif typ == 'probe':
                self.sendBitcoinPresence(cnx, frm)
            elif (typ == 'available') or (typ is None):
                self.sendBitcoinPresence(cnx, frm)
            elif typ == 'unavailable':
                cnx.send(Presence(typ='unavailable', frm=to, to=frm))
            elif typ == 'error':
                debug('Presence error. Just ignore it?')
        else:
            try:
                address = BitcoIMAddress(JID(prs.getTo()).getNode())
            except InvalidBitcoinAddressError:
                raise NodeProcessed # Just drop the case. TODO: Handle invalid addresses better
            if not frm.ownsAddress(address):
                raise NodeProcessed # Just drop the case. TODO: Reply an error ("not-authorized" or something)
            if typ == 'subscribe':
                cnx.send(Presence(typ='subscribed', frm=to, to=frm))
            elif typ == 'unsubscribe':
                debug('%s doesn\'t want to see address %s anymore. We should really honor that.') #TODO: Implement hiding of addresses
            elif typ == 'probe':
                self.sendBitcoinPresence(cnx, frm, address)
            elif (typ == 'available') or (typ is None):
                self.sendBitcoinPresence(cnx, frm, address) # Funny way to show/hide addresses: send them directed presence
            elif typ == 'unavailable':
                cnx.send(Presence(typ='unavailable', frm=to, to=frm)) # Funny way to show/hide addresses: send them directed presence
        raise NodeProcessed

    def iqReceived(self, cnx, iq):
        '''IQ received'''
        typ = iq.getType()
        ns = iq.getQueryNS()
        if NS_REGISTER == ns:
            if 'set' == typ:
                children = iq.getQueryChildren()
                if (0 != len(children)) and ('remove' == children[0].getName()):
                    self.unregistrationRequested(cnx, iq)
                else:
                    self.registrationRequested(cnx, iq)
                raise NodeProcessed
            elif 'get' == typ:
                instructions = Node('instructions')
                registered = UserAccount(iq.getFrom()).isRegistered()
                if registered:
                    instructions.setData('There is no registration information to update. Simple as that.')
                else:
                    instructions.setData('Register? If you do, you\'ll get a Bitcoin address that you can use to send and receive payments via Bitcoin.')
                reply = iq.buildReply('result')
                query = reply.getTag('query')
                if registered:
                    query.addChild(node=Node('registered'))
                query.addChild(node=instructions)
                cnx.send(reply)
                raise NodeProcessed
            else:
                # Unkown namespace and type. The default handler will take care of it if we don't raise NodeProcessed.
                debug("Unknown IQ with ns '%s' and type '%s'." % (ns, typ))
        elif (NS_VERSION == ns) and ('get' == typ):
            name = Node('name')
            name.setData(app.name)
            version = Node('version')
            version.setData(app.version)
            reply = iq.buildReply('result')
            query = reply.getTag('query')
            query.addChild(node=name)
            query.addChild(node=version)
            cnx.send(reply)
            raise NodeProcessed
        else:
            debug("Unhandled IQ namespace '%s'." % ns)

    def registrationRequested(self, cnx, iq):
        '''A registration request was received'''
        frm = UserAccount(iq.getFrom())
        debug("Registration request from %s" % frm)
        isUpdate = False
        try:
            frm.register()
            new_address = frm.createAddress('My first address at %s' % self.jid)
            self.addAddressToRoster(cnx, new_address, frm)
        except AlreadyRegisteredError:
            isUpdate = True # This would be stupid, since there's no registration info to update
        cnx.send(Iq(typ='result', to=frm, frm=self.jid, attrs={'id': iq.getID()}))
        if not isUpdate:
            cnx.send(Presence(typ='subscribe', to=frm.getStripped(), frm=self.jid))

    def unregistrationRequested(self, cnx, iq):
        '''An unregistration request was received'''
        frm = UserAccount(iq.getFrom())
        try:
            frm.unregister()
            #TODO: Destroy all information about that user's addresses
        except AlreadyUnregisteredError:
            pass # We don't really mind about unknown people wanting to unregister. Should we?
        cnx.send(iq.buildReply('result'))
        cnx.send(Presence(to=frm, frm=self.jid, typ='unsubscribe'))
        cnx.send(Presence(to=frm, frm=self.jid, typ='unsubscribed'))
        cnx.send(Presence(to=frm, frm=self.jid, typ='unavailable', status='Thanks for using this service. Bye!'))
