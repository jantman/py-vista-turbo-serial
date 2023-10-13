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
import argparse
import logging
from typing import Dict, List, Set

from py_vista_turbo_serial.communicator import Communicator
from py_vista_turbo_serial.messages import (
    MessagePacket, ArmAwayMessage, ArmHomeMessage, DisarmMessage,
    ArmingStatusRequest, ArmingStatusReport, PartitionState, ZoneStatusRequest,
    ZoneStatusReport, ZoneState, ZonePartitionRequest, ZonePartitionReport,
    SystemEventNotification
)
from py_vista_turbo_serial.events import (
    AlarmEvent, OtherAlarmRestore, RfLowBattery, RfLowBatteryRestore,
    OtherTrouble, OtherTroubleRestore, ArmDisarmEvent, ArmStay, Arm, Disarm,
    LowBattery, LowBatteryRestore, AcFail, AcRestore, AlarmCancel,
    OtherBypass, OtherUnbypass, FaultEvent, FaultRestoreEvent, SystemEvent
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(levelname)s] %(message)s"
)
logger: logging.Logger = logging.getLogger()


class StateMonitor:

    def __init__(self, port: str):
        self.panel: Communicator = Communicator(port=port)
        self.arming_status: Dict[int, PartitionState] = {}
        self.zone_status: Dict[int, ZoneState] = {}
        self.zone_partitions: Dict[int, int] = {}
        self.zone_troubles: Dict[int, Set[str]] = {}

    def _handle_alarm(self, evt: AlarmEvent):
        logger.debug(
            'Event: %s in zone %d', evt.NAME, evt.zone_or_user
        )
        if self.zone_status[evt.zone_or_user].alarm:
            logger.warning(
                'Got %s event for zone %d but zone is already in alarm',
                evt.NAME, evt.zone_or_user
            )
        else:
            logger.info(
                'CHANGE zone %d alarm state to True', evt.zone_or_user
            )
            self.zone_status[evt.zone_or_user].alarm = True

    def _handle_alarm_restore(self, evt: OtherAlarmRestore):
        logger.debug(
            'Got OtherAlarmRestore event for zone %d', evt.zone_or_user
        )
        if self.zone_status[evt.zone_or_user].alarm:
            logger.info(
                'CHANGE zone %d alarm state to False', evt.zone_or_user
            )
            self.zone_status[evt.zone_or_user].alarm = False
        else:
            logger.warning(
                'Got %s event for zone %d but zone is not in alarm',
                evt.NAME, evt.zone_or_user
            )

    def _handle_zone_trouble(self, evt: SystemEvent):
        logger.debug(
            'Got %s event for zone %d',
            evt.NAME, evt.zone_or_user
        )
        if self.zone_status[evt.zone_or_user].trouble:
            if evt.NAME in self.zone_troubles[evt.zone_or_user]:
                logger.debug(
                    'Got another %s message for zone %d',
                    evt.NAME, evt.zone_or_user
                )
            else:
                logger.info(
                    'ADD zone %s trouble cause: %s',
                    evt.zone_or_user, evt.NAME
                )
                self.zone_troubles[evt.zone_or_user].add(evt.NAME)
        else:
            logger.info(
                'CHANGE zone %d is in trouble: %s',
                evt.zone_or_user, evt.NAME
            )
            self.zone_troubles[evt.zone_or_user].add(evt.NAME)
            self.zone_status[evt.zone_or_user].trouble = True

    def _handle_zone_trouble_restore(self, evt: SystemEvent):
        logger.debug(
            'Got %s event for zone %d',
            evt.NAME, evt.zone_or_user
        )
        if self.zone_status[evt.zone_or_user].trouble:
            if evt.NAME not in self.zone_troubles[evt.zone_or_user]:
                logger.warning(
                    'Got %s for zone %d but zone trouble causes are: %s',
                    evt.NAME, evt.zone_or_user,
                    self.zone_troubles[evt.zone_or_user]
                )
            else:
                logger.info(
                    'REMOVE zone %s trouble cause: %s',
                    evt.zone_or_user, evt.NAME
                )
                self.zone_troubles[evt.zone_or_user].remove(evt.NAME)
            if not self.zone_troubles[evt.zone_or_user]:
                logger.info(
                    'CHANGE zone %d is no longer in trouble', evt.zone_or_user
                )
                self.zone_status[evt.zone_or_user].trouble = False
        else:
            logger.warning(
                'Got %s for zone %d but zone is not in trouble',
                evt.NAME, evt.zone_or_user
            )

    def _handle_zone_bypass(self, evt: SystemEvent):
        if self.zone_status[evt.zone_or_user].bypassed:
            logger.debug(
                'Got another %s message for zone %d',
                evt.NAME, evt.zone_or_user
            )
            return
        logger.info(
            'CHANGE zone %d to Bypassed', evt.zone_or_user
        )
        self.zone_status[evt.zone_or_user].bypassed = True

    def _handle_zone_unbypass(self, evt: SystemEvent):
        if not self.zone_status[evt.zone_or_user].bypassed:
            logger.debug(
                'Got another %s message for zone %d',
                evt.NAME, evt.zone_or_user
            )
            return
        logger.info(
            'CHANGE zone %d to Unbypassed', evt.zone_or_user
        )
        self.zone_status[evt.zone_or_user].bypassed = False

    def _handle_zone_fault(self, evt: SystemEvent):
        raise NotImplementedError(
            'Not implemented; also how to handle NC/NO zones?'
        )
        if self.zone_status[evt.zone_or_user].closed:
            logger.debug(
                'Got another %s message for zone %d',
                evt.NAME, evt.zone_or_user
            )
            return
        logger.info(
            'CHANGE zone %d to Bypassed', evt.zone_or_user
        )
        self.zone_status[evt.zone_or_user].bypassed = True

    def _handle_zone_fault_restore(self, evt: SystemEvent):
        raise NotImplementedError('not implemented - also NC/NO?')
        if not self.zone_status[evt.zone_or_user].bypassed:
            logger.debug(
                'Got another %s message for zone %d',
                evt.NAME, evt.zone_or_user
            )
            return
        logger.info(
            'CHANGE zone %d to Unbypassed', evt.zone_or_user
        )
        self.zone_status[evt.zone_or_user].bypassed = False

    def _handle_event(self, evt: SystemEvent):
        logger.debug(
            'Got System Event Notification: %s', evt
        )
        if isinstance(evt, AlarmEvent):
            return self._handle_alarm(evt)
        if isinstance(evt, OtherAlarmRestore):
            return self._handle_alarm_restore(evt)
        if (
            isinstance(evt, RfLowBattery) or
            isinstance(evt, OtherTrouble) or
            isinstance(evt, LowBattery)
        ):
            return self._handle_zone_trouble(evt)
        if (
            isinstance(evt, RfLowBatteryRestore) or
            isinstance(evt, OtherTroubleRestore) or
            isinstance(evt, LowBatteryRestore)
        ):
            return self._handle_zone_trouble_restore(evt)
        if isinstance(evt, OtherBypass):
            return self._handle_zone_bypass(evt)
        if isinstance(evt, OtherUnbypass):
            return self._handle_zone_unbypass(evt)
        if isinstance(evt, FaultEvent):
            return self._handle_zone_fault(evt)
        if isinstance(evt, FaultRestoreEvent):
            return self._handle_zone_fault_restore(evt)
        # @TODO ArmDisarmEvent (ArmStay, Disarm, Arm)
        # @TODO AcFail, AcRestore
        # @TODO AlarmCancel
        # @TODO DayNightAlarm, DayNightDestore
        # @TODO FailToDisarm
        # @TODO FailToArm
        logger.warning(
            'Got un-handled System Event Notification: %s', evt
        )

    def run(self):
        # @TODO every N minutes/hours we want to re-send the status requests
        #    and re-populate our stored state
        # queue commands to get initial state
        self.panel.send_message(ArmingStatusRequest.generate())
        self.panel.send_message(ZoneStatusRequest.generate())
        self.panel.send_message(ZonePartitionRequest.generate())
        is_ready: bool = False
        message: MessagePacket
        for message in self.panel.communicate():
            if isinstance(message, ArmingStatusReport):
                self.arming_status.update(message.partition_state)
                logger.info(
                    'Got initial partition arming status: %s',
                    self.arming_status
                )
            elif isinstance(message, ZoneStatusReport):
                self.zone_status.update(message.zones)
                logger.info(
                    'Got initial zone status: %s', self.zone_status
                )
                self.zone_troubles = {
                    x: set() for x in self.zone_status.keys()
                }
            elif isinstance(message, ZonePartitionReport):
                self.zone_partitions.update(message.partitions)
                logger.info(
                    'Got zone partition state: %s', self.zone_partitions
                )
            elif isinstance(message, ArmAwayMessage):
                logger.info(
                    'Got Arm Away for user %s (code %s)',
                    message.user, message.user_code
                )
                # @TODO how to handle arm away message
                logger.error(
                    'NOT IMPLEMENTED: how to handle ArmAwayMessage?'
                )
            elif isinstance(message, ArmHomeMessage):
                logger.info(
                    'Got Arm Home for user %s (code %s)',
                    message.user, message.user_code
                )
                # @TODO how to handle arm home message
                logger.error(
                    'NOT IMPLEMENTED: how to handle ArmHomeMessage?'
                )
            elif isinstance(message, DisarmMessage):
                logger.info(
                    'Got Disarm for user %s (code %s)',
                    message.user, message.user_code
                )
                # @TODO how to handle disarm message
                logger.error(
                    'NOT IMPLEMENTED: how to handle DisarmMessage?'
                )
            elif isinstance(message, SystemEventNotification):
                self._handle_event(message.event_type)
            else:
                logger.error(
                    'Got un-handled message: %s', message
                )
            if (
                (not is_ready) and
                self.arming_status and self.zone_status and self.zone_partitions
            ):
                is_ready = True
                logger.info('Initial state data is populated.')


def parse_args(argv):
    p = argparse.ArgumentParser(description='Alarm state monitor logger')
    p.add_argument(
        '-v', '--verbose', dest='verbose', action='store_true',
        default=False, help='verbose output'
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

    StateMonitor(args.PORT).run()


if __name__ == "__main__":
    main()
