from __future__ import print_function, unicode_literals
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
import urwid

APPID = u"lothar.com/wormhole/text-or-file-xfer"

def open_wormhole(args, reactor=reactor):
    return Opener(args, reactor).go()

class Opener(object):
    def __init__(self, args, reactor):
        self._args = args
        self._reactor = reactor

    @inlineCallbacks
    def go(self):
        #text = prompt("give me input: ")
        #print("text: ", text)
        yield None
        evl = urwid.TwistedEventLoop(manage_reactor=False)
        loop = urwid.MainLoop(self.toplevel, screen=self.screen,
                              event_loop=evl,
                              unhandled_input=self.mind.unhandled_key,
                              palette=self.palette)
        self.screen.loop = loop
        loop.run()

        print("go exiting")
        

