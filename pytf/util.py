from __future__ import print_function
from sys import stdout, stderr

def outmsg(*message):
    print(*message, file=stdout)


def errmsg(*message):
    print(*message, file=stderr)
