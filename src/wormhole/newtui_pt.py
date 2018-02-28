from __future__ import print_function, unicode_literals
import os
import random
import asyncio
from binascii import b2a_hex
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet.task import react
from twisted.python import usage
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.controls import FormattedTextControl, UIControl, UIContent
from prompt_toolkit.widgets import VerticalLine, HorizontalLine, TextArea#, Frame
from prompt_toolkit.document import Document
from prompt_toolkit.filters import has_focus
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop, get_event_loop
from prompt_toolkit.styles import Style
from . import create

style = Style.from_dict({#"": "#ff0066", #for the input text
                         "prompt": "#ff0066", # for the prompt itself
                         "input-field": "bg:#000000 #ffffff",
                         })

class Starfield(object):
    NUM_STARS = 50
    STAR_SHAPES = "..+..++*+."
    _sizing = frozenset(["box"])
    starlines = None
    places = None

    def __init__(self, maxcol, maxrow):
        self.field = [[" "]*maxcol for i in range(maxrow)] # field[row][col]
        self.places = [(random.randrange(0, maxcol),
                        random.randrange(0, maxrow),
                        random.randrange(0, len(self.STAR_SHAPES)),
                        ) for i in range(self.NUM_STARS)]

    def twinkle(self):
        self.places = [(col, row, (shape+1)%len(self.STAR_SHAPES))
                       for (col, row, shape) in self.places]
        for (col, row, shape) in self.places:
            self.field[row][col] = self.STAR_SHAPES[shape:shape+1]

    def render(self):
        return "\n".join(["".join(row) for row in self.field]) + "\n"
    def render_lines(self):
        return ["".join(row) for row in self.field]

# this is a UIControl
class StarfieldControl(UIControl):
    def __init__(self):
        self.starfield = None
        self.width = None
        self.height = None

    def create_content(self, width, height):
        if (width, height) != (self.width, self.height):
            (self.width, self.height) = (width, height)
            self.starfield = Starfield(width, height)
        self.starfield.twinkle()
        #text = self.starfield.render()
        lines = self.starfield.render_lines()
        content = UIContent(get_line=lambda i: [("", lines[i]),],
                            line_count=len(lines),
                            show_cursor=False)
        return content

    def twinkle(self):
        if self.starfield:
            self.starfield.twinkle()

ALLOCATING, ENTERING = object(), object()

class TUI(object):
    def __init__(self, reactor, options):
        targetdir = os.getcwd() + os.sep
        homedir = os.path.expanduser("~")
        if targetdir.startswith(homedir):
            targetdir = "~/" + targetdir[len(homedir+os.sep):]
        if len(targetdir) > 40:
            targetdir = "... " + targetdir[-40:]
        self.targetdir = targetdir

        self.active_transfers = []
        self.active = TextArea(text="(no active transfers)",
                               read_only=True,
                               focusable=False)
        self.wormhole = create("newcli", relay_url="ws://localhost:4000/v1",
                               reactor=reactor)
        self._welcome = "not received"
        self._verifier = "not received"
        self.wormhole.get_welcome().addCallback(self._got_welcome)
        self.wormhole.get_verifier().addCallback(self._got_verifier)
        if options["generate"]:
            self._code = ALLOCATING
            self.wormhole.allocate_code()
        else:
            self._code = ENTERING
        self.wormhole.get_code().addCallback(self._got_code)
        self.input_field = TextArea(height=1, prompt=self.get_prompt,
                                    style="class:input-field")
        left = HSplit([
            Window(FormattedTextControl(self.get_instructions),
                   dont_extend_height=True),
            Window(height=1, char="="),
            self.active,
            HorizontalLine(),
            self.input_field,
            ])
        self.starfield_control = StarfieldControl()
        body = VSplit([
            left,
            VerticalLine(),
            Window(self.starfield_control),
            ])

        kb = KeyBindings()
        kb.add("c-q")(self.quit)
        kb.add("enter", filter=has_focus(self.input_field))(self.enter)

        app = Application(
            full_screen=True,
            layout=Layout(body),
            key_bindings=kb,
            style=style,
            )
        self.please_show = False
        @kb.add("c-w")
        def _toggle(event):
            self.please_show = not self.please_show
            app.invalidate()
        self.app = app

    def start_animation(self):
        self._animation_frame_rate = 0.5
        loop = asyncio.get_event_loop()
        self._animation_handle = loop.call_later(self._animation_frame_rate,
                                                 self._do_animation_loop)

    def stop_animation(self):
        self._animation_handle.cancel()
        self._animation_handle = None

    def _do_animation_loop(self):
        self._animation_handle = None
        loop = asyncio.get_event_loop()
        self._do_animation()
        self._animation_handle = loop.call_later(self._animation_frame_rate,
                                                 self._do_animation_loop)

    def _do_animation(self):
        self.starfield_control.twinkle()
        self.app.invalidate()

    def get_instructions(self):
        lines = ["Control-Q: quit",
                 "",
                 "downloading into:",
                 self.targetdir,
                 ""
                 "welcome: {}".format(self._welcome),
                 "verifier: {}".format(self._verifier),
                 "",
                 ]
        if self._code is ALLOCATING:
            lines.append("allocating a code..")
        elif self._code is ENTERING:
            lines.append("please enter the wormhole code below")
        else:
            lines.append("wormhole code is:  {}".format(self._code))
        return "\n".join(lines)

    def get_prompt(self):
        if self._code is ENTERING:
            return "Code: "
        else:
            return "Send: "

    # keybinding handlers
    def quit(self, event):
        " quit app"
        event.app.set_result(4)

    def _start_send(self, filename):
        self.active_transfers.append("sending {} ..".format(filename))
        text = "\n".join(self.active_transfers)
        #active.buffer.document = Document(text=text, cursor_position=len(text))
        #active.buffer.text = text
        self.active.buffer.set_document(Document(text=text,
                                                 cursor_position=len(text)),
                                        bypass_readonly=True)

    def _got_code(self, code):
        self._code = code
        self.app.invalidate()

    def enter(self, event):
        if self._code is ENTERING:
            self._code = self.input_field.text
            self.wormhole.set_code(self._code)
        else:
            self._start_send(self.input_field.text)
        self.input_field.text = ""

    def _got_welcome(self, welcome):
        self._welcome = welcome
        self.app.invalidate()
    def _got_verifier(self, verifier):
        self._verifier = b2a_hex(verifier).decode("ascii")
        self.app.invalidate()

class Options(usage.Options):
    optFlags = [
        ("generate", "g", "Generate a code, instead of accepting one"),
        ]

@inlineCallbacks
def go(reactor, options):
    yield None
    # exceptions tend to get masked. Comment out use_asyncio_event_loop to
    # reveal them.
    use_asyncio_event_loop()
    t = TUI(reactor, options)
    t.start_animation()
    f = t.app.run_async()
    d = Deferred()
    f.add_done_callback(d.callback)
    yield d
    #get_event_loop().run_until_complete(f)
    returnValue(0)

def run():
    options = Options()
    options.parseOptions()
    loop = asyncio.get_event_loop()
    from twisted.internet.asyncioreactor import install
    install(loop) # we must install the same loop that prompt_toolkit will use
    # a bare install() would create a brand new loop, distinct from PT's

    # but then PT will find the loop itself, we don't need to pass it in

    return react(go, (options,))
    #open(None, options)

