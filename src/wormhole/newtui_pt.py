from __future__ import print_function, unicode_literals
import os
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import react
from twisted.python import usage
#from prompt_toolkit import prompt
#from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.application import Application
#from prompt_toolkit.shortcuts import create_eventloop
#from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.key_binding import KeyBindings
#from prompt_toolkit import print_formatted_text, HTML
#from prompt_toolkit.layout import FloatContainer, Float, ConditionalContainer
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.controls import FormattedTextControl, UIControl, UIContent
from prompt_toolkit.widgets import VerticalLine, HorizontalLine, TextArea#, Frame
from prompt_toolkit.document import Document
from prompt_toolkit.filters import has_focus
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop, get_event_loop
import asyncio
from prompt_toolkit.styles import Style
style = Style.from_dict({#"": "#ff0066", #for the input text
                         "prompt": "#ff0066", # for the prompt itself
                         "input-field": "bg:#000000 #ffffff",
                         })
import random

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


class TUI(object):
    def __init__(self, options):
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
        self.need_code = True
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
        return "Control-Q: quit\n\ndownloading into:\n{}\n".format(self.targetdir)
    def get_prompt(self):
        if self.need_code:
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

    def got_code(self, code):
        pass

    def enter(self, event):
        if self.need_code:
            self.got_code(self.input_field.text)
            self.need_code = False
        else:
            self._start_send(self.input_field.text)
        self.input_field.text = ""

class Options(usage.Options):
    pass

@inlineCallbacks
def go(reactor, options):
    yield None
    use_asyncio_event_loop()
    t = TUI(options)
    t.start_animation()
    f = t.app.run_async()
    get_event_loop().run_until_complete(f)
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

