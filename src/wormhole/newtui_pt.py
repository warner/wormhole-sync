from __future__ import print_function, unicode_literals
import os
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import react
from twisted.python import usage
from prompt_toolkit import prompt
#from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.application import Application
#from prompt_toolkit.shortcuts import create_eventloop
#from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.layout import FloatContainer, Float, ConditionalContainer
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import VerticalLine, HorizontalLine, TextArea, Frame
from prompt_toolkit.document import Document
from prompt_toolkit.filters import has_focus
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop, get_event_loop
import asyncio

@inlineCallbacks
def open(reactor, options, loop):
    yield None
    use_asyncio_event_loop()
    from prompt_toolkit.styles import Style
    style = Style.from_dict({#"": "#ff0066", #for the input text
                             "prompt": "#ff0066", # for the prompt itself
                             "input-field": "bg:#000000 #ffffff",
                             })
    def get_rprompt():
        return "<filename>"
    def bottom_toolbar():
        return [("class:bottom-toolbar", " bottom-side toolbar text")]
    #text = prompt("give me input: ", style=style,
    #              rprompt=get_rprompt, bottom_toolbar=bottom_toolbar)
    #print("text: ", text)
    print_formatted_text(HTML("<b>bold hello</b>"))
    print_formatted_text(HTML("<u>underlined hello</u>"))
    #loop = create_eventloop()
    #manager = KeyBindingManager()
    #registry = manager.registry
    #left = "welcome to the left\npanel\n"
    targetdir = os.getcwd() + os.sep
    homedir = os.path.expanduser("~")
    if targetdir.startswith(homedir):
        targetdir = "~/" + targetdir[len(homedir+os.sep):]
    if len(targetdir) > 40:
        targetdir = "... " + targetdir[-40:]
    instructions = "Control-Q: quit\n\ndownloading into:\n{}\n".format(targetdir)
    active_transfers = []
    active = TextArea(text="(no active transfers)",
                      read_only=True,
                      focusable=False)
    input_field = TextArea(height=1, prompt="Send: ", style="class:input-field")
    left = HSplit([
        Window(FormattedTextControl(instructions), dont_extend_height=True),
        Window(height=1, char="="),
        #Window(FormattedTextControl(active)),
        active,
        #Window(height=1, char="-"),
        HorizontalLine(),
        input_field,
        ])
    right = "imagine stars"
    body = VSplit([
        left,
        #Window(width=1, char="|"),
        VerticalLine(),
        Window(FormattedTextControl(right)),
        ])

    from prompt_toolkit.filters import Condition
    please_show = [True]
    def show_codeinput():
        return please_show[0]
    codeinput_frame = Frame(Window(FormattedTextControl("float"),
                                   width=20, height=4),
                            style="bg:#44ffff #ffffff")
    maybe_codeinput_frame = ConditionalContainer(codeinput_frame,
                                                 filter=Condition(show_codeinput))
    codeinput = Float(maybe_codeinput_frame,
                      left=10, top=5,
                      )

    screen = FloatContainer(content=body,
                            floats=[codeinput],
                            modal=True,
                            z_index=1)
    kb = KeyBindings()
    @kb.add("c-q")
    def _quit(event):
        " quit app"
        event.app.set_result(4)
    def _start_send(filename):
        active_transfers.append("sending {} ..".format(filename))
        text = "\n".join(active_transfers)
        #active.buffer.document = Document(text=text, cursor_position=len(text))
        #active.buffer.text = text
        active.buffer.set_document(Document(text=text,
                                            cursor_position=len(text)),
                                   bypass_readonly=True)
    @kb.add("enter", filter=has_focus(input_field))
    def _send(event):
        _start_send(input_field.text)
        input_field.text = ""

    app = Application(
        full_screen=True,
        #layout=Layout(body),
        layout=Layout(screen),
        key_bindings=kb,
        style=style,
        )
    @kb.add("c-w")
    def _toggle(event):
        please_show[0] = not please_show[0]
        app.invalidate()

    loop = get_event_loop()
    f = app.run_async()

    def _fire():
        _start_send("timer.txt")
    reactor.callLater(2.0, _fire)
    #print("calling cli.run()")
    x = loop.run_until_complete(f)
    print("cli.run() exited", x)
    print("reactor is", reactor)
    returnValue(0)

class Options(usage.Options):
    pass

def run():
    loop = asyncio.get_event_loop()
    from twisted.internet.asyncioreactor import install
    install(loop) # we must install the same loop that prompt_toolkit will use
    # a bare install() would create a brand new loop, distinct from PT's
    options = Options()
    options.parseOptions()
    return react(open, (options, loop))
    #open(None, options)

