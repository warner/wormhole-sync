from __future__ import print_function, unicode_literals
from twisted.python import usage
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.internet.task import react
from twisted.internet.protocol import Protocol, Factory
from . import create
#from twisted.python import log; import sys; log.startLogging(sys.stderr)

class Options(usage.Options):
    pass

class HelloProtocol(Protocol):
    def connectionMade(self):
        print("connectionMade")
        self.transport.write(b"hello you\n")
    def dataReceived(self, data):
        print("data:", data)

@inlineCallbacks
def open(reactor, options):
    w = create("newcli", relay_url="ws://localhost:4000/v1", reactor=reactor)
    w.set_code("4-purple-sausages")
    (control_ep, client_ep, server_ep) = yield w.dilate()
    print("control_ep", control_ep)
    f = Factory()
    f.protocol = HelloProtocol
    control_ep.connect(f)
    d = Deferred()
    reactor.callLater(3.0, d.callback, None)
    yield d
    returnValue(0)


def run():
    options = Options()
    options.parseOptions()
    return react(open, (options,))

