from __future__ import print_function, unicode_literals
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import react
from twisted.python import usage
from prompt_toolkit import prompt
from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.application import Application
from prompt_toolkit.shortcuts import create_eventloop
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.keys import Keys

@inlineCallbacks
def open(reactor, options):
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
    returnValue(0)


class Options(usage.Options):
    pass

def run():
    options = Options()
    options.parseOptions()
    return react(open, (options,))

