"""
The latest version of this package is available at:
<http://github.com/jantman/py-vista-turbo-serial>

##################################################################################
Copyright 2023 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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

import pytest

from py_vista_turbo_serial.messages import (
    InvalidMessageLengthException, MessageChecksumException, MessagePacket,
    UnknownMessage, ArmAwayMessage, ArmHomeMessage, DisarmMessage,
    ArmingStatusRequest, ArmingStatusReport, PartitionState, ZoneStatusRequest,
    ZoneStatusReport, ZoneState, ZonePartitionRequest, ZonePartitionReport,
    SystemEventNotification
)
from py_vista_turbo_serial.events import FaultEvent


class TestZoneState:

    def test_closed(self):
        res = ZoneState(0)
        assert res.closed is True
        assert res.open is False
        assert res.trouble is False
        assert res.alarm is False
        assert res.bypassed is False
        assert str(res) == 'CLOSED'

    def test_open(self):
        res = ZoneState(1)
        assert res.closed is False
        assert res.open is True
        assert res.trouble is False
        assert res.alarm is False
        assert res.bypassed is False
        assert str(res) == 'OPEN'

    def test_trouble(self):
        res = ZoneState(2)
        assert res.closed is True
        assert res.open is False
        assert res.trouble is True
        assert res.alarm is False
        assert res.bypassed is False
        assert str(res) == 'CLOSED|TROUBLE'

    def test_alarm(self):
        res = ZoneState(4)
        assert res.closed is True
        assert res.open is False
        assert res.trouble is False
        assert res.alarm is True
        assert res.bypassed is False
        assert str(res) == 'CLOSED|ALARM'

    def test_bypassed(self):
        res = ZoneState(8)
        assert res.closed is True
        assert res.open is False
        assert res.trouble is False
        assert res.alarm is False
        assert res.bypassed is True
        assert str(res) == 'CLOSED|BYPASSED'

    def test_open_alarm_trouble(self):
        res = ZoneState(7)
        assert res.closed is False
        assert res.open is True
        assert res.trouble is True
        assert res.alarm is True
        assert res.bypassed is False
        assert str(res) == 'OPEN|TROUBLE|ALARM'

    def test_open_trouble_bypassed(self):
        res = ZoneState(0xb)
        assert res.closed is False
        assert res.open is True
        assert res.trouble is True
        assert res.alarm is False
        assert res.bypassed is True
        assert str(res) == 'OPEN|TROUBLE|BYPASSED'


class TestInvalidLength:

    def test_invalid_length(self):
        with pytest.raises(InvalidMessageLengthException) as exc:
            MessagePacket.parse('0Dah037898001F')
        assert isinstance(exc.value, InvalidMessageLengthException)
        assert exc.value.actual_len == 0x0E
        assert exc.value.expected_len == 0x0D


class TestCrcError:

    def test_invalid_length(self):
        with pytest.raises(MessageChecksumException) as exc:
            MessagePacket.parse('0Eah037898001E')
        assert isinstance(exc.value, MessageChecksumException)
        assert exc.value.actual_crc == '1F'
        assert exc.value.expected_crc == '1E'


class TestMessagePacket:

    def test_base_class_from_panel(self):
        res = MessagePacket.parse('0Eah037898001F')
        assert isinstance(res, MessagePacket)
        assert res.raw_message == '0Eah037898001F'
        assert res._data == '037898'
        assert res.from_panel is False

    def test_base_class_to_panel(self):
        res = MessagePacket.parse('0EAH037898005F')
        assert isinstance(res, MessagePacket)
        assert res.raw_message == '0EAH037898005F'
        assert res._data == '037898'
        assert res.from_panel is True

    def test_unknown_message(self):
        res = MessagePacket.parse('0Ezz03789800F4')
        assert isinstance(res, UnknownMessage)


class TestArmAway:

    def test_from_panel(self):
        res = MessagePacket.parse('0EAA0223450079')
        assert isinstance(res, ArmAwayMessage)
        assert res.from_panel is True
        assert res.user == 2
        assert res.user_code == '2345'

    def test_to_panel(self):
        res = MessagePacket.parse('0Eaa0223450039')
        assert isinstance(res, ArmAwayMessage)
        assert res.from_panel is False
        assert res.user == 2
        assert res.user_code == '2345'


class TestArmHome:

    def test_from_panel(self):
        res = MessagePacket.parse('0EAH0223450072')
        assert isinstance(res, ArmHomeMessage)
        assert res.from_panel is True
        assert res.user == 2
        assert res.user_code == '2345'

    def test_to_panel(self):
        res = MessagePacket.parse('0Eah0223450032')
        assert isinstance(res, ArmHomeMessage)
        assert res.from_panel is False
        assert res.user == 2
        assert res.user_code == '2345'


class TestDisarm:

    def test_from_panel(self):
        res = MessagePacket.parse('0EAD0223450076')
        assert isinstance(res, DisarmMessage)
        assert res.from_panel is True
        assert res.user == 2
        assert res.user_code == '2345'

    def test_to_panel(self):
        res = MessagePacket.parse('0Ead0223450036')
        assert isinstance(res, DisarmMessage)
        assert res.from_panel is False
        assert res.user == 2
        assert res.user_code == '2345'


class TestArmingStatusRequest:

    def test_to_panel(self):
        res = MessagePacket.parse('08as0064')
        assert isinstance(res, ArmingStatusRequest)
        assert res.from_panel is False

    def test_generate(self):
        assert ArmingStatusRequest.generate() == '08as0064'


class TestArmingStatusReport:

    def test_from_panel(self):
        res = MessagePacket.parse('10ASHHHHDDAA0081')
        assert isinstance(res, ArmingStatusReport)
        assert res.from_panel is True
        assert res.partition_state == {
            1: PartitionState.HOME,
            2: PartitionState.HOME,
            3: PartitionState.HOME,
            4: PartitionState.HOME,
            5: PartitionState.DISARMED,
            6: PartitionState.DISARMED,
            7: PartitionState.AWAY,
            8: PartitionState.AWAY,
        }


class TestZoneStatusRequest:

    def test_to_panel(self):
        res = MessagePacket.parse('08zs004B')
        assert isinstance(res, ZoneStatusRequest)
        assert res.from_panel is False

    def test_generate(self):
        assert ZoneStatusRequest.generate() == '08zs004B'


class TestZoneStatusReport:

    def test_from_panel(self):
        res = MessagePacket.parse(
            '68ZS1B00' + '0' * 92 + '0072'
        )
        assert isinstance(res, ZoneStatusReport)
        assert res.from_panel is True
        expected = {
            x: ZoneState(0) for x in range(1, 97)
        }
        expected[1] = ZoneState(1)
        expected[2] = ZoneState(11)
        assert res.zones == expected


class TestZonePartitionRequest:

    def test_to_panel(self):
        res = MessagePacket.parse('08zp004E')
        assert isinstance(res, ZonePartitionRequest)
        assert res.from_panel is False

    def test_generate(self):
        assert ZonePartitionRequest.generate() == '08zp004E'


class TestZonePartitionReport:

    def test_from_panel(self):
        res = MessagePacket.parse(
            '68ZP2085' + '0' * 92 + '0079'
        )
        assert isinstance(res, ZonePartitionReport)
        assert res.from_panel is True
        expected = {x: 0 for x in range(1, 97)}
        expected[1] = 2
        expected[3] = 8
        expected[4] = 5
        assert res.partitions == expected


class TestSystemEventNotification:

    def test_zone_14_open(self):
        res = MessagePacket.parse(
            '14NQ2B14231021020038'
        )
        assert isinstance(res, SystemEventNotification)
        assert res._event_type == 0x2b
        assert res.zone_or_user == 14
        assert res.minute == 23
        assert res.hour == 10
        assert res.day == 21
        assert res.month == 2
        assert isinstance(res.event_type, FaultEvent)
