#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
Hardware Object is used to get relevant machine information
(current, intensity, hutch temperature and humidity, and data storage disc
information). Value limits are included
"""

import os
import time
import logging

try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

from collections import OrderedDict
from datetime import datetime, timedelta
from gevent import spawn

from HardwareRepository.BaseHardwareObjects import HardwareObject

from HardwareRepository import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLMachineInfo(HardwareObject):
    """Displays actual information about the beamline
    """

    def __init__(self, name):
        """OrderedDict is used to have a sorted items for display
           and directory like access when updating values
        """

        HardwareObject.__init__(self, name)

        self.update_interval = None
        self.limits_dict = None
        self.hutch_temp_addr = None
        self.hutch_hum_addr = None
        self.hutch_temp = 0
        self.hutch_hum = 0
        self.overflow_alarm = None
        self.low_level_alarm = None
        self.state_text = ""
        self.ring_energy = None
        self.bunch_count = None
        self.flux_area = None
        self.last_transmission = None
        self.frontend_is_open = False
        self.undulator_gap = 9999

        self.values_ordered_dict = OrderedDict()

        self.values_ordered_dict["current"] = {
            "value": 0,
            "value_str": "",
            "in_range": False,
            "title": "Machine current",
            "bold": True,
        }

        self.values_ordered_dict["machine_state"] = {
            "value": None,
            "in_range": False,
            "title": "Machine state",
        }

        self.values_ordered_dict["frontend_undulator"] = {
            "value": None,
            "in_range": True,
            "title": "Front End, undulator gap",
        }

        self.values_ordered_dict["temp_hum"] = {
            "value": "",
            "value_str": "",
            "in_range": None,
            "title": "Hutch temperature and humidity",
        }

        self.temp_hum_values = [None, None]
        self.temp_hum_in_range = [None, None]
        self.temp_hum_polling = None

        self.chan_mach_curr = None
        self.chan_mach_energy = None
        self.chan_bunch_count = None
        self.chan_frontend_status = None
        self.chan_undulator_gap = None
        self.chan_state_text = None
        self.chan_cryojet_in = None
        self.chan_sc_dewar_low_level_alarm = None
        self.chan_sc_dewar_overflow_alarm = None

    def init(self):

        self.update_interval = int(self.get_property("updateIntervalS"))
        self.limits_dict = eval(self.get_property("limits"))
        self.hutch_temp_addr = self.get_property("hutchTempAddress")
        self.hutch_hum_addr = self.get_property("hutchHumAddress")

        self.chan_mach_curr = self.get_channel_object("machCurrent")
        self.chan_mach_curr.connect_signal("update", self.mach_current_changed)
        self.chan_state_text = self.get_channel_object("machStateText")
        self.chan_state_text.connect_signal("update", self.state_text_changed)
        # self.state_text_changed(self.chan_state_text.get_value())

        self.chan_mach_energy = self.get_channel_object("machEnergy")
        self.chan_mach_energy.connect_signal("update", self.mach_energy_changed)
        self.chan_bunch_count = self.get_channel_object("machBunchCount")
        self.chan_bunch_count.connect_signal("update", self.bunch_count_changed)
        self.chan_frontend_status = self.get_channel_object("frontEndStatus")
        self.chan_frontend_status.connect_signal("update", self.frontend_status_changed)
        # self.frontend_status_changed(self.chan_frontend_status.get_value())

        if HWR.beamline.flux is not None:
            self.connect(HWR.beamline.flux, "fluxInfoChanged", self.flux_info_changed)
            self.values_ordered_dict["flux"] = {
                "value": 1,
                "value_str": "Remeasure flux!",
                "in_range": False,
                "title": "Measured flux",
            }

        self.chan_undulator_gap = self.get_channel_object("chanUndulatorGap")
        if self.chan_undulator_gap is not None:
            self.chan_undulator_gap.connect_signal("update", self.undulator_gap_changed)
        self.undulator_gap_changed(self.chan_undulator_gap.get_value())

        self.chan_cryojet_in = self.get_channel_object("cryojetIn", optional=True)
        if self.chan_cryojet_in is not None:
            self.values_ordered_dict["cryo"] = {
                "value": "???",
                "in_range": None,
                "title": "Cryoject in place",
            }
            self.cryojet_in_changed(self.chan_cryojet_in.get_value())
            self.chan_cryojet_in.connect_signal("update", self.cryojet_in_changed)
        else:
            logging.getLogger("HWR").debug("MachineInfo: Cryojet channel not defined")

        self.chan_sc_dewar_low_level_alarm = self.get_channel_object(
            "scLowLevelAlarm", optional=True
        )
        if self.chan_sc_dewar_low_level_alarm is not None:
            self.values_ordered_dict["sc"] = {
                "value": "Dewar level in range",
                "in_range": True,
                "title": "Sample changer",
            }

            self.chan_sc_dewar_low_level_alarm.connect_signal(
                "update", self.low_level_alarm_changed
            )
            self.low_level_alarm_changed(self.chan_sc_dewar_low_level_alarm.get_value())

        self.chan_sc_dewar_overflow_alarm = self.get_channel_object(
            "scOverflowAlarm", optional=True
        )
        if self.chan_sc_dewar_overflow_alarm is not None:
            self.chan_sc_dewar_overflow_alarm.connect_signal(
                "update", self.overflow_alarm_changed
            )

        if HWR.beamline.ppu_control is not None:
            self.values_ordered_dict["ppu"] = {
                "value": "- - -",
                "in_range": False,
                "title": "Files copied - pending - failed",
            }

            self.connect(
                HWR.beamline.ppu_control,
                "fileTranferStatusChanged",
                self.file_transfer_status_changed,
            )

        self.chan_count_dropped = self.get_channel_object(
            "framesCountDropped", optional=True
        )
        if self.chan_count_dropped is not None:
            self.values_ordered_dict["frames_dropped"] = {
                "value": "",
                "in_range": True,
                "title": "Frames dropped",
            }
            self.chan_count_dropped.connect_signal("update", self.count_dropped_changed)

        self.temp_hum_polling = spawn(
            self.get_temp_hum_values, self.get_property("updateIntervalS")
        )

        self.re_emit_values()

    def clear_gevent(self):
        """Clear gevent tasks

        :return: None
        """
        self.temp_hum_polling.kill()
        if self.update_task:
            self.update_task.kill()

    def cryojet_in_changed(self, value):
        """Updates cryojet status

        :param value: status
        :type value: bool
        :return: None
        """

        self.values_ordered_dict["cryo"]["in_range"] = False
        self.values_ordered_dict["cryo"]["bold"] = True

        if value == 1:
            self.values_ordered_dict["cryo"]["value"] = " In place"
            self.values_ordered_dict["cryo"]["in_range"] = True
            self.values_ordered_dict["cryo"]["bold"] = False
        elif value == 0:
            self.values_ordered_dict["cryo"]["value"] = "NOT IN PLACE"
        else:
            self.values_ordered_dict["cryo"]["value"] = "Unknown"
        self.re_emit_values()

    def mach_current_changed(self, value):
        """Method called if the machine current is changed

        :param value: new machine current
        :type value: float
        """
        if (
            self.values_ordered_dict["current"]["value"] is None
            or abs(self.values_ordered_dict["current"]["value"] - value) > 0.00001
        ):
            self.values_ordered_dict["current"]["value"] = value
            self.values_ordered_dict["current"]["value_str"] = "%.1f mA" % value
            self.values_ordered_dict["current"]["in_range"] = value > 60.0
            self.re_emit_values()

    def state_text_changed(self, text):
        """Function called if machine state text is changed

        :param text: new machine state text
        :type text: string
        """
        self.state_text = str(text)
        self.values_ordered_dict["machine_state"]["in_range"] = text != "Fehler"
        self.update_machine_state()

    def mach_energy_changed(self, value):
        """Updates machine energy value

        :param value: machine energy
        :type value: float
        :return: None
        """
        self.ring_energy = value
        self.update_machine_state()

    def bunch_count_changed(self, value):
        """Bunch count changed"""
        self.bunch_count = value
        self.update_machine_state()

    def frontend_status_changed(self, value):
        """
        Update front end status
        :param value:
        :return:
        """
        self.frontend_is_open = value[2] == 2
        self.update_machine_state()

    def undulator_gap_changed(self, value):
        """
        Update undulator gaps
        :param value: float
        :return:
        """
        if isinstance(value, (list, tuple)):
            value = value[0]
        self.undulator_gap = value / 1000

    def update_machine_state(self):
        """Machine state assembly"""
        state_text = self.state_text
        if self.ring_energy is not None:
            state_text += "\n%.2f GeV " % self.ring_energy
        if self.bunch_count is not None:
            state_text += ", %d Bunches" % self.bunch_count
        self.values_ordered_dict["machine_state"]["value"] = state_text

        if not self.frontend_is_open or self.undulator_gap > 30:
            self.values_ordered_dict["frontend_undulator"]["in_range"] = False
        else:
            self.values_ordered_dict["frontend_undulator"]["in_range"] = True
        if self.frontend_is_open:
            self.values_ordered_dict["frontend_undulator"]["value_str"] = (
                "Opened, %d mm" % self.undulator_gap
            )
        else:
            self.values_ordered_dict["frontend_undulator"]["value_str"] = (
                "Closed, %d mm" % self.undulator_gap
            )

        self.re_emit_values()

    def low_level_alarm_changed(self, value):
        """Low level alarm"""
        self.low_level_alarm = value
        self.update_sc_alarm()

    def overflow_alarm_changed(self, value):
        """Overflow alarm"""
        self.overflow_alarm = value
        self.update_sc_alarm()

    def file_transfer_status_changed(self, status):
        """
        Updates info about file beeing transfered
        :param total: int
        :param pending: int
        :param failed: int
        :return:
        """
        self.values_ordered_dict["ppu"]["value"] = "%d  -  %d  -  %d" % (
            status[0],
            status[1],
            status[2],
        )
        self.values_ordered_dict["ppu"]["in_range"] = status[2] == 0

        if status[2] > 0:
            logging.getLogger("GUI").error(
                "Error in file transfer (%d files failed to copy)." % status[2]
            )

    def count_dropped_changed(self, num_dropped):
        self.values_ordered_dict["frames_dropped"]["value"] = str(num_dropped)
        self.values_ordered_dict["frames_dropped"]["in_range"] = num_dropped == 0
        if num_dropped > 0:
            logging.getLogger("GUI").error(
                "Error during the frame acquisition (in total %d frame(s) dropped)."
                % num_dropped
            )

    def update_sc_alarm(self):
        """Sample changer alarm"""
        if self.low_level_alarm == 1:
            self.values_ordered_dict["sc"]["value"] = "Low level alarm!"
            self.values_ordered_dict["sc"]["in_range"] = False
            self.values_ordered_dict["sc"]["bold"] = True
            logging.getLogger("GUI").error(
                "Liquid nitrogen level in sample changer dewar is too low!"
            )

        elif self.overflow_alarm:
            self.values_ordered_dict["sc"]["value"] = "Overflow alarm!"
            self.values_ordered_dict["sc"]["in_range"] = False
            self.values_ordered_dict["sc"]["bold"] = True
            logging.getLogger("GUI").error(
                "Liquid nitrogen overflow in sample changer dewar!"
            )
        else:
            self.values_ordered_dict["sc"]["value"] = "Dewar level in range"
            self.values_ordered_dict["sc"]["in_range"] = True
        self.re_emit_values()

    def flux_info_changed(self, flux_info):
        """Sets flux value"""

        if flux_info["measured"] is None:
            self.values_ordered_dict["flux"]["value"] = 0
            self.values_ordered_dict["flux"][
                "value_str"
            ] = "Beamline mode changed\nRemeasure flux!"
            self.values_ordered_dict["flux"]["in_range"] = False
        else:
            msg_str = "Flux: %.2E ph/s\n" % flux_info["measured"]["flux"]
            msg_str += "%d%% transmission, %dx%d beam" % (
                flux_info["measured"]["transmission"],
                flux_info["measured"]["size_x"] * 1000,
                flux_info["measured"]["size_y"] * 1000,
            )

            self.values_ordered_dict["flux"]["value"] = flux_info["measured"]["flux"]
            self.values_ordered_dict["flux"]["value_str"] = msg_str
            self.values_ordered_dict["flux"]["in_range"] = (
                flux_info["measured"]["flux"] > 1e6
            )
        self.re_emit_values()

    def re_emit_values(self):
        """Emits list of values"""
        self.emit("valuesChanged", self.values_ordered_dict)

    def get_values(self):
        """Returns list of values"""
        return self.values_ordered_dict

    def get_temp_hum_values(self, sleep_time):
        """Updates temperatur and humidity values"""
        while True:
            temp = self.get_external_value(self.hutch_temp_addr)
            hum = self.get_external_value(self.hutch_hum_addr)
            if not None in (temp, hum):
                if abs(float(temp) - self.hutch_temp) > 0.1 or abs(
                    float(hum) != self.hutch_hum > 1
                ):
                    self.hutch_temp = temp
                    self.hutch_hum = hum
                    self.values_ordered_dict["temp_hum"][
                        "value"
                    ] = "%.1f C, %.1f %%" % (temp, hum)
                    self.values_ordered_dict["temp_hum"]["in_range"] = (
                        temp < 25 and hum < 60
                    )
                    self.re_emit_values()
            time.sleep(sleep_time)

    def get_current(self):
        """Returns machine current in mA
        """
        return self.values_ordered_dict["current"]["value"]

    def get_current_value(self):
        """Returns machine current in mA"""
        return self.values_ordered_dict["current"]["value"]

    def get_message(self):
        """Returns synchrotron state text"""
        return self.state_text

    def get_external_value(self, addr):
        """Extracts value from the given epics address. This is very specific
           implementation how to get a value from epics web tool. At first
           web address string is formed and then web page by urllib2
           extracted. Page contains column with records.
           Then the last value is choosen as the last active value.

        :param addr: epics address
        :type addr: str
        :returns : float
        """
        url_prefix = (
            "http://cssweb.desy.de:8084/ArchiveViewer/archive"
            + "reader.jsp?DIRECTORY=%2Fdata7%2FChannelArchiver%"
            + "2FchannelReference2.kryo&PATTERN=&"
        )
        end = datetime.now()
        start = end - timedelta(hours=24)
        url_date = "=on&STARTMONTH=%d&STARTDAY=%d&STARTYEAR=%d" % (
            start.month,
            start.day,
            start.year,
        ) + "&STARTHOUR=%d&STARTMINUTE=%d&STARTSECOND=0" % (start.hour, start.minute)
        url_date = url_date + (
            "&ENDMONTH=%d&ENDDAY=%d&ENDYEAR=%d" % (end.month, end.day, end.year)
            + "&ENDHOUR=%d&ENDMINUTE=%d&ENDSECOND=0" % (end.hour, (end.minute - 10))
        )
        url_date = (
            url_date
            + "&COMMAND=GET&Y0=0&Y1=0&FORMAT=SPREADSHEET&"
            + "INTERPOL=0&NUMOFPOINTS=10"
        )
        url_file = None
        last_value = None
        try:
            addr = addr.split(":")
            url_device = (
                "NAMES=" + addr[0] + "%3A" + addr[1] + "%3A" + addr[2] + "%3A" + addr[3]
            )
            url_device = (
                url_device
                + "&FRAME2=1"
                + addr[0]
                + "%3A"
                + addr[1]
                + "%3A"
                + addr[2]
                + "%3A"
                + addr[3]
            )
            url_device = (
                url_device
                + "&NAMES2=&"
                + addr[0]
                + "%3A"
                + addr[1]
                + "%3A"
                + addr[2]
                + "%3A"
                + addr[3]
            )
            final_url = url_prefix + url_device + url_date
            url_file = urlopen(final_url)
            for line in url_file:
                line_el = line.split()
                if line_el:
                    if line_el[-1].isdigit:
                        last_value = line_el[-1]
            last_value = float(last_value)
        except Exception:
            logging.getLogger("HWR").debug("MachineInfo: Unable to read epics values")
        finally:
            if url_file:
                url_file.close()
        return last_value

    def get_ramdisk_size(self):
        """
        Gets ramdisk size in bytes
        :return: total, free disc size in bytes and free disc in perc
        """
        data_dir = "/ramdisk/"
        # p = '/' + data_dir.split('/')[1]
        # data_dir = str(p)
        if os.path.exists(data_dir):
            st = os.statvfs(data_dir)

            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            perc = st.f_bavail / float(st.f_blocks)
            return total, free, perc
        else:
            return None, None, None

    def sizeof_fmt(self, num):
        """Returns disk space formated in string"""

        try:
            for x in ["bytes", "KB", "MB", "GB"]:
                if num < 1024.0:
                    return "%3.1f%s" % (num, x)
                num /= 1024.0
            return "%3.1f%s" % (num, "TB")
        except Exception:
            return "???"
