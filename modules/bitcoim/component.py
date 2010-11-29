# -*- coding: utf-8 -*-
# vi: sts=4 et sw=4

from bitcoim.address import Address
from bitcoin.address import InvalidBitcoinAddressError
from bitcoin.controller import Controller, BitcoinServerIOError
from common import problem, debug
from conf import bitcoin as bitcoin_conf
from useraccount import UserAccount, AlreadyRegisteredError
from xmpp.client import Component as XMPPComponent
from xmpp.protocol import JID, Iq, Presence, Error, NodeProcessed, \
                          NS_IQ, NS_MESSAGE, NS_PRESENCE, NS_DISCO_INFO, \
                          NS_DISCO_ITEMS, NS_GATEWAY, NS_REGISTER, NS_VERSION
from protocol import NS_NICK
from xmpp.simplexml import Node
from xmpp.browser import Browser

APP_NAME = 'BitcoIM'
APP_IDENTIFIER = 'bitcoim'
APP_VERSION = '0.1'
APP_DESCRIPTION = 'Bitcoin payment orders via XMPP'

class Component:
    '''The component itself.'''

    def __init__(self, jid, password, server, port=5347):
        '''Constructor.
           - Establish a session
           - Declare handlers
           - Send initial presence probe to all users
           - Send initial presence broadcasts to all users, from the gateway
             and from each of their "contacts" (bitcoin addresses)
        '''
        self.bye = False
        Controller(bitcoin_conf['user'], bitcoin_conf['password']).getinfo() # This will raise an exception if there's a connection problem
        self.cnx = XMPPComponent(jid, port, debug=['socket'])
        self.jid = jid
        self.connectedUsers = set()
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
            user = UserAccount(JID(jid))
            self.sendBitcoinPresence(self.cnx, user)
            for addr in user.getRoster():
                self.sendBitcoinPresence(self.cnx, user, Address(addr))

    def handleDisco(self, cnx):
        '''Define the Service Discovery information for automatic handling
           by the xmpp library.
        '''
        browser = Browser()
        browser.PlugIn(cnx)
        ids = [{'category': 'gateway', 'type': 'bitcoin',
               'name':APP_DESCRIPTION}]
        info = {'ids': ids, 'features': [NS_DISCO_INFO, NS_DISCO_ITEMS, NS_REGISTER, NS_VERSION, NS_GATEWAY]}
        items = [{'jid': self.jid, 'name': APP_DESCRIPTION}]
        browser.setDiscoHandler({'items': items, 'info': info})

    def loop(self, timeout=0):
        '''Main loop. Listen to incoming stanzas.'''
        while not self.bye:
            self.cnx.Process(timeout)

    def sayGoodbye(self):
        '''Ending method. Doesn't do anything interesting yet.'''
        for user in self.connectedUsers:
            self.cnx.send(Presence(to=user.jid, frm=self.jid, typ='unavailable',
                          status='Service is shutting down. See you later.'))
        debug("Bye.")

    def sendBitcoinPresence(self, cnx, user, address=None):
        '''Send a presence information to the user, from a specific address.
           If address is None, send information from the gateway itself.
        '''
        if not user.isRegistered():
            return
        if address is None:
            prs = Presence(to=user.jid, typ='available', show='online', frm=self.jid,
                           status='Current balance: %s' % user.getBalance())
        else:
            #TODO: More useful information (number/percentage of payments received?)
            prs = Presence(to=user.jid, typ='available', show='online', frm=address.asJID())
        cnx.send(prs)

    def addAddressToRoster(self, cnx, address, user):
        msg = 'Hi! I\'m your new Bitcoin address'
        label = address.label
        if 0 != len(label):
            msg += ' (%s)' % label
        pres = Presence(typ='subscribe', status=msg, frm=address.asJID(), to=user.jid)
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
        frm = prs.getFrom()
        resource = frm.getResource()
        user = UserAccount(frm)
        to = prs.getTo().getStripped()
        if not user.isRegistered():
            return #TODO: Send a registration-required error
        typ = prs.getType()
        if to == self.jid:
            if typ == 'subscribe':
                cnx.send(Presence(typ='subscribed', frm=to, to=user.jid))
            elif typ == 'subscribed':
                debug('We were allowed to see %s\'s presence.' % user)
            elif typ == 'unsubscribe':
                debug('Just received an "unsubscribe" presence stanza. What does that mean?')
            elif typ == 'unsubscribed':
                debug('Unsubscribed. Any interest in this information?')
            elif typ == 'probe':
                self.sendBitcoinPresence(cnx, user)
            elif (typ == 'available') or (typ is None):
                self.userResourceConnects(user, resource)
            elif typ == 'unavailable':
                self.userResourceDisconnects(user, resource)
            elif typ == 'error':
                debug('Presence error. TODO: Handle it by not sending presence updates to them until they send a non-error.')
        else:
            try:
                address = Address(JID(prs.getTo()))
            except InvalidBitcoinAddressError:
                debug("Invalid address %s" % prs.getTo())
                raise NodeProcessed # Just drop the case. TODO: Handle invalid addresses better
            if not user.ownsAddress(address):
                raise NodeProcessed # Just drop the case. TODO: Reply an error ("not-authorized" or something)
            if typ == 'subscribe':
                cnx.send(Presence(typ='subscribed', frm=to, to=user.jid))
            elif typ == 'unsubscribe':
                debug('%s doesn\'t want to see address %s anymore. We should really honor that.' % user) #TODO: Implement hiding of addresses
            elif typ == 'probe':
                self.sendBitcoinPresence(cnx, user, address)
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
            name.setData(APP_NAME)
            version = Node('version')
            version.setData(APP_VERSION)
            reply = iq.buildReply('result')
            query = reply.getTag('query')
            query.addChild(node=name)
            query.addChild(node=version)
            cnx.send(reply)
            raise NodeProcessed
        elif NS_GATEWAY == ns:
                if 'get' == typ:
                    desc = Node('desc')
                    desc.setData('Please enter the Bitcoin address you would like to add.')
                    prompt = Node('prompt')
                    prompt.setData('Bitcoin address')
                    reply = iq.buildReply('result')
                    query = reply.getTag('query')
                    query.addChild(node=desc)
                    query.addChild(node=prompt)
                    cnx.send(reply)
                    raise NodeProcessed
                elif 'set' == typ:
                    children = iq.getQueryChildren()
                    if (0 != len(children)) and ('prompt' == children[0].getName()):
                        prompt = children[0].getData()
                        try:
                            jid = Node('jid')
                            jid.setData(Address(prompt).asJID())
                            reply = iq.buildReply('result')
                            query = reply.getTag('query')
                            query.addChild(node=jid)
                        except InvalidBitcoinAddressError:
                            reply = iq.buildReply('error')
                            debug("TODO: Send an error because the address %s is invalid." % prompt)
                        cnx.send(reply)
                        raise NodeProcessed
        else:
            debug("Unhandled IQ namespace '%s'." % ns)

    def userResourceConnects(self, user, resource):
        '''Called when the component receives a presence"available" from a
           user. This method first registers the resource. Then, if it's the
           user's first online resource: sends them a presence packet, and
           internally adds them to the list of online users.'''
        user.resourceConnects(resource)
        if not user in self.connectedUsers:
            self.connectedUsers.add(user)

    def userResourceDisconnects(self, user, resource):
        '''Called when the component receives a presence "unavailable" from
           a user. This method first unregisters the resource. Then, if the
           user has no more online resource, sends them an "unavailable" presence,
           and internally removes them from the list of online users.'''
        user.resourceDisconnects(resource)
        if (user in self.connectedUsers) and (0 == len(user.resources)):
            #TODO: Send unavailable presence from bc addressses too
            self.cnx.send(Presence(typ='unavailable', frm=self.jid, to=user.jid))
            self.connectedUsers.remove(user)

    def registrationRequested(self, cnx, iq):
        '''A registration request was received'''
        frm = iq.getFrom()
        debug("Registration request from %s" % frm)
        isUpdate = False
        user = UserAccount(frm)
        try:
            user.register()
            new_address = user.createAddress('My first address at %s' % self.jid)
            self.addAddressToRoster(cnx, new_address, user)
        except AlreadyRegisteredError:
            isUpdate = True # This would be stupid, since there's no registration info to update
        cnx.send(Iq(typ='result', to=frm, frm=self.jid, attrs={'id': iq.getID()}))
        if not isUpdate:
            cnx.send(Presence(typ='subscribe', to=frm.getStripped(), frm=self.jid))

    def unregistrationRequested(self, cnx, iq):
        '''An unregistration request was received'''
        user = UserAccount(iq.getFrom())
        try:
            user.unregister()
        except AlreadyUnregisteredError:
            pass # We don't really mind about unknown people wanting to unregister. Should we?
        cnx.send(iq.buildReply('result'))
        cnx.send(Presence(to=user.jid, frm=self.jid, typ='unsubscribe'))
        cnx.send(Presence(to=user.jid, frm=self.jid, typ='unsubscribed'))
        cnx.send(Presence(to=user.jid, frm=self.jid, typ='unavailable', status='Thanks for using this service. Bye!'))
