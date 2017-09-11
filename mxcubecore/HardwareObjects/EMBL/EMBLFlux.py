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

import numpy
import gevent
import logging

from copy import copy
from scipy.interpolate import interp1d

from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLFlux(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.flux_value = None
        self.beam_info = None
        self.transmission = None
        self.ready_event = None
        self.intensity_measurements = []
        self.ampl_chan_index = None
        self.intensity_ranges = []
        self.intensity_value = None

        self.origin_flux_value = None
        self.origin_beam_info = None
        self.origin_transmission = None

        self.chan_intens_range = None
        self.chan_intens_mean = None
        self.cmd_set_intens_acq_time = None
        self.cmd_set_intens_range = None
        self.cmd_set_intens_resolution = None
     
        self.diode_calibration_amp_per_watt = interp1d(\
              [4., 6., 8., 10., 12., 12.5, 15., 16., 20., 30.],
              [0.2267, 0.2116, 0.1405, 0.086, 0.0484, 0.0469,
               0.0289, 0.0240, 0.01248, 0.00388])

        self.air_absorption_coeff_per_meter = interp1d(\
               [4., 6.6, 9.2, 11.8, 14.4, 17., 19.6, 22.2, 24.8, 27.4, 30],
               [9.19440446, 2.0317802, 0.73628084, 0.34554261,
                0.19176669, 0.12030697, 0.08331135, 0.06203213,
                0.04926173, 0.04114024, 0.0357374])
        self.carbon_window_transmission = interp1d(\
               [4., 6.6, 9.2, 11.8, 14.4, 17., 19.6, 22.2, 24.8, 27.4, 30],
               [0.74141, 0.93863, 0.97775, 0.98946, 0.99396,
                0.99599, 0.99701, 0.99759, 0.99793, 0.99815, 0.99828])
        self.dose_rate_per_10to14_ph_per_mmsq = interp1d(\
               [4., 6.6, 9.2, 11.8, 14.4, 17., 19.6, 22.2, 24.8, 27.4, 30.0],
               [459000., 162000., 79000., 45700., 29300., 20200.,
                14600., 11100., 8610., 6870., 5520.])

    def init(self):
        """Reads config xml, initiates all necessary hwobj, channels and cmds
        """
        self.ready_event = gevent.event.Event()

        self.intensity_ranges = []
        self.intensity_measurements = []

        try:
            for intens_range in self['intensity']['ranges']:
                temp_intens_range = {}
                temp_intens_range['max'] = intens_range.CurMax
                temp_intens_range['index'] = intens_range.CurIndex
                temp_intens_range['offset'] = intens_range.CurOffset
                self.intensity_ranges.append(temp_intens_range)
            self.intensity_ranges = sorted(self.intensity_ranges,
                                           key=lambda item: item['max'])
        except:
            logging.getLogger("HWR").error(\
               "BeamlineTest: No intensity ranges defined")

        self.chan_intens_mean = self.getChannelObject('intensMean')
        self.chan_intens_range = self.getChannelObject('intensRange')

        self.cmd_set_intens_resolution = \
            self.getCommandObject('setIntensResolution')
        self.cmd_set_intens_acq_time = \
            self.getCommandObject('setIntensAcqTime')
        self.cmd_set_intens_range = \
            self.getCommandObject('setIntensRange')

        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        self.connect(self.beam_info_hwobj,
                     "beamInfoChanged",
                     self.beam_info_changed)
        self.beam_info_changed(self.beam_info_hwobj.get_beam_info())

        self.transmission_hwobj = self.getObjectByRole("transmission")
        self.connect(self.transmission_hwobj,
                     "attFactorChanged",
                     self.transmission_changed)
        self.transmission_changed(self.transmission_hwobj.getAttFactor())

        if self.getProperty("defaultFlux") is not None:
            self.set_flux(self.getProperty("defaultFlux"))

    def beam_info_changed(self, beam_info):
        self.beam_info = beam_info
        self.update_flux_value()

    def transmission_changed(self, transmission):
        self.transmission = transmission
        self.update_flux_value()

    def set_flux(self, flux_value):
        self.flux_value = flux_value
        self.origin_flux_value = copy(flux_value)
        self.origin_beam_info = copy(self.beam_info)
        self.origin_transmission = copy(self.transmission)
        self.update_flux_value()

    def get_flux(self):
        return self.flux_value

    def update_flux_value(self):
        if self.flux_value is not None:
            if self.origin_transmission != self.transmission:
                self.flux_value = self.origin_flux_value * self.transmission / \
                                  self.origin_transmission
            if self.origin_beam_info != self.beam_info:
                if self.origin_beam_info['shape'] == 'ellipse':
                    original_area = 3.141592 * pow(self.origin_beam_info['size_x'] / 2, 2)
                else:     
                    original_area = self.original_beam_info['size_x'] * \
                                    self.original_beam_info['size_y']

                if self.beam_info['shape'] == 'ellipse':
                    current_area = 3.141592 * pow(self.beam_info['size_x'] / 2, 2)
                else:
                    current_area = self.beam_info['size_x'] * \
                                   self.beam_info['size_y']
                self.flux_value = self.origin_flux_value * current_area / \
                                  original_area   
            self.emit('fluxChanged', self.flux_value, self.beam_info, self.transmission)

    def measure_intensity(self):
        """Measures intesity"""

        # 1. close guillotine and fast shutter -------------------------------
        self.bl_hwobj.collect_hwobj.close_guillotine(wait=True)
        self.bl_hwobj.fast_shutter_hwobj.closeShutter(wait=True)
        gevent.sleep(0.1)

        #2. move back light in, check beamstop position ----------------------
        self.bl_hwobj.back_light_hwobj.move_in()

        beamstop_position = self.bl_hwobj.beamstop_hwobj.get_position()
        if beamstop_position == "BEAM":
            self.bl_hwobj.beamstop_hwobj.set_position("OFF")
            self.bl_hwobj.diffractometer_hwobj.wait_device_ready(30)

        #3. check scintillator position --------------------------------------
        scintillator_position = self.bl_hwobj.\
            diffractometer_hwobj.get_scintillator_position()
        if scintillator_position == "SCINTILLATOR":
            #TODO add state change when scintillator position changed
            self.bl_hwobj.diffractometer_hwobj.\
                 set_scintillator_position("PHOTODIODE")
            gevent.sleep(1)
            self.bl_hwobj.diffractometer_hwobj.\
                 wait_device_ready(30)

        #5. open the fast shutter --------------------------------------------
        self.bl_hwobj.fast_shutter_hwobj.openShutter(wait=True)
        gevent.sleep(0.3)

        #6. measure mean intensity
        self.ampl_chan_index = 0

        if True:
            intens_value = self.chan_intens_mean.getValue()
            intens_range_now = self.chan_intens_range.getValue()
            for intens_range in self.intensity_ranges:
                if intens_range['index'] is intens_range_now:
                    self.intensity_value = intens_value[self.ampl_chan_index] - \
                                           intens_range['offset']
                    break

        #7. close the fast shutter -------------------------------------------
        self.bl_hwobj.fast_shutter_hwobj.closeShutter(wait=True)

        # 7/7 set back original phase ----------------------------------------
        self.bl_hwobj.diffractometer_hwobj.set_phase(current_phase)

        #8. Calculate --------------------------------------------------------
        energy = self.bl_hwobj._get_energy()
        detector_distance = self.bl_hwobj.detector_hwobj.get_distance()
        beam_size = self.bl_hwobj.collect_hwobj.get_beam_size()
        transmission = self.bl_hwobj.transmission_hwobj.getAttFactor()

        meas_item = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                     "%.4f" % energy,
                     "%.2f" % detector_distance,
                     "%.2f x %.2f" % (beam_size[0], beam_size[1]),
                     "%.2f" % transmission]

        air_trsm = numpy.exp(-self.air_absorption_coeff_per_meter(energy) * \
             detector_distance / 1000.0)
        carb_trsm = self.carbon_window_transmission(energy)
        flux = 0.624151 * 1e16 * self.intensity_value / \
               self.diode_calibration_amp_per_watt(energy) / \
               energy / air_trsm / carb_trsm

        #GB correcting diode misscalibration!!!
        flux = flux * 1.8

        dose_rate = 1e-3 * 1e-14 * self.dose_rate_per_10to14_ph_per_mmsq(energy) * \
               flux / beam_size[0] / beam_size[1]

        self.bl_hwobj.collect_hwobj.machine_info_hwobj.\
           set_flux(flux, self.bl_hwobj.beam_info_hwobj.get_beam_info())

        msg = "Intensity = %1.1e A" % self.intensity_value
        logging.getLogger("user_level_log").info(msg)
        meas_item.append("%1.1e" % self.intensity_value)

        msg = "Flux = %1.1e photon/s" % flux
        logging.getLogger("user_level_log").info(msg)
        meas_item.append("%1.1e" % flux)

        msg = "Dose rate =  %1.1e KGy/s" % dose_rate
        logging.getLogger("user_level_log").info(msg)
        meas_item.append("%1.1e" % dose_rate)

        msg = "Time to reach 20 MGy = %d s = %d frames " % \
              (20000. / dose_rate, int(25 * 20000. / dose_rate))
        logging.getLogger("user_level_log").info(msg)
        meas_item.append("%d, %d frames" % \
              (20000. / dose_rate, int(25 * 20000. / dose_rate)))

        self.intensity_measurements.insert(0, meas_item)
        self.flux_value = flux

        self.ready_event.set()

        return meas_item
