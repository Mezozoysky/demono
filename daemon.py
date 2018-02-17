# -*- coding: utf-8 -*-
"""
Module provides some tools for tuna daemonisation
"""

import sys
import os
import time
import atexit
import signal
from signal import signal as register_signal


def signal_handler(signal_id):
    """
    Signal handler decorator
    """
    def underlying_decorator(handler_func):
        def handler_func_wrapper(signum, frame):
            return handler_func(signum, frame)
        register_signal(signal_id, handler_func_wrapper)
        return handler_func_wrapper
    return underlying_decorator


class Daemon:
    """
    Daemon desc
    """

    _pid_file = None
    _stdin = None
    _stdout = None
    _stderr = None

    def __init__(self, pidfile, **kwargs):
        self._pid_file = pidfile
        if kwargs is not None:
            self._stdin = kwargs['stdin']
            self._stdout = kwargs['stdout']
            self._stderr = kwargs['stderr']

    def run(self):
        assert False, \
            'You should subclass "Daemon" class end override it\'s' \
            '"run" method, like this:\n' \
            '<< ----- Example start -----\n' \
            'from da.daemon import Daemon\n' \
            'import time\n\n' \
            'class MyDaemon(Daemon):\n\n' \
            'def run(self):\n' \
            '    while True:\n' \
            '        time.sleep(1)\n\n' \
            '# your other code here\n' \
            '>> -----  Example end  -----\n'

    def start(self):
        """
        Daemonize execution and run into 'run' method
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = open(self._pid_file, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = 'pidfile {} already exist. '\
                      'Daemon already running?\n'
            sys.stderr.write(message.format(self._pid_file))
            sys.exit(1)

        # Start the daemon
        self._daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon process and clean up
        """

        if not os.path.exists(self._pid_file):
            sys.stderr.write(
                'Pidfile {} does not exist; '
                'Considered daemon is not running;\n'.format(self._pid_file))
            sys.stderr.write('Stopping the daemon is failed')
            exit(1)

        # Get the pid from the pidfile
        pid = None
        try:
            with open(self._pid_file, 'r') as f:
                pid = int(f.read().strip())
        except IOError as e:
            sys.stderr.write(
                'Error while reading pid from pidfile "{}": {}'
                .format(self._pid_file, e))
            sys.stderr.write('Stopping the daemon is failed\n;')
            exit(1)

        try:
            cnt = 0
            while Daemon._is_process_running(pid):
                os.kill(pid, signal.SIGTERM)
                cnt += 1
                time.sleep(0.1)
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            if 'No such process' in str(e):
                # We here if daemon has terminated just after last
                # "_is process_running()" call and before the next "kill".
                # We OK with it.
                pass
            else:
                sys.stderr.write('{}\n'.format(e))
                sys.stderr.write('Stopping the daemon if failed\n')
                #Note: pidfile is not removed in this case
                sys.exit(1)
        finally:
            print('Kill try count: {}'.format(cnt))

        if os.path.exists(self._pid_file):
            self._remove_pid_file()

    def _daemonize(self):
        # Daemonize execution using double-fork technique to safely decouple
        # from the ctl process

        # try first fork
        pid = None
        try:
            pid = os.fork()
        except OSError as e:
            sys.stderr.write(
                'Error while daemonizing (first fork): {}\n'.format(e))
            sys.exit(1)

        if pid > 0:  # we are in the ctl process now
            sys.exit(0)  # exit the ctl process
            return

        #
        # we are in the first forked process now
        #

        os.setsid()
        os.chdir('/')
        os.umask(0)

        # try second fork
        pid = None
        try:
            pid = os.fork()
        except OSError as e:
            sys.stderr.write(
                'Error while daemonizing (second fork): {}\n'.format(e))
            sys.exit(1)

        if pid > 0:  # we are still in the first forked process
            # exit the first fork
            sys.exit(0)
            return

        #
        # we are in the second forked process now -- the daemon one
        #

        # TODO: signals registration should go here

        self._place_pid_file()

        sys.stdout.write('Daemonized\n')

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self._stdin, 'r')
        so = open(self._stdout, 'a+')
        se = open(self._stderr, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

    def _remove_pid_file(self):
        try:
            os.remove(self._pid_file)
        except FileNotFoundError as e:
            print('Error while removing pid file: "{}"'.format(e.args))

    def _place_pid_file(self):
        pid = str(os.getpid())
        with open(self._pid_file, 'w+') as f:
            f.write("{}\n".format(pid))
        atexit.register(self._remove_pid_file)

    @staticmethod
    def _is_process_running(pid):
        """Check if process is running by pid"""
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True
