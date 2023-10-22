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

import logging
from typing import List, Generator

from serial import Serial

from py_vista_turbo_serial.messages import MessagePacket

logger = logging.getLogger(__name__)


class Communicator:
    """
    Class for handling communication with the alarm.
    """

    def __init__(self, port: str, timeout_sec: int = 1):
        self._port: str = port
        logger.debug('Opening serial connection on %s', port)
        self.serial: Serial = Serial(
            port, baudrate=9600, timeout=timeout_sec
        )  # default 8N1
        logger.debug('Serial is connected')
        self.outgoing: List[str] = []

    def __del__(self):
        logger.debug('Closing serial port')
        self.serial.close()
        logger.debug('Serial port closed')

    def send_message(self, msg: str):
        logger.debug('Enqueueing message: %s', msg)
        self.outgoing.append(msg)

    def communicate(self) -> Generator[MessagePacket, None, None]:
        logger.info('Entering communicate() loop')
        # at start, if we have a message to send, send it
        if self.outgoing:
            msg = self.outgoing.pop(0)
            logger.info('Sending message: %s', msg)
            self.serial.write((msg + '\r\n').encode('utf-8'))
        # this might be better with select(), but let's try this...
        while True:
            # @TODO handle exception on timeout
            line = self.serial.readline().decode().strip()
            logger.debug('Got line: %s', line)
            yield MessagePacket.parse(line)
            if self.outgoing:
                msg = self.outgoing.pop(0)
                logger.info('Sending message: %s', msg)
                self.serial.write(msg + '\r\n')
