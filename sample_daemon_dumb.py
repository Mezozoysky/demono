# -*- coding: utf-8 -*-
"""
Sample dumb Demono-based Unix daemon which does nothing.
Module provides daemon's basic start/stop facilities.
Requires Click 6.x .

Usage: 'python3 sample_daemon_dumb.py <start|stop>'.
"""

import sys
import time
import signal
import click
from demono import Demono, signal_handler


class DumbDaemon(Demono):

    def run(self):
        while True:
            time.sleep(1)

    @staticmethod
    @signal_handler(signal.SIGTERM)
    def sig_term_handler(signum, frame):
        sys.stderr.write('Ouch! SIGTERM recived!\n' \
                         'signum: {}, frame: {}\n'.format(signum, frame));
        sys.exit(0)
        return


@click.group()
@click.pass_context
def ctl_cli(ctx):
    daemon = DumbDaemon(err='/home/mezozoy/tmp/CyberDaemon.stderr')
    ctx.obj['daemon'] = daemon


@click.command('start')
@click.pass_context
def start(ctx):
    daemon = ctx.obj['daemon']
    assert daemon is not None, 'daemon object should exist at that time'
    daemon.start()

ctl_cli.add_command(start)


@click.command('stop')
@click.pass_context
def stop(ctx):
    daemon = ctx.obj['daemon']
    assert daemon is not None, 'daemon object should exist at thet time'
    daemon.stop()

ctl_cli.add_command(stop)


@click.command('restart')
@click.pass_context
def restart(ctx):
    daemon = ctx.obj['daemon']
    assert daemon is not None, 'daemon object should exist at thet time'
    daemon.stop()
    daemon.start()

ctl_cli.add_command(restart)


if __name__ == "__main__":
    ctl_cli(obj={})
