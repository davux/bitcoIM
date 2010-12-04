COMMAND_HELP = 'help'
COMMAND_PAY = 'pay'

def parse(line):
    '''Parse a command line and return a tuple (action, arguments), where
       action is a word, and arguments is an array of words.
       If the line is empty, None is returned.'''
    parts = line.split(None, 1)
    if 0 == len(parts):
        return None
    action = parts.pop(0)
    try:
        arguments = parts[0].split()
    except IndexError:
        arguments = []
    return (action, arguments)


class Command(object):
    '''A command that is sent to the component.'''

    def __init__(self, action, user=None, arguments=[], target=None):
        '''Constructor. user is the user that sent the command, action is the
           action to perform. arguments is an array of words, target is either
           an address or None if it's the gateway itself.'''
        self.action = action.lower()
        self.user = user
        self.arguments = arguments
        self.target = target

    def usage(self):
        if COMMAND_PAY == self.action:
            return 'pay <amount> [<reason>]\n - <amount> must be a positive number\n - <reason> is a free-form text'
        elif COMMAND_HELP == self.action:
            return 'help [<command>]'
        else:
            raise UnknownCommandError

    def execute(self):
        if self.user is None:
            raise AnonymousCommandError
        if COMMAND_PAY == self.action:
            if self.target is None:
                raise CommandTargetError
            try:
                amount = self.arguments.pop(0)
            except IndexError:
                raise CommandSyntaxError, 'You must specify an amount.'
            try:
                comment = self.arguments.pop(0)
            except IndexError:
                comment = ''
            return self._executePay(user.jid, amount, self.target, comment)
        elif COMMAND_HELP == self.action:
            try:
                targetCommand = self.arguments.pop(0)
            except IndexError:
                targetCommand = None
            return self._executeHelp(self.target, targetCommand)
        else:
            raise UnknownCommandError

    def _executePay(self, sender, amount, address, comment=''):
        try:
            amount = int(amount)
        except ValueError:
            raise CommandSyntaxError, 'The amount must be a number.'
        if amount <= 0:
            raise CommandSyntaxError, 'The amount must be positive.'
        order = PaymentOrder(sender.jid, address, amount, comment)
        order.queue()
        reply = "You want to pay BTC %s to address %s" % (amount, order.address)
        if 0 != len(comment):
            reply += ' (%s)' % comment
        reply += ". Please confirm by typing: confirm %s" % order.code
        return reply

    def _executeHelp(self, target, command=None):
        if command is None:
            if target is None:
                reply = 'Possible commands: help. Type \'help <command>\' for details. You can also type a bitcoin address directly to start a chat.'
            else:
                reply = 'Possible commands: pay, help. Type \'help <command>\' for details.'
        else:
            try:
                reply = "Usage: " + Command(command).usage()
            except UnknownCommandError:
                raise CommandSyntaxError, 'help: No such command \'%s\'' % command
        return reply


class CommandError(Exception):
    '''Generic error in command.'''

class CommandSyntaxError(CommandError):
    '''There was a syntax in the command.'''

class UnknownCommandError(CommandSyntaxError):
    '''Unknown command.'''

class CommandTargetError(CommandError):
    '''The target of the command is wrong (address instead of gateway or
       viceversa).'''

class AnonymousCommandError(CommandError):
    '''No user was given, so the command can't be executed. This is a
       programming error.'''
