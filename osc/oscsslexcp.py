#!/usr/bin/python

class NoSecureSSLError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

# vim: sw=4 et
