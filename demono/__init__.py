# -*- coding: utf-8 -*-
"""
Module provides the base daemon class 'Demono', 'signal_handler' decorator and
a bit of utility functions.
"""

import sys
import os
import time
import atexit
import signal
from signal import signal as register_signal


def echo(message: str):
    """
    Convenience wrapper for sys.stdout.write, just prints message and newline.
    """
    sys.stdout.write('{}\n'.format(message))


def warn(message: str):
    """
    Convenience wrapper for sys.stderr.write,
    just prints 'WARN: ', message and newline.
    """
    sys.stderr.write('WARN: {}\n'.format(message))


def die(message, code=1):
    """
    Convenience wrapper for sys.stderr.write,
    prints 'FATAL:', message and newline, after that exits with code.
    Default exit code is 1.
    """
    sys.stderr.write('FATAL: {}\n'.format(message))
    sys.exit(code)


def signal_handler(signal_id):
    """
    Signal handler decorator attributed with signal number
    """
    def underlying_decorator(handler_func):
        def handler_func_wrapper(signum, frame):
            return handler_func(signum, frame)
        if not hasattr(signal_handler, 'registered'):
            signal_handler.registered = {}
        signal_handler.registered[signal_id] = handler_func_wrapper
        return handler_func_wrapper
    return underlying_decorator


class Demono:
    """
    Base daemon abstraction
    """

    # Kind of 'default' values for io streams' files
    _in = '/dev/null'
    _out = '/dev/null'
    _err = '/dev/null'

    def __init__(self, name=None, **kwargs):
        self._name = name \
            if name is not None \
            else self.__class__.__name__

        if kwargs is not None:
            if 'pid_file' in kwargs:
                self._pid_file = kwargs['pid_file']
            else:
                self._pid_file = '/var/run/{}.pid'.format(self._name)
            if 'in' in kwargs:
                self._in = kwargs['in']
            if 'out' in kwargs:
                self._out = kwargs['out']
            if 'err' in kwargs:
                self._err = kwargs['err']

    def run(self):
        assert False, \
            'You should subclass "Demono" class end override it\'s' \
            '"run" method, like this:\n' \
            '<< ----- Example start -----\n' \
            'from demono import Demono\n' \
            'import time\n\n' \
            'class MyDaemon(Demono):\n\n' \
            'def run(self):\n' \
            '    while True:\n' \
            '        time.sleep(1)\n\n' \
            '# your other code here\n' \
            '>> -----  Example end  -----\n'

    def start(self):
        """
        Daemonize process and 'run' the daemon
        """
        if os.path.exists(self._pid_file):
            die('Pidfile "{}" already exists. '
                'Considered daemon is running already'.format(self._pid_file))

        self._daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon process and clean up
        """

        if not os.path.exists(self._pid_file):
            die('Pidfile {} does not exist; '
                'Considered daemon is not running;\n'.format(self._pid_file))

        pid = None
        try:
            with open(self._pid_file, 'r') as f:
                pid = int(f.read().strip())
        except IOError as e:
            die('Error while reading pidfile "{}": {}'
                .format(self._pid_file, e))
        except ValueError as e:
            die('Error while parsing pid from pidfile "{}": {}'
                .format(self._pid_file, e))

        try:
            kill_count = 0
            while Demono._is_process_running(pid):
                os.kill(pid, signal.SIGTERM)
                kill_count += 1
                time.sleep(0.1)
        except OSError as e:
            if 'No such process' in str(e):
                # We here if daemon has terminated just after last
                # "_is process_running()" call and before the next "kill".
                # We OK with it.
                pass
            else:
                die('Failed to stop the daemon: {}'.format(e))
                # Note: pidfile is not removed in this case
        finally:
            if kill_count > 1:
                echo('Kill try count: {}'.format(kill_count))

        if os.path.exists(self._pid_file): # on the case of fire
            self._remove_pid_file()

    def _daemonize(self):
        # Daemonize execution using double-fork technique to safely decouple
        # from the ctl process

        # try first fork
        pid = None
        try:
            pid = os.fork()
        except OSError as e:
            die('Error while daemonizing (first fork): {}\n'.format(e))

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
        # We are in the second forked process now -- the daemon one.
        #

        # Signals registration.
        if hasattr(signal_handler, 'registered'):
            for sig, handler in signal_handler.registered.items():
                register_signal(sig, handler)
        else:
            warn('No signal handlers registered!')

        self._place_pid_file()

        echo('Daemonized')
        # echo('REGISTERED: {}'.format(signal_handler.registered
        #                                if hasattr(signal_handler, 'registered')
        #                                else None))

        # Flush std output streams.
        sys.stdout.flush()
        sys.stderr.flush()

        # Redirect streams.
        # Note: dont use 'with .. as' syntax, files shouldnt be closed till the
        # bloody end of daemon execution.
        try:
            in_ = open(self._in, 'r')
            os.dup2(in_.fileno(), sys.stdin.fileno())
            out = open(self._out, 'a+')
            os.dup2(out.fileno(), sys.stdout.fileno())
            # Err stream redirection should go as the last one,
            # otherwise the next die (on OSError) will happen quietly.
            err = open(self._err, 'a+')
            os.dup2(err.fileno(), sys.stderr.fileno())
        except OSError as e:
            die('Failed to redirect daemon\'s io streams: {}'.format(e))

    def _remove_pid_file(self):
        """Remove the pid_file from fs"""
        try:
            os.remove(self._pid_file)
        except FileNotFoundError as e:
            print('Error while removing pid file: "{}"'.format(e.args))

    def _place_pid_file(self):
        """
        Write process' pid into pid_file and
        register _remove_pid_file at process' exit
        """
        pid = str(os.getpid())
        with open(self._pid_file, 'w+') as f:
            f.write("{}\n".format(pid))
        atexit.register(self._remove_pid_file)

    @staticmethod
    def _is_process_running(pid):
        """Check if process specified by pid is running"""
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

