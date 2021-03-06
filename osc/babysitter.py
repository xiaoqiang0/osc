# Copyright (C) 2008 Novell Inc.  All rights reserved.
# This program is free software; it may be used, copied, modified
# and distributed under the terms of the GNU General Public Licence,
# either version 2, or (at your option) any later version.

import errno
import os.path
import pdb
import sys
import signal
import traceback

from osc import oscerr
from oscsslexcp import NoSecureSSLError
from osc.util.cpio import CpioError
from osc.util.packagequery import PackageError

try:
    from M2Crypto.SSL.Checker import SSLVerificationError
    from M2Crypto.SSL import SSLError as SSLError
except:
    SSLError = None
    SSLVerificationError = None

try:
    # import as RPMError because the class "error" is too generic
    from rpm import error as RPMError
except:
    # if rpm-python isn't installed (we might be on a debian system):
    RPMError = None

from httplib import HTTPException, BadStatusLine
from urllib2 import URLError, HTTPError

# the good things are stolen from Matt Mackall's mercurial


def catchterm(*args):
    raise oscerr.SignalInterrupt

for name in 'SIGBREAK', 'SIGHUP', 'SIGTERM':
    num = getattr(signal, name, None)
    if num:
        signal.signal(num, catchterm)


def run(prg):
    try:
        try:
            if '--debugger' in sys.argv:
                pdb.set_trace()
            # here we actually run the program:
            return prg.main()
        except:
            # look for an option in the prg.options object and in the config
            # dict print stack trace, if desired
            if getattr(prg.options, 'traceback', None) or getattr(prg.conf, 'config', {}).get('traceback', None) or \
               getattr(prg.options, 'post_mortem', None) or getattr(prg.conf, 'config', {}).get('post_mortem', None):
                traceback.print_exc(file=sys.stderr)
                # we could use http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52215
            # enter the debugger, if desired
            if getattr(prg.options, 'post_mortem', None) or getattr(prg.conf, 'config', {}).get('post_mortem', None):
                if sys.stdout.isatty() and not hasattr(sys, 'ps1'):
                    pdb.post_mortem(sys.exc_info()[2])
                else:
                    print >>sys.stderr, 'sys.stdout is not a tty. Not jumping into pdb.'
            raise
    except oscerr.SignalInterrupt:
        print >>sys.stderr, 'killed!'
        return 1
    except KeyboardInterrupt:
        print >>sys.stderr, 'interrupted!'
        return 1
    except oscerr.UserAbort:
        print >>sys.stderr, 'aborted.'
        return 1
    except oscerr.APIError, e:
        print >>sys.stderr, 'BuildService API error:', e.msg
        return 1
    except oscerr.LinkExpandError, e:
        print >>sys.stderr, 'Link "%s/%s" cannot be expanded:\n' % (e.prj, e.pac), e.msg
        print >>sys.stderr, 'Use "osc repairlink" to fix merge conflicts.\n'
        return 1
    except oscerr.WorkingCopyWrongVersion, e:
        print >>sys.stderr, e
        return 1
    except oscerr.NoWorkingCopy, e:
        print >>sys.stderr, e
        if os.path.isdir('.git'):
            print >>sys.stderr, "Current directory looks like git."
        if os.path.isdir('.hg'):
            print >>sys.stderr, "Current directory looks like mercurial."
        if os.path.isdir('.svn'):
            print >>sys.stderr, "Current directory looks like svn."
        if os.path.isdir('CVS'):
            print >>sys.stderr, "Current directory looks like cvs."
        return 1
    except HTTPError, e:
        print >>sys.stderr, 'Server returned an error:', e
        if hasattr(e, 'osc_msg'):
            print >>sys.stderr, e.osc_msg

        try:
            body = e.read()
        except AttributeError:
            body = ''

        if getattr(prg.options, 'debug', None) or \
           getattr(prg.conf, 'config', {}).get('debug', None):
            print >>sys.stderr, e.hdrs
            print >>sys.stderr, body

        if e.code in [400, 403, 404, 500]:
            if '<summary>' in body:
                msg = body.split('<summary>')[1]
                msg = msg.split('</summary>')[0]
                print >>sys.stderr, msg
        return 1
    except BadStatusLine, e:
        print >>sys.stderr, 'Server returned an invalid response:', e
        print >>sys.stderr, e.line
        return 1
    except HTTPException, e:
        print >>sys.stderr, e
        return 1
    except URLError, e:
        print >>sys.stderr, 'Failed to reach a server:\n', e.reason
        return 1
    except IOError, e:
        # ignore broken pipe
        if e.errno != errno.EPIPE:
            raise
        return 1
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise
        print >>sys.stderr, e
        return 1
    except (oscerr.ConfigError, oscerr.NoConfigfile), e:
        print >>sys.stderr, e.msg
        return 1
    except oscerr.OscIOError, e:
        print >>sys.stderr, e.msg
        if getattr(prg.options, 'debug', None) or \
           getattr(prg.conf, 'config', {}).get('debug', None):
            print >>sys.stderr, e.e
        return 1
    except (oscerr.WrongOptions, oscerr.WrongArgs), e:
        print >>sys.stderr, e
        return 2
    except oscerr.ExtRuntimeError, e:
        print >>sys.stderr, e.file + ':', e.msg
        return 1
    except oscerr.WorkingCopyOutdated, e:
        print >>sys.stderr, e
        return 1
    except (oscerr.PackageExists, oscerr.PackageMissing, oscerr.WorkingCopyInconsistent), e:
        print >>sys.stderr, e.msg
        return 1
    except oscerr.PackageInternalError, e:
        print >>sys.stderr, 'a package internal error occured\n' \
            'please file a bug and attach your current package working copy ' \
            'and the following traceback to it:'
        print >>sys.stderr, e.msg
        traceback.print_exc(file=sys.stderr)
        return 1
    except oscerr.PackageError, e:
        print >>sys.stderr, e.msg
        return 1
    except PackageError, e:
        print >>sys.stderr, '%s:' % e.fname, e.msg
        return 1
    except RPMError, e:
        print >>sys.stderr, e
        return 1
    except SSLError, e:
        print >>sys.stderr, "SSL Error:", e
        return 1
    except SSLVerificationError, e:
        print >>sys.stderr, "Certificate Verification Error:", e
        return 1
    except NoSecureSSLError, e:
        print >>sys.stderr, e
        return 1
    except CpioError, e:
        print >>sys.stderr, e
        return 1
    except oscerr.OscBaseError, e:
        print >>sys.stderr, '*** Error:', e
        return 1

# vim: sw=4 et
