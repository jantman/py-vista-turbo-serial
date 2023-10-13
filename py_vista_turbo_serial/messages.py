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

from typing import Tuple, List, Dict
import logging
from string import ascii_uppercase
from enum import Enum
from functools import total_ordering

from py_vista_turbo_serial.events import SystemEvent

logger = logging.getLogger(__name__)


class PartitionState(Enum):

    HOME = 1
    DISARMED = 2
    AWAY = 3


@total_ordering
class ZoneState:

    def __init__(self, state: int):
        self._state_numeric: int = state
        self.closed: bool = state & 1 == 0
        self.open: bool = state & 1 == 1
        self.trouble: bool = state & 2 == 2
        self.alarm: bool = state & 4 == 4
        self.bypassed: bool = state & 8 == 8

    def __str__(self):
        values = [
            'CLOSED' if self.closed else None,
            'OPEN' if self.open else None,
            'TROUBLE' if self.trouble else None,
            'ALARM' if self.alarm else None,
            'BYPASSED' if self.bypassed else None,
        ]
        return '|'.join([x for x in values if x is not None])

    def __repr__(self):
        return f'<ZoneState({self._state_numeric})>'

    def __eq__(self, other):
        return self._state_numeric == other._state_numeric

    def __lt__(self, other):
        return self._state_numeric < other._state_numeric


class InvalidMessageException(Exception):

    def __init__(self, error: str, raw_message: str):
        super().__init__(error)
        self._raw_message: str = raw_message


class InvalidMessageLengthException(InvalidMessageException):

    def __init__(self, raw_message: str, expected_len: int, actual_len: int):
        super().__init__(
            f'Received message with length {actual_len} but expected '
            f'length of {expected_len}: {raw_message}',
            raw_message
        )
        self.expected_len: int = expected_len
        self.actual_len: int = actual_len


class MessageChecksumException(InvalidMessageException):

    def __init__(self, raw_message: str, expected_crc: str, actual_crc: str):
        super().__init__(
            f'Received message with CRC {actual_crc} but expected '
            f'CRC of {expected_crc}: {raw_message}',
            raw_message
        )
        self.expected_crc: str = expected_crc
        self.actual_crc: str = actual_crc


class MessagePacket:

    MSG_TYPES: List[str] = []

    MSG_SUBTYPES: List[str] = []

    def __init__(
        self, raw_message: str, data: str = '', from_panel: bool = True
    ):
        """
        raw_message cannot be an empty string and should be just one line
        without leading or trailing whitespace or terminator (CR/LF)
        """
        self.raw_message: str = raw_message
        self._data: str = data
        self.from_panel: bool = from_panel

    def __repr__(self):
        return f'<MessagePacket("{self.raw_message}")>'

    @classmethod
    def _parse_message(cls, raw_message: str) -> Tuple[str, str, str]:
        msglen: int = int(raw_message[0:2], 16)
        if len(raw_message) != msglen:
            raise InvalidMessageLengthException(
                raw_message, msglen, len(raw_message)
            )
        expected_crc: str = raw_message[-2:]
        # thanks to: https://stackoverflow.com/a/16824894
        crc: str = '%2X' % (
            -(sum(ord(c) for c in raw_message[:-2]) % 256) & 0xFF
        )
        if crc != expected_crc:
            raise MessageChecksumException(
                raw_message, expected_crc, crc
            )
        msgtype: str = raw_message[2]
        subtype: str = raw_message[3]
        data: str = raw_message[4:-4]
        return msgtype, subtype, data

    @classmethod
    def parse(cls, raw_message: str) -> 'MessagePacket':
        msgtype: str
        subtype: str
        data: str
        msgtype, subtype, data = cls._parse_message(raw_message)
        from_panel: bool = msgtype in ascii_uppercase
        for klass in cls.__subclasses__():
            if msgtype in klass.MSG_TYPES and subtype in klass.MSG_SUBTYPES:
                return klass(
                    raw_message=raw_message, data=data, from_panel=from_panel
                )
        return UnknownMessage(
            raw_message=raw_message, data=data, from_panel=from_panel,
            msg_type=msgtype, msg_subtype=subtype
        )

    @classmethod
    def generate(cls) -> str:
        raise NotImplementedError(
            f'ERROR: Message generation of type {cls.__name__} '
            'is not implemented.'
        )


class UnknownMessage(MessagePacket):

    def __init__(
        self, raw_message: str, data: str, from_panel: bool, msg_type: str,
        msg_subtype: str
    ):
        super().__init__(raw_message, data, from_panel)
        self.msg_type: str = msg_type
        self.msg_subtype: str = msg_subtype

    def __repr__(self):
        return (f'<UnknownMessage(type="{self.msg_type}" '
                f'subtype="{self.msg_subtype}" data="{self._data}")>')


class ArmAwayMessage(MessagePacket):

    MSG_TYPES: List[str] = ['A', 'a']

    MSG_SUBTYPES: List[str] = ['A', 'a']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)
        self.user: int = int(data[0:2], 16)
        self.user_code: str = data[2:]

    def __repr__(self):
        return (f'<ArmAwayMessage(user={self.user}, '
                f'user_code="{self.user_code}")>')


class ArmHomeMessage(MessagePacket):

    MSG_TYPES: List[str] = ['A', 'a']

    MSG_SUBTYPES: List[str] = ['H', 'h']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)
        self.user: int = int(data[0:2], 16)
        self.user_code: str = data[2:]

    def __repr__(self):
        return (f'<ArmHomeMessage(user={self.user}, '
                f'user_code="{self.user_code}")>')


class DisarmMessage(MessagePacket):

    MSG_TYPES: List[str] = ['A', 'a']

    MSG_SUBTYPES: List[str] = ['D', 'd']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)
        self.user: int = int(data[0:2], 16)
        self.user_code: str = data[2:]

    def __repr__(self):
        return (f'<DisarmMessage(user={self.user}, '
                f'user_code="{self.user_code}")>')


class ArmingStatusRequest(MessagePacket):

    MSG_TYPES: List[str] = ['a']

    MSG_SUBTYPES: List[str] = ['s']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)

    def __repr__(self):
        return f'<ArmingStatusRequest("{self.raw_message}")>'

    @classmethod
    def generate(cls) -> str:
        return '08as0064'


class ArmingStatusReport(MessagePacket):

    MSG_TYPES: List[str] = ['A']

    MSG_SUBTYPES: List[str] = ['S']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)
        self.partition_state: Dict[int, PartitionState] = {}
        for idx, val in enumerate(data):
            if val == 'H':
                self.partition_state[idx + 1] = PartitionState.HOME
            elif val == 'D':
                self.partition_state[idx + 1] = PartitionState.DISARMED
            elif val == 'A':
                self.partition_state[idx + 1] = PartitionState.AWAY
            else:
                raise InvalidMessageException(
                    f'Invalid partition state code "{val}" in Arming '
                    f'Status Report message with data: "{data}"',
                    raw_message
                )

    def __repr__(self):
        s = ', '.join([
            f'Zone{x}={self.partition_state[x].name}' for x in sorted(
                self.partition_state.keys()
            )
        ])
        return f'<ArmingStatusReport({s})>'


class ZoneStatusRequest(MessagePacket):

    MSG_TYPES: List[str] = ['z']

    MSG_SUBTYPES: List[str] = ['s']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)

    def __repr__(self):
        return f'<ZoneStatusRequest("{self.raw_message}")>'

    @classmethod
    def generate(cls) -> str:
        return '08zs004B'


class ZoneStatusReport(MessagePacket):

    MSG_TYPES: List[str] = ['Z']

    MSG_SUBTYPES: List[str] = ['S']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)
        self.zones: Dict[int, ZoneState] = {}
        for idx, val in enumerate(data):
            self.zones[idx + 1] = ZoneState(int(val, 16))

    def __repr__(self):
        s = '; '.join([
            f'Zone{x}={str(self.zones[x])}' for x in sorted(self.zones.keys())
        ])
        return f'<ZoneStatusReport({s})>'


class ZonePartitionRequest(MessagePacket):

    MSG_TYPES: List[str] = ['z']

    MSG_SUBTYPES: List[str] = ['p']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)

    def __repr__(self):
        return f'<ZonePartitionRequest("{self.raw_message}")>'

    @classmethod
    def generate(cls) -> str:
        return '08zp004E'


class ZonePartitionReport(MessagePacket):

    MSG_TYPES: List[str] = ['Z']

    MSG_SUBTYPES: List[str] = ['P']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)
        self.partitions: Dict[int, int] = {}
        for idx, val in enumerate(data):
            self.partitions[idx + 1] = int(val)

    def __repr__(self):
        s = '; '.join([
            f'Zone{x}={self.partitions[x]}'
            for x in sorted(self.partitions.keys())
        ])
        return f'<ZonePartitionReport({s})>'


class SystemEventNotification(MessagePacket):

    MSG_TYPES: List[str] = ['N']

    MSG_SUBTYPES: List[str] = ['Q']

    def __init__(self, raw_message: str, data: str, from_panel: bool):
        super().__init__(raw_message, data, from_panel)
        self._event_type: int = int(data[0:2], 16)
        self.zone_or_user: int = int(data[2:4])
        self.event_type: SystemEvent = SystemEvent.event_for_code(
            self._event_type, self.zone_or_user
        )
        self.minute: int = int(data[4:6])
        self.hour: int = int(data[6:8])
        self.day: int = int(data[8:10])
        self.month: int = int(data[10:12])

    def __repr__(self):
        return (f'<SystemEvent(Type={self.event_type.NAME} Zone/User='
                f'{self.zone_or_user} Time={self.minute}:{self.hour} '
                f'{self.month}/{self.day})>')
