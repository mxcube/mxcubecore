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
- chanintensMean 
- chanintensRange

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
- intensRangeChanged()
- intensMeanChanged()
- shutterStateChanged()
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
    <channel type="tine" name="machCurrent" tinename=
             "/PETRA/ARCHIVER/keyword">curDC</channel>
    <channel type="tine" name="machStateText" tinename=
             "/PETRA/ARCHIVER/keyword">MachineStateText</channel>
    <!--P14-->
    <hutchTempAddress>G47cS9:K:KL:P14EH1RaTIW_ai</hutchTempAddress>
    <hutchHumAddress>G47cS9:K:KL:P14EH1RaF_ai</hutchHumAddress>
    <!--P13-->
    <!-- <hutchTempAddress>G47cS9:K:KL:P13EH1RaTIW_ai</hutchTempAddress>
    <hutchHumAddress>G47cS9:K:KL:P13EH1RaF_ai</hutchHumAddress> -->
    <intensity>  
        <shutterOpenValue>0</shutterOpenValue>
        <valueOnClose>1e-9</valueOnClose>
        <initialResolution>1</initialResolution>
        <updateRelativeTolerance>0.1</updateRelativeTolerance>
        <acqTimeOnCloseMs>1000</acqTimeOnCloseMs>
        <acqTimeOnOpenMs>100</acqTimeOnOpenMs>
        <ranges>
            <range>
                <CurMax>2.5e-9</CurMax>
                <CurOffset>-7.53517e-12</CurOffset>
                <CurIndex>2</CurIndex>
            </range>
        </ranges>
    </intensity>
    <safetyshutter>/ICSShutter</safetyshutter>
    <amplChannelIndex>1</amplChannelIndex>
    <channel type="tine" name="intensMean" tinename="/P14/QBPMs/QBPM2">
             ChannelsMean.get</channel>
    <channel type="tine" name="intensRange" tinename="/P14/QBPMs/QBPM2">
             CurrentRange.set</channel>
    <command type="tine" name="setIntensResolution" tinename="/P14/QBPMs/QBPM2">
             ADCResolution.set</command>
    <command type="tine" name="setIntensAcqTime" tinename="/P14/QBPMs/QBPM2">
             AcquisitionTime.set</command>
    <command type="tine" name="setIntensRange" tinename="/P14/QBPMs/QBPM2">
             CurrentRange.set</command>
</device>
"""
import logging
import time
from gevent import spawn
from urllib2 import urlopen
from datetime import datetime, timedelta
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Equipment


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


class EMBLMachineInfo(Equipment):
    """
    Descript. : Displays actual information about the beeamline
    """

    def __init__(self, name):
	Equipment.__init__(self, name)
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
        self.values_dict['intens'] = {}
        self.values_dict['intens']['value'] = None
        self.values_dict['cryo'] = None
        #Dictionary for booleans indicating if values are in range
        self.values_in_range_dict = {}
        self.values_in_range_dict['current'] = None
        self.values_in_range_dict['intens'] = None
        self.values_in_range_dict['cryo'] = None
        self.temp_hum_values = [0, 0]
        self.temp_hum_in_range = [False, False]

        self.intens_range = None
        self.ampl_chan_index = None
        self.shutter_is_opened = None
        self.shutter_hwobj = None
        self.temp_hum_polling = None

        self.chan_mach_curr = None
        self.chan_state_text = None
        self.chan_intens_mean = None
        self.chan_intens_range = None
        self.chan_cryojet_in = None

        self.cmd_set_intens_resolution = None
        self.cmd_set_intens_acq_time = None
        self.cmd_set_intens_range = None
	
    def init(self):
        """
        Descript.
        """
        self.update_interval = int(self.getProperty('updateIntervalS')) 
        self.limits_dict =  eval(self.getProperty('limits'))
        self.hutch_temp_addr = self.getProperty('hutchTempAddress')
        self.hutch_hum_addr = self.getProperty('hutchHumAddress')
        self.ampl_chan_index = int(self.getProperty('amplChannelIndex'))

        self.values_dict['intens'] = self['intensity'].getProperties()
        self.values_dict['intens']['value'] = None
        self.values_dict['intens']['ranges'] = []
        for intens_range in self['intensity']['ranges']:
            temp_intens_range = {}
            temp_intens_range['max'] = intens_range.CurMax
            temp_intens_range['index'] = intens_range.CurIndex
            temp_intens_range['offset'] = intens_range.CurOffset
            self.values_dict['intens']['ranges'].append(temp_intens_range)
            #Sort the ranges accordingly to the maximal values
        self.values_dict['intens']['ranges'] = \
             sorted(self.values_dict['intens']['ranges'], \
             key=lambda item: item['max'])

        self.chan_mach_curr = self.getChannelObject('machCurrent')
        if self.chan_mach_curr is not None: 
            self.chan_mach_curr.connectSignal('update', self.mach_current_changed)
        self.chan_state_text = self.getChannelObject('machStateText')
        if self.chan_state_text is not None:
            self.chan_state_text.connectSignal('update', self.state_text_changed)
        
        self.chan_intens_mean = self.getChannelObject('intensMean')
        if self.chan_intens_mean is not None:
            self.chan_intens_mean.connectSignal('update', self.intens_mean_changed)
        self.chan_intens_range = self.getChannelObject('intensRange')

        self.cmd_set_intens_resolution = self.getCommandObject('setIntensResolution')
        self.cmd_set_intens_acq_time = self.getCommandObject('setIntensAcqTime')
        if self.cmd_set_intens_acq_time is not None:
            self.cmd_set_intens_acq_time(self.values_dict['intens']['acqTimeOnOpenMs'])
        self.cmd_set_intens_range = self.getCommandObject('setIntensRange')

        self.chan_cryojet_in = self.getChannelObject('cryojetIn')
        if self.chan_cryojet_in is not None:
            self.values_dict['cryo'] = self.chan_cryojet_in.getValue()
            self.chan_cryojet_in.connectSignal('update', self.cryojet_in_changed)
        else:
            logging.getLogger("HWR").debug('MachineInfo: Cryojet channel not defined')

        self.shutter_is_opened = False
        self.shutter_hwobj = self.getObjectByRole('shutter')
        if self.shutter_hwobj is not None:
            self.connect(self.shutter_hwobj, 'shutterStateChanged', self.shutter_state_changed)

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
        self.values_in_range_dict['cryo'] = value == 1
        #self.update_values()

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
            #self.update_values()

    def state_text_changed(self, text):
        """
        Descript. : Function called if machine state text is changed
        Arguments : new machine state text (string)  
        Return    : -
        """
        self.values_dict['stateText'] = str(text)
        #self.update_values()

    def intens_mean_changed(self, value):
        """
        Descript. : Event if intensity value is changed
        Arguments : new intensity value (float)
        Return    : -
        """
        if self.shutter_hwobj is not None:
            if self.shutter_hwobj.is_shuter_open():
                intens_range_now = self.chan_intens_range.getValue()
                for intens_range in self.values_dict['intens']['ranges']:
                    if intens_range['index'] is intens_range_now:
                        self.values_dict['intens']['value'] = \
                             value[self.ampl_chan_index] - \
                             intens_range['offset']
                        break
                self.values_in_range_dict['intens'] = \
                     self.values_dict['intens']['value'] > \
                     self.limits_dict['intens']
            else:
                self.values_dict['intens']['value'] = None
                self.values_in_range_dict['intens'] = True	
        self.update_values()

    def shutter_state_changed(self, state):
        """
        Descript. : Function called by shutter HO if shutter state is changed
        Arguments : new state (string)
        Return    : -
	"""
        if state == 'opened':
            self.shutter_is_opened = True
            if self.cmd_set_intens_acq_time is not None:
                self.cmd_set_intens_acq_time(self.values_dict['intens'] \
                     ['acqTimeOnOpenMs']) 
        else:
            self.shutter_is_opened = False
            if self.cmd_set_intens_acq_time is not None:
                self.cmd_set_intens_acq_time(self.values_dict['intens'] \
                     ['acqTimeOnCloseMs'])

    def update_values(self):
        """
        Descript. : Updates storage disc information, detects if intensity
		    and storage space is in limits, forms a value list 
		    and value in range list, both emited by qt as lists
        Arguments : -
        Return    : -
        """
        values_to_send = []
        values_to_send.append(self.values_dict['current'])
        values_to_send.append(self.values_dict['stateText'])
        values_to_send.append(self.values_dict['intens']['value'])
        values_to_send.append(self.values_dict['cryo'])       
        self.emit('valuesChanged', values_to_send)
        self.emit('inRangeChanged', self.values_in_range_dict)
        self.emit('tempHumChanged', (self.temp_hum_values, self.temp_hum_in_range))

    def get_values(self):
        """
        Descript:
        """
        val = dict(self.values_dict)
        val['intens'] = val['intens']['value']
        return val

    def get_temp_hum_values(self, sleep_time):
        """
        Descript. : 
        """
        while True:	
            temp = self.get_external_value(self.hutch_temp_addr)
            hum = self.get_external_value(self.hutch_hum_addr)
            if temp and hum:
                if abs(float(temp) - self.temp_hum_values[0]) > 0.1 \
                or abs(float(hum) != self.temp_hum_values[1] > 1):
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
