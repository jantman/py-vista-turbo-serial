#!/usr/bin/env python
"""
The latest version of this package is available at:
<http://github.com/jantman/py-vista-turbo-serial>

##################################################################################
Copyright 2018 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the “Software”), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

##################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/py-vista-turbo-serial> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
##################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
##################################################################################
"""

import sys
import os
import argparse
import logging
from typing import List, Optional
import threading
from time import sleep
from datetime import datetime

from py_vista_turbo_serial.communicator import Communicator
from py_vista_turbo_serial.messages import (
    MessagePacket, ArmingStatusRequest, ZoneStatusRequest
)

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(levelname)s] %(message)s"
)
logger: logging.Logger = logging.getLogger()


class MessageStore:

    def __init__(self):
        self._lock: threading.Lock = threading.Lock()
        self._messages: List[str] = []

    def add(self, msg: str):
        logger.debug('Enqueue: %s', msg)
        with self._lock:
            self._messages.append(msg)

    def get_all(self) -> List[str]:
        with self._lock:
            items, self._messages = self._messages, []
        return items


class PushoverNotifier(threading.Thread):

    def __init__(
        self, store: MessageStore, app_token: str, user_key: str,
        batch_seconds: int = 10, proxies: Optional[dict] = None,
        dry_run: bool = False
    ):
        super().__init__()
        self.daemon = True
        self._store: MessageStore = store
        self._app_token: str = app_token
        self._user_key: str = user_key
        self._batch_seconds: int = batch_seconds
        self._proxies: Optional[dict] = proxies
        self._dry_run: bool = dry_run

    def _do_notify_pushover(self, title, message, sound=None):
        """Build Pushover API request arguments and call _send_pushover"""
        d = {
            'data': {
                'token': self._app_token,
                'user': self._user_key,
                'title': title,
                'message': message,
                'retry': 300  # 5 minutes
            }
        }
        if sound is not None:
            d['data']['sound'] = sound
        logger.info('Sending Pushover notification: %s', d)
        if self._dry_run:
            logger.warning('DRY RUN - don\'t actually send')
            return
        for i in range(0, 2):
            try:
                self._send_pushover(d)
                return
            except Exception:
                logger.critical(
                    'send_pushover raised exception', exc_info=True
                )
        if self._proxies:
            logger.critical(
                'send_pushover failed on all attempts and proxies is empty!'
            )
            return
        # try sending through proxy
        d['proxies'] = self._proxies
        for i in range(0, 2):
            try:
                self._send_pushover(d)
                return
            except Exception:
                logger.critical(
                    'send_pushover via proxy raised exception', exc_info=True
                )

    def _send_pushover(self, params):
        """
        Send the actual Pushover notification.

        We do this directly with ``requests`` because python-pushover still
        doesn't have support for images or some other API options.
        """
        url = 'https://api.pushover.net/1/messages.json'
        if 'proxies' in params:
            logger.debug(
                'Sending Pushover notification with proxies=%s',
                params['proxies']
            )
        else:
            logger.debug('Sending Pushover notification')
        r = requests.post(url, timeout=5, **params)
        logger.debug(
            'Pushover POST response HTTP %s: %s', r.status_code, r.text
        )
        r.raise_for_status()
        if r.json()['status'] != 1:
            raise RuntimeError('Error response from Pushover: %s', r.text)
        logger.info('Pushover Notification Success: %s', r.text)

    def _handle_messages(self, messages: List[str]):
        title: str = f'{len(messages)} Alarm Messages'
        if len(messages) == 1:
            title = '1 Alarm Message'
        self._do_notify_pushover(title, '\n'.join(messages))

    def run(self):
        messages: List[str]
        while True:
            messages = self._store.get_all()
            if messages:
                logger.info('Got %d messages to handle', len(messages))
                self._handle_messages(messages)
            sleep(self._batch_seconds)


class PushoverAlarmNotifier:

    def __init__(
        self, port: str, batch_seconds: int = 10, dry_run: bool = False
    ):
        self.store: MessageStore = MessageStore()
        self.store.add(
            'PushoverAlarmNotifier initializing at ' +
            datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        )
        self.notifier: PushoverNotifier = PushoverNotifier(
            store=self.store,
            app_token=os.environ['PUSHOVER_APIKEY'],
            user_key=os.environ['PUSHOVER_USERKEY'],
            batch_seconds=batch_seconds,
            dry_run=dry_run
        )
        self.notifier.start()
        self.panel: Communicator = Communicator(port=port)

    def run(self):
        self.store.add(
            'PushoverAlarmNotifier starting run loop at ' +
            datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        )
        self.panel.send_message(ArmingStatusRequest.generate())
        self.panel.send_message(ZoneStatusRequest.generate())
        message: MessagePacket
        dt: str
        for message in self.panel.communicate():
            dt = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            """
            if isinstance(message, ArmingStatusReport):
                raise NotImplementedError()
            elif isinstance(message, ZoneStatusReport):
                raise NotImplementedError()
            else:
                self.store.add(str(message) + ' (' + dt + ')')
            """
            self.store.add(str(message) + ' (' + dt + ')')


def parse_args(argv):
    p = argparse.ArgumentParser(description='Alarm state Pushover notifier')
    p.add_argument(
        '-v', '--verbose', dest='verbose', action='store_true',
        default=False, help='verbose output'
    )
    p.add_argument(
        '-s', '--seconds', dest='seconds', action='store',
        type=int, default=10,
        help='How many seconds to wait before sending batches of messages '
             'to Pushover; default: 10'
    )
    p.add_argument(
        '-d', '--dry-run', dest='dry_run', action='store_true',
        default=False, help='dry run - don\'t actually send pushover'
    )
    p.add_argument(
        'PORT', action='store', type=str, default='/dev/ttyUSB0',
        help='Serial port to connect to (default: /dev/ttyUSB0)'
    )
    args = p.parse_args(argv)
    return args


def set_log_info(l: logging.Logger):
    """set logger level to INFO"""
    set_log_level_format(
        l,
        logging.INFO,
        '%(asctime)s %(levelname)s:%(name)s:%(message)s'
    )


def set_log_debug(l: logging.Logger):
    """set logger level to DEBUG, and debug-level output format"""
    set_log_level_format(
        l,
        logging.DEBUG,
        "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - "
        "%(name)s.%(funcName)s() ] %(message)s"
    )


def set_log_level_format(lgr: logging.Logger, level: int, fmt: str):
    """Set logger level and format."""
    formatter = logging.Formatter(fmt=fmt)
    lgr.handlers[0].setFormatter(formatter)
    lgr.setLevel(level)


def main():
    args = parse_args(sys.argv[1:])

    # set logging level
    if args.verbose:
        set_log_debug(logger)
    else:
        set_log_info(logger)

    PushoverAlarmNotifier(
        args.PORT, batch_seconds=args.seconds, dry_run=args.dry_run
    ).run()


if __name__ == "__main__":
    main()
