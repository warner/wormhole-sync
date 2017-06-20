from __future__ import print_function, unicode_literals
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
import urwid

APPID = u"lothar.com/wormhole/text-or-file-xfer"

def open_wormhole(args, reactor=reactor):
    return Opener(args, reactor).go()
import random

class Starfield(urwid.Widget):
    NUM_STARS = 50
    STAR_SHAPES = b"..+..++*+."
    _sizing = frozenset(["box"])
    starlines = None
    places = None

    def init_starlines(self, maxcol, maxrow):
        self.starlines = [[b" "]*maxcol for i in range(maxrow)] # base[row][col]

    def place_stars(self, maxcol, maxrow):
        self.places = [(random.randrange(0, maxcol),
                        random.randrange(0, maxrow),
                        random.randrange(0, len(self.STAR_SHAPES)),
                        ) for i in range(self.NUM_STARS)]

    def render_stars(self):
        for (col, row, shape) in self.places:
            self.starlines[row][col] = self.STAR_SHAPES[shape]

    def twinkle_stars(self):
        self.places = [(col, row, (shape+1)%len(self.STAR_SHAPES))
                       for (col, row, shape) in self.places]
        self.render_stars()
        self._invalidate()

    def render(self, size, focus=False):
        (maxcol, maxrow) = size
        if self.starlines is None:
            self.init_starlines(maxcol, maxrow)
            self.place_stars(maxcol, maxrow)
        return urwid.TextCanvas([b"".join(whole_row)
                                 for whole_row in self.starlines],
                                maxcol=maxcol)

class Opener(object):
    def __init__(self, args, reactor):
        self._args = args
        self._reactor = reactor

    @inlineCallbacks
    def go(self):
        #text = prompt("give me input: ")
        #print("text: ", text)
        yield None

        stars = Starfield()
        txt = urwid.Text("Hello world")
        top_status = urwid.Text("top status")
        bottom_status = urwid.Text("bottom status")
        top = urwid.Frame(stars,
                          header=top_status,
                          footer=bottom_status,
                          )
        #top = urwid.Filler(pile, valign="top")
        def show_or_exit(key):
            if key.lower() == "q":
                raise urwid.ExitMainLoop()
            txt.set_text(repr(key))
        loop = urwid.MainLoop(top,
                              unhandled_input=show_or_exit)
        def animate(loop=None, user_data=None):
            #with open("/tmp/starbug", "a") as f:
            #    import time
            #    f.write("more {}\n".format(time.time()))
            stars.twinkle_stars()
            loop.set_alarm_in(0.3, animate)
        alarm = loop.set_alarm_in(0.2, animate)
        loop.run()

        if 0:
            evl = urwid.TwistedEventLoop(manage_reactor=False)
            loop = urwid.MainLoop(self.toplevel,
                                  #screen=self.screen,
                                  event_loop=evl,
                                  #unhandled_input=self.mind.unhandled_key,
                                  #palette=self.palette,
                                  )
            self.screen.loop = loop
            loop.run()

        print("go exiting")
        

