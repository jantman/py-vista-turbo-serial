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

from typing import Union, Dict, Optional

EventTypes: type = Union['SystemEvent', 'UnknownEvent']


def subclasses_recursive(cls):
    direct = cls.__subclasses__()
    indirect = []
    for subclass in direct:
        indirect.extend(subclasses_recursive(subclass))
    return direct + indirect


class SystemEvent:

    NAME: str = 'Unknown Event'

    CODE: int = 0

    IS_ZONE: bool = True

    def __init__(self, zone_or_user: int, zone_or_user_name: Optional[str]):
        self.zone_or_user: int = zone_or_user
        self.zone_or_user_name: Optional[str] = zone_or_user_name

    def __repr__(self) -> str:
        if not self.IS_ZONE:
            return f'<{self.NAME}(user={self.zone_or_user})>'
        if self.zone_or_user_name is None:
            return f'<{self.NAME}(zone_num={self.zone_or_user})>'
        return (f'<{self.NAME}(zone={self.zone_or_user} '
                f'"{self.zone_or_user_name}")>')

    @classmethod
    def event_for_code(
        cls, event_code: int, zone_or_user: int, zones: Dict[int, str]
    ) -> EventTypes:
        for klass in subclasses_recursive(cls):
            if klass.CODE == event_code:
                if klass.IS_ZONE:
                    return klass(zone_or_user, zones.get(zone_or_user))
                else:
                    return klass(zone_or_user, None)
        return UnknownEvent(event_code, zone_or_user)


class UnknownEvent:

    def __init__(self, code: int, zone_or_user: int):
        self.zone_or_user: int = zone_or_user
        self.code: int = code
        self.NAME: str = self.__repr__()

    def __repr__(self) -> str:
        return (f'<UnknownEvent(code={self.code}, code_hex=0x{self.code:02x},'
                f' zone_or_user={self.zone_or_user})>')


class AlarmEvent(SystemEvent):
    pass


class PerimeterAlarm(AlarmEvent):
    NAME: str = 'Perimeter Alarm'
    CODE: int = 0


class EntryExitAlarm(AlarmEvent):
    NAME: str = 'Entry/Exit Alarm'
    CODE: int = 1


class InteriorFollowerAlarm(AlarmEvent):
    NAME: str = 'Interior Follower Alarm'
    CODE: int = 4


class FireAlarm(AlarmEvent):
    NAME: str = 'Fire Alarm'
    CODE: int = 6


class AudiblePanicAlarm(AlarmEvent):
    NAME: str = 'Audible Panic Alarm'
    CODE: int = 7


class SilentPanicAlarm(AlarmEvent):
    NAME: str = 'Silent Panic Alarm'
    CODE: int = 8


class Aux24hrAlarm(AlarmEvent):
    NAME: str = '24-Hour Auxiliary'
    CODE: int = 9


class DuressAlarm(AlarmEvent):
    NAME: str = 'Duress Alarm'
    CODE: int = 0x0c


class OtherAlarmRestore(SystemEvent):
    NAME: str = 'Other Alarm Restore'
    CODE: int = 0x0e


class RfLowBattery(SystemEvent):
    NAME: str = 'RF Low Battery'
    CODE: int = 0x0f


class RfLowBatteryRestore(SystemEvent):
    NAME: str = 'RF Low Battery Restore'
    CODE: int = 0x10


class OtherTrouble(SystemEvent):
    NAME: str = 'Other Trouble'
    CODE: int = 0x11


class OtherTroubleRestore(SystemEvent):
    NAME: str = 'Other Trouble Restore'
    CODE: int = 0x12


class ArmDisarmEvent(SystemEvent):
    IS_ZONE: bool = False


class ArmStay(ArmDisarmEvent):
    NAME: str = 'Arm Stay/Home'
    CODE: int = 0x15


class Disarm(ArmDisarmEvent):
    NAME: str = 'Disarm'
    CODE: int = 0x16


class Arm(ArmDisarmEvent):
    NAME: str = 'Arm'
    CODE: int = 0x18


class LowBattery(SystemEvent):
    NAME: str = 'Low Battery'
    CODE: int = 0x1a


class LowBatteryRestore(SystemEvent):
    NAME: str = 'Low Battery Restore'
    CODE: int = 0x1b


class AcFail(SystemEvent):
    NAME: str = 'AC Fail'
    CODE: int = 0x1c


class AcRestore(SystemEvent):
    NAME: str = 'AC Restore'
    CODE: int = 0x1d


class AlarmCancel(SystemEvent):
    NAME: str = 'Alarm Cancel'
    CODE: int = 0x20
    IS_ZONE: bool = False


class OtherBypass(SystemEvent):
    NAME: str = 'Other Bypass'
    CODE: int = 0x21


class OtherUnbypass(SystemEvent):
    NAME: str = 'Other Unbypass'
    CODE: int = 0x22


class DayNightAlarm(SystemEvent):
    NAME: str = 'Day/Night Alarm'
    CODE: int = 0x23


class DayNightRestore(SystemEvent):
    NAME: str = 'Day/Night Restore'
    CODE: int = 0x24


class FailToDisarm(SystemEvent):
    NAME: str = 'Fail to Disarm'
    CODE: int = 0x27


class FailToArm(SystemEvent):
    NAME: str = 'Fail to Arm'
    CODE: int = 0x28


class FaultEvent(SystemEvent):
    NAME: str = 'Fault'
    CODE: int = 0x2b


class FaultRestoreEvent(SystemEvent):
    NAME: str = 'Fault Restore'
    CODE: int = 0x2c


class LowBatteryExtended(SystemEvent):
    NAME: str = 'Low Battery'
    CODE: int = 0x29


class LowBatteryRestoreExtended(SystemEvent):
    NAME: str = 'Low Battery Restore'
    CODE: int = 0x2a
