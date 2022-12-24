from __future__ import print_function

import hashlib
import os
import sys
import json
import itertools

import stat
import tempfile
import zipfile

import six
from humanize import naturalsize
from tqdm import tqdm
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.protocols import basic
from twisted.internet.endpoints import serverFromString, clientFromString
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.process import ProcessWriter, ProcessReader
from twisted.python import log
from twisted.python.failure import Failure
from wormhole import __version__, create

from ..errors import TransferError, UnsendableFileError
from ..transit import TransitSender
from ..util import bytes_to_dict, bytes_to_hexstr, dict_to_bytes
from .welcome import handle_welcome

APPID = u"lothar.com/wormhole/forward"
VERIFY_TIMER = float(os.environ.get("_MAGIC_WORMHOLE_TEST_VERIFY_TIMER", 1.0))


@inlineCallbacks
def forward(args, reactor=reactor):
    """
    I implement 'wormhole forward'.
    """
    assert isinstance(args.relay_url, type(u""))
    if args.tor:
        from ..tor_manager import get_tor
        tor = yield get_tor(
            reactor,
            args.launch_tor,
            args.tor_control_port,
            timing=args.timing,
        )
    else:
        tor = None

    w = create(
        args.appid or APPID,
        args.relay_url,
        reactor,
        tor=tor,
        timing=args.timing,
        _enable_dilate=True,
    )
    if args.debug_state:
        w.debug_set_trace("send", which=" ".join(args.debug_state), file=args.stdout)

    try:
        # if we succeed, we should close and return the w.close results
        # (which might be an error)
        res = yield _forward_loop(args, w)
        yield w.close()  # wait for ack
        returnValue(res)

    except Exception:
        # if we raise an error, we should close and then return the original
        # error (the close might give us an error, but it isn't as important
        # as the original one)
        try:
            yield w.close()  # might be an error too
        except Exception:
            pass
        f = Failure()
        returnValue(f)


@inlineCallbacks
def _forward_loop(args, w):
    """
    Run the main loop of the forward:
       - perform setup (version stuff etc)
       - wait for commands (as single-line JSON messages) on stdin
       - write results to stdout (as single-line JSON messages)
       - service subchannels
    """

    welcome = yield w.get_welcome()
    print(
        json.dumps({
            "welcome": welcome
        })
    )

    if args.code:
        w.set_code(args.code)
    else:
        w.allocate_code(args.code_length)

    code = yield w.get_code()
    print(
        json.dumps({
            "kind": "wormhole-code",
            "code": code,
        })
    )

    control_ep, connect_ep, listen_ep = w.dilate()
    _next_id = itertools.count(1, 1)

    def create_subchannel_id():
        return next(_next_id)

    class SubchannelMapper:
        id_to_incoming = dict()

        def subchannel_opened(self, incoming):
            i = create_subchannel_id()
            self.id_to_incoming[i] = incoming
            return i

    mapper = SubchannelMapper()

    class Forwarder(Protocol):
        def connectinoMade(self):
            print("fwd conn")
        def dataReceived(self, data):
            print("fwd {} {}".format(len(data), self.local.transport))
            self.local.transport.write(data)
            print(data)


    class LocalServer(Protocol):
        """
        """

        def connectionMade(self):
            print("local connection")
            print(self.factory)
            print(self.factory.endpoint)
            self.queue = []
            self.remote = None

            def got_proto(proto):
                print("PROTO", proto)
                proto.local = self
                self.remote = proto
                self._maybe_drain_queue()
            d = connect_ep(Factory.forProtocol(Forwarder))
            d.addBoth(got_proto)
            return d

        def _maybe_drain_queue(self):
            while self.queue:
                msg = self.queue.pop(0)
                self.remote.transport.write(msg)
                print("wrote", len(msg))
                print(msg)

        def connectionLost(self, reason):
            print("local connection lost")

        def dataReceived(self, data):
            print("local {}b".format(len(data)))
            if self.remote is None:
                print("queue", len(data))
                self.queue.append(data)
            else:
                self.remote.transport.write(data)
                print("wrote", len(data))
                print(data)


    class Incoming(Protocol):
        """
        """

        def connectionMade(self):
            print("incoming connection")
            # XXX first message should tell us where to connect, locally
            # (want some kind of opt-in on this side, probably)

        def connectionLost(self, reason):
            print("incoming connection lost")

        def dataReceived(self, data):
            print("incoming {}b".format(len(data)))


    class Outgoing(Protocol):
        """
        """
        def connectionMade(self):
            print("outgoing conn")

        def dataReceived(self, data):
            print(f"out_record: {data}")

    listen_ep.listen(Factory.forProtocol(Incoming))

    yield w.get_unverified_key()
    verifier_bytes = yield w.get_verifier()  # might WrongPasswordError

    if args.verify:
        raise NotImplementedError()

    # arrange to read incoming commands from stdin
    from twisted.internet.stdio import StandardIO
    from twisted.protocols.basic import LineReceiver

    @inlineCallbacks
    def _local_to_remote_forward(cmd):
        """
        Listen locally, and for each local connection create an Outgoing
        subchannel which will connect on the other end.
        """
        print("local forward", cmd)
        ep = serverFromString(reactor, cmd["endpoint"])
        print("ep", ep)
        factory = Factory.forProtocol(LocalServer)
        factory.endpoint = clientFromString(reactor, cmd["local-endpoint"])
        proto = yield ep.listen(factory)
        print(f"PROTO: {proto}")
        ##proto.transport.write(b'{"kind": "dummy"}\n')

    def process_command(cmd):
        print("cmd", cmd)
        if "kind" not in cmd:
            raise ValueError("no 'kind' in command")

        return {
            # listens locally, conencts to other side
            "local": _local_to_remote_forward,

            # asks the other side to listen, connects to us
            # "remote": _remote_to_local_forward,
        }[cmd["kind"]](cmd)

    class CommandDispatch(LineReceiver):
        delimiter = b"\n"
        def connectionMade(self):
            print(json.dumps({
                "kind": "connected",
            }))

        def lineReceived(self, line):
            try:
                cmd = json.loads(line)
                d = process_command(cmd)
                print("ZZZ", d)
                d.addErrback(print)
                return d
            except Exception as e:
                print(f"{line.strip()}: failed: {e}")


    x = StandardIO(CommandDispatch())
    yield Deferred()