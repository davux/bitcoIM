# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

import app
from common import problem, debug
from conf import bitcoin as bitcoin_conf
from jsonrpc import ServiceProxy
from registrationmanager import RegistrationManager, AlreadyRegisteredError
from xmpp.client import Component
from xmpp.protocol import JID, Iq, Presence, Error, NodeProcessed, \
                          NS_IQ, NS_MESSAGE, NS_PRESENCE, NS_DISCO_INFO, \
                          NS_REGISTER
from xmpp.simplexml import Node
from xmpp.browser import Browser

class BitcoimComponent:
    '''The component itself.'''

    def __init__(self, jid, password, server, port=5347):
        '''Constructor.
           - Establish a session
           - Declare handlers
        '''
        self.bye = False
        self.cnx = Component(server, port, debug=['socket'])
        self.jid = jid
        if not self.cnx.connect():
            raise Exception('Unable to connect to %s:%s' % (server, port))
        if not self.cnx.auth(jid, password):
            raise Exception('Unable to authenticate as %s' % (jid))
        self.bitcoin = ServiceProxy("http://%s:%s@127.0.0.1:8332" % (bitcoin_conf['user'], bitcoin_conf['password']))
        try:
            debug("Connected to bitcoin. Balance: %s" % self.bitcoin.getbalance())
        except IOError:
            raise Exception('Unable to connect to JSON server as %s' % (bitcoin_conf['user']))
        self.cnx.RegisterHandler(NS_MESSAGE, self.messageReceived)
        self.cnx.RegisterHandler(NS_PRESENCE, self.presenceReceived)
        self.cnx.RegisterHandler(NS_IQ, self.iqReceived)
        self.handleDisco(self.cnx)
        self.regManager = RegistrationManager()
        for jid in self.regManager.getAllContacts():
            self.cnx.send(Presence(to=jid, frm=self.jid, typ='probe'))
            self.sendBitcoinPresence(self.cnx, JID(jid))

    def handleDisco(self, cnx):
        '''Define the Service Discovery information for automatic handling
           by the xmpp library.
        '''
        browser = Browser()
        browser.PlugIn(cnx)
        ids = [{'category': 'gateway', 'type': 'bitcoin',
               'name':app.identifier}]
        info = {'ids': ids, 'features': [NS_DISCO_INFO, NS_REGISTER]}
        browser.setDiscoHandler({'items': [], 'info': info})

    def loop(self, timeout=0):
        '''Main loop. Listen to incoming stanzas.'''
        while not self.bye:
            self.cnx.Process(timeout)

    def sayGoodbye(self):
        '''Ending method. Doesn't do anything interesting yet.'''
        debug("Bye.")

    def sendBitcoinPresence(self, cnx, jid):
        if not self.regManager.isRegistered(jid.getStripped()):
            return
        prs = Presence(to=jid, typ='available', show='chat', frm=self.jid,
                       status='Current balance: %s' % self.bitcoin.getbalance())
        cnx.send(prs)

    def messageReceived(self, cnx, msg):
        '''Message received'''
        if not self.regManager.isRegistered(msg.getFrom().getStripped()):
            return
        debug("Message received from subscriber %s" % msg.getBody())

    def presenceReceived(self, cnx, prs):
        '''Presence received'''
        typ = prs.getType()
        frm = prs.getFrom()
        to = prs.getTo().getStripped()
        if to != self.jid:
            return
        if typ == 'subscribe':
            if self.regManager.isRegistered(frm.getStripped()):
                cnx.send(Presence(typ='subscribed', frm=self.jid, to=frm))
                self.sendBitcoinPresence(cnx, frm)
            else:
                debug("Simple subscription request without prior registration. What should we do?")
        elif typ == 'subscribed':
            debug('We were allowed to see %s\'s presence.')
        elif typ == 'unsubscribe':
            debug('Just received an "unsubscribe" presence stanza. What does that mean?')
        elif typ == 'unsubscribed':
            debug('Unsubscribed. Any interest in this information?')
        elif typ == 'probe':
            self.sendBitcoinPresence(cnx, frm)
        elif typ == 'error':
            debug('Presence error. Just ignore it?')
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
                registered = self.regManager.isRegistered(iq.getFrom().getStripped())
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
        else:
            debug("Unhandled IQ namespace '%s'. TODO: handle it!" % ns)

    def registrationRequested(self, cnx, iq):
        '''A registration request was received'''
        frm = iq.getFrom()
        debug("Registration request from %s" % frm)
        isUpdate = False
        try:
            self.regManager.registerJid(frm.getStripped())
        except AlreadyRegisteredError:
            isUpdate = True # This would be stupid, since there's no registration info to update
        cnx.send(Iq(typ='result', to=frm, frm=self.jid, attrs={'id': iq.getID()}))
        if not isUpdate:
            cnx.send(Presence(typ='subscribe', to=frm, frm=self.jid))

    def unregistrationRequested(self, cnx, iq):
        '''An unregistration request was received'''
        frm = iq.getFrom().getStripped()
        self.regManager.unregisterJid(frm)
        cnx.send(iq.buildReply('result'))
        cnx.send(Presence(to=frm, frm=self.jid, typ='unsubscribe'))
        cnx.send(Presence(to=frm, frm=self.jid, typ='unsubscribed'))
        cnx.send(Presence(to=frm, frm=self.jid, typ='unavailable', status='Thanks for using this service. Bye!'))
