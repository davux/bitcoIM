# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

import app
from common import problem, debug
from conf import bitcoin as bitcoin_conf
from jsonrpc import ServiceProxy
from registrationmanager import RegistrationManager
from xmpp.client import Component
from xmpp.protocol import JID, Presence, Error, NodeProcessed, \
                          NS_IQ, NS_MESSAGE, NS_PRESENCE, NS_DISCO_INFO
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
        self.reg_manager = RegistrationManager()
        for jid in self.reg_manager.getAllContacts():
            self.cnx.send(Presence(to=jid, frm=self.jid, typ='probe'))

    def handleDisco(self, cnx):
        '''Define the Service Discovery information for automatic handling
           by the xmpp library.
        '''
        browser = Browser()
        browser.PlugIn(cnx)
        ids = [{'category': 'gateway', 'type': 'xmpp',
               'name':app.identifier}]
        info = {'ids': ids, 'features': [NS_DISCO_INFO]}
        browser.setDiscoHandler({'items': [], 'info': info})

    def loop(self, timeout=0):
        '''Main loop. Listen to incoming stanzas.'''
        while not self.bye:
            self.cnx.Process(timeout)

    def sayGoodbye(self):
        '''Ending method. Doesn't do anything interesting yet.'''
        debug("Bye.")

    def messageReceived(self, cnx, msg):
        '''Message received'''

    def presenceReceived(self, cnx, prs):
        '''Presence received'''

    def iqReceived(self, cnx, iq):
        '''IQ received'''
