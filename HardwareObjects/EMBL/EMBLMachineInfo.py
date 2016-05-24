#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name] EMBLMachineInfo

[Description]
Hardware Object is used to get relevant machine information 
(current, intensity, hutch temperature and humidity, and data storage disc 
information). Value limits are included

[Channels]
- chanMachCurr
- chanStateText

[Commands]
- cmdSetIntensResolution
- cmdSetIntensAcqTime
- cmdSetIntensRange

[Emited signals]
- valuesChanged 
- inRangeChanged

[Functions]
- mach_current_changed()
- machStateTextChanged()
- updateValues()
- setInitialIntens()
- setExternalValues()


[Included Hardware Objects]
- ICShutter

Example Hardware Object XML file :
==================================
<device class="MachineInfo">
    <updateIntervalS>120</updateIntervalS>
    <discPath>/home</discPath>
    <limits>{'current':90, 'temp': 25, 'hum': 60, 'intens': 0.1, 
             'discSizeGB': 20}</limits>
</device>
"""
import logging
import time
from gevent import spawn
from urllib2 import urlopen
from datetime import datetime, timedelta
from HardwareRepository.BaseHardwareObjects import HardwareObject


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class EMBLMachineInfo(HardwareObject):
    """
    Descript. : Displays actual information about the beeamline
    """

    def __init__(self, name):
	HardwareObject.__init__(self, name)
        """
        Descript. : 
        """
        #Parameters
        self.update_interval = None  
        self.limits_dict =  None
        self.hutch_temp_addr = None
        self.hutch_hum_addr = None
	#Intensity current ranges
        self.values_dict = {}
        self.values_dict['current'] = None
        self.values_dict['stateText'] = ""
        self.values_dict['flux'] = None
        self.values_dict['cryo'] = None
        #Dictionary for booleans indicating if values are in range
        self.values_in_range_dict = {}
        self.values_in_range_dict['current'] = None
        self.values_in_range_dict['cryo'] = None
        self.values_in_range_dict['flux'] = True
        self.temp_hum_values = [None, None]
        self.temp_hum_in_range = [None, None]
        self.temp_hum_polling = None

        self.chan_mach_curr = None
        self.chan_state_text = None
        self.chan_cryojet_in = None

    def init(self):
        """
        Descript.
        """
        self.update_interval = int(self.getProperty('updateIntervalS')) 
        self.limits_dict =  eval(self.getProperty('limits'))
        self.hutch_temp_addr = self.getProperty('hutchTempAddress')
        self.hutch_hum_addr = self.getProperty('hutchHumAddress')

        self.chan_mach_curr = self.getChannelObject('machCurrent')
        if self.chan_mach_curr is not None: 
            self.chan_mach_curr.connectSignal('update', self.mach_current_changed)
        self.chan_state_text = self.getChannelObject('machStateText')
        if self.chan_state_text is not None:
            self.chan_state_text.connectSignal('update', self.state_text_changed)

        self.chan_cryojet_in = self.getChannelObject('cryojetIn')
        if self.chan_cryojet_in is not None:
            self.cryojet_in_changed(self.chan_cryojet_in.getValue())
            self.chan_cryojet_in.connectSignal('update', self.cryojet_in_changed)
        else:
            logging.getLogger("HWR").debug('MachineInfo: Cryojet channel not defined')

        self.temp_hum_polling = spawn(self.get_temp_hum_values, 
             self.getProperty("updateIntervalS"))

    def has_cryo(self):
        """
        Descript. :
        """
        return self.chan_cryojet_in is not None

    def cryojet_in_changed(self, value):
        """
        Descript. :
        """ 
        self.values_dict['cryo'] = value
        self.values_in_range_dict['cryo'] = value == 1
        self.update_values()

    def mach_current_changed(self, value):
        """
        Descript. : Function called if the machine current is changed
        Arguments : new machine current (float)
        Return    : -
        """
        if self.values_dict['current'] is None \
        or abs(self.values_dict['current'] - value) > 0.10:
            self.values_dict['current'] = value
            self.values_in_range_dict['current'] = self.values_dict['current'] > \
                 self.limits_dict['current']
            self.update_values()

    def state_text_changed(self, text):
        """
        Descript. : Function called if machine state text is changed
        Arguments : new machine state text (string)  
        Return    : -
        """
        self.values_dict['stateText'] = str(text)
        self.update_values()

    def set_flux(self, value):
        self.values_dict['flux'] = value
        self.update_values()

    def get_flux(self):
        return self.values_dict['flux']

    def update_values(self):
        """
        Descript. : Updates storage disc information, detects if intensity
		    and storage space is in limits, forms a value list 
		    and value in range list, both emited by qt as lists
        Arguments : -
        Return    : -
        """
        self.emit('valuesChanged', self.values_dict)
        self.emit('inRangeChanged', self.values_in_range_dict)
        self.emit('tempHumChanged', (self.temp_hum_values, self.temp_hum_in_range))

    def get_values(self):
        """
        Descript:
        """
        val = dict(self.values_dict)
        return val

    def get_temp_hum_values(self, sleep_time):
        """
        Descript. : 
        """
        while True:	
            temp = self.get_external_value(self.hutch_temp_addr)
            hum = self.get_external_value(self.hutch_hum_addr)
            if not None in (temp, hum):
                if (None in self.temp_hum_values) or \
                   (abs(float(temp) - self.temp_hum_values[0]) > 0.1 \
                    or abs(float(hum) != self.temp_hum_values[1] > 1)):
                    self.temp_hum_values[0] = temp
                    self.temp_hum_values[1] = hum
                    self.temp_hum_in_range[0] = temp < self.limits_dict['temp']
                    self.temp_hum_in_range[1] = hum < self.limits_dict['hum']
                    self.emit('tempHumChanged', (self.temp_hum_values, 
                                                 self.temp_hum_in_range))
            
            time.sleep(sleep_time)	

    def get_current(self):
        return self.values_dict['current']
 
    def get_current_value(self):
        """
        Descript. :
        """     
        return self.values_dict['current']

    def	get_message(self):
        """
        Descript :
        """  
        return self.values_dict['stateText']

    def get_external_value(self, addr):
        """
        Description : Extracts value from the given epics address. This is  
		      very specific implementation how to get a value from 
		      epics web tool. At first web address string is formed 
		      and then web page by urllib2 extracted. Page contains 
		      column with records. 
		      Then the last value is choosen as the last active value.
        Arguments   : epics address (string)
        Return      : value (float)
        """
        url_prefix = "http://cssweb.desy.de:8084/ArchiveViewer/archive" + \
                     "reader.jsp?DIRECTORY=%2Fdata7%2FChannelArchiver%" + \
                     "2FchannelReference2.kryo&PATTERN=&"
        end = datetime.now()
        start = end - timedelta(hours = 24)
        url_date = "=on&STARTMONTH=%d&STARTDAY=%d&STARTYEAR=%d&STARTHOUR=%d&STARTMINUTE=%d&STARTSECOND=0" % \
                  (start.month, start.day,start.year, start.hour, start.minute)
        url_date = url_date + ("&ENDMONTH=%d&ENDDAY=%d&ENDYEAR=%d&ENDHOUR=%d&ENDMINUTE=%d&ENDSECOND=0" % \
                  (end.month, end.day, end.year, end.hour, (end.minute - 10)))
        url_date = url_date + "&COMMAND=GET&Y0=0&Y1=0&FORMAT=SPREADSHEET&INTERPOL=0&NUMOFPOINTS=10"
        url_file = None
        last_value = None

        try:
            addr = addr.split(':')        
            url_device = "NAMES=" + addr[0] + "%3A" + addr[1] + "%3A" + \
                         addr[2] + "%3A" + addr[3]
            url_device = url_device + "&FRAME2=1" + addr[0] + "%3A" + \
                         addr[1] + "%3A" + addr[2] + "%3A" + addr[3]
            url_device = url_device + "&NAMES2=&" + addr[0] + "%3A" + \
                         addr[1] + "%3A" + addr[2] + "%3A" + addr[3]
            final_url = url_prefix + url_device + url_date
            url_file = urlopen(final_url)
            for line in url_file:
                line_el = line.split()
                if line_el:
                    if line_el[-1].isdigit:
                        last_value = line_el[-1]
            last_value = float(last_value)
        except:
            logging.getLogger("HWR").debug("MachineInfo: Unable to read epics values")
        finally:
            if url_file:
                url_file.close()	
        return last_value   
