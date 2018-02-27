from __future__ import print_function, unicode_literals
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from prompt_toolkit import prompt
from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.application import Application
from prompt_toolkit.shortcuts import create_eventloop
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.keys import Keys

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
        loop = create_eventloop()
        manager = KeyBindingManager()
        registry = manager.registry
        application = Application(key_bindings_registry=registry,
                                  use_alternate_screen=True,
                                  )
        @registry.add_binding(Keys.ControlQ, eager=True)
        def exit_(event):
            event.cli.set_return_value(None)
        cli = CommandLineInterface(application=application, eventloop=loop)

        print("calling cli.run()")
        cli.run()
        print("cli.run() exited")
        

