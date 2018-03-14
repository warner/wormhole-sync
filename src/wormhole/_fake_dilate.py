from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet.endpoints import clientFromString, serverFromString
from twisted.internet.interfaces import IStreamClientEndpoint
from twisted.internet.protocol import Protocol, Factory
from zope.interface import implementer

LEADER, FOLLOWER = object(), object()


@implementer(IStreamClientEndpoint)
class ControlEndpoint(object):
    def __init__(self):
        self._cp = Deferred()

    def got_connection(self, control_protocol):
        self._cp.callback(control_protocol)

    @inlineCallbacks
    def connect(self, protocolFactory):
        # return Deferred that fires with IProtocol or Failure(ConnectError)
        cp = yield self._cp
        p = protocolFactory.buildProtocol("fake address")
        p.makeConnection(cp.transport)
        cp.glue(p)
        returnValue(p)

class ControlProtocolListener(Protocol):
    def __init__(self, d):
        self._d = d
        self._other = None
    def connectionMade(self):
        self._d.callback(self)
    def glue(self, other_protocol):
        print("glue", other_protocol)
        self._other = other_protocol
    def dataReceived(self, data):
        self._other.dataReceived(data)
    def connectionLost(self, reason=None):
        self._other.connectionLost()

class ControlProtocolListenerFactory(Factory):
    def __init__(self):
        self._d = Deferred()
    def on_first_connection(self):
        return self._d
    def buildProtocol(self, addr):
        p = ControlProtocolListener(self._d)
        p.factory = self
        return p

@inlineCallbacks
def start_dilation(w, reactor):
    res = yield w._get_wormhole_versions_and_sides()
    (our_side, their_side, their_wormhole_versions) = res
    my_role = LEADER if our_side > their_side else FOLLOWER
    # the control connection is defined to be an IStreamClientEndpoint on
    # both sides. In the fake dilation, we do this by connecting from
    # FOLLOWER to LEADER and then building a special endpoint around both
    # sides.
    if my_role == LEADER:
        print("LEADER")
        ep = serverFromString(reactor, "tcp:4002")
        f = ControlProtocolListenerFactory()
        #yield ep.listen(f)
        ep.listen(f) # returns Deferred, but we ignore it
        control_ep = ControlEndpoint()
        f.on_first_connection().addCallback(control_ep.got_connection)
        listen_ep = serverFromString(reactor, "tcp:4003")
        connect_ep = clientFromString(reactor, "tcp:127.0.0.1:4004")
    else:
        print("FOLLOWER")
        control_ep = clientFromString(reactor, "tcp:127.0.0.1:4002")
        listen_ep = serverFromString(reactor, "tcp:4004")
        connect_ep = clientFromString(reactor, "tcp:127.0.0.1:4003")

    endpoints = (control_ep, connect_ep, listen_ep)
    returnValue(endpoints)


