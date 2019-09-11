# no unicode_literals
# Find all of our ip addresses. From tahoe's src/allmydata/util/iputil.py

import errno
import os
import re
import subprocess
from sys import platform

from twisted.python.procutils import which

# Wow, I'm really amazed at home much mileage we've gotten out of calling
# the external route.exe program on windows...  It appears to work on all
# versions so far.  Still, the real system calls would much be preferred...
# ... thus wrote Greg Smith in time immemorial...
_win32_re = re.compile(
    (r'^\s*\d+\.\d+\.\d+\.\d+\s.+\s'
     r'(?P<address>\d+\.\d+\.\d+\.\d+)\s+(?P<metric>\d+)\s*$'),
    flags=re.M | re.I | re.S)
_win32_commands = (('route.exe', ('print', ), _win32_re, None), )

# These work in most Unices.
_addr_re = re.compile(
    r'^\s*inet [a-zA-Z]*:?(?P<address>\d+\.\d+\.\d+\.\d+)[\s/].+$',
    flags=re.M | re.I | re.S)
# macOS ifconfig (link): inet6 fe80::49b:d8e4:8af8:30e%en0 prefixlen 64 secured scopeid 0x8
# linux ip (link): inet6 fe80::ec4:7aff:fe46:a6cc/64 scope link
# linux ip (global): inet6 2600:3c00::f03c:91ff:fe62:b5b5/64 scope global dynamic mngtmpaddr noprefixroute
# linux ifconfig (global): inet6 2600:3c00::f03c:91ff:fe62:b5b5  prefixlen 64  scopeid 0x0<global>

_addr6_re = re.compile(
    r'^\s*inet6 (?P<address>[0-9a-f:]+)[\s/%].+global.*$',
    flags=re.M | re.I | re.S)

_unix_commands = (
    ('/bin/ip', ('addr', ), _addr_re, _addr6_re),
    ('/sbin/ip', ('addr', ), _addr_re, _addr6_re),
    ('/sbin/ifconfig', ('-a', ), _addr_re, _addr6_re),
    ('/usr/sbin/ifconfig', ('-a', ), _addr_re, _addr6_re),
    ('/usr/etc/ifconfig', ('-a', ), _addr_re, _addr6_re),
    ('ifconfig', ('-a', ), _addr_re, _addr6_re),
    ('/sbin/ifconfig', (), _addr_re, _addr6_re),
)


def find_addresses():
    # originally by Greg Smith, hacked by Zooko and then Daira

    # We don't reach here for cygwin.
    if platform == 'win32':
        commands = _win32_commands
    else:
        commands = _unix_commands

    for (pathtotool, args, v4regex, v6regex) in commands:
        # If pathtotool is a fully qualified path then we just try that.
        # If it is merely an executable name then we use Twisted's
        # "which()" utility and try each executable in turn until one
        # gives us something that resembles a dotted-quad IPv4 address.

        if os.path.isabs(pathtotool):
            exes_to_try = [pathtotool]
        else:
            exes_to_try = which(pathtotool)

        for exe in exes_to_try:
            try:
                addresses = _query(exe, args, v4regex, v6regex)
            except Exception:
                addresses = []
            if addresses:
                return addresses

    return ["127.0.0.1"]


def _query(path, args, v4regex, v6regex):
    env = {'LANG': 'en_US.UTF-8'}
    trial = 0
    while True:
        trial += 1
        try:
            p = subprocess.Popen(
                [path] + list(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                universal_newlines=True)
            (output, err) = p.communicate()
            break
        except OSError as e:
            if e.errno == errno.EINTR and trial < 5:
                continue
            raise

    addresses = []
    outputsplit = output.split('\n')
    for outline in outputsplit:
        m = v4regex.match(outline)
        if m:
            addr = m.group('address')
            if addr not in addresses:
                addresses.append(addr)
        if v6regex:
            m = v6regex.match(outline)
            if m:
                addr = m.group('address')
                if addr not in addresses:
                    addresses.append(addr)

    return addresses
