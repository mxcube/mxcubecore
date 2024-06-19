import numpy as np
import logging
import time
import gevent
import gevent.event
import PyTango
from mxcubecore.HardwareObjects.abstract.AbstractFlux import AbstractFlux

"""You may need to import monkey when you test standalone"""
# from gevent import monkey
# monkey.patch_all(thread=False)


class BIOMAXFlux(AbstractFlux):
    def __init__(self, name):
        AbstractFlux.__init__(self, name)

        self.al_coeff = [
            2.70033918627e-07,
            -2.98687890398e-05,
            0.00123604226164,
            -0.0258445478508,
            0.443366527092,
            -1.88717819273,
            6.51896436249,
            -8.15712686311,
        ]

        self.sipha_coeff = [
            5.6946e-08,
            -7.20953e-06,
            0.000359681,
            -0.00844784,
            0.242434,
            -0.960961,
            4.52577,
            -7.00435,
        ]

        self.air_coeff = [
            -4.93236e-03,
            6.84953e-01,
            -35.9648,
            845.516,
            -8440.87,
            66209.7,
            -225579,
            309746,
        ]

        self.al_model = np.array(self.al_coeff)
        self.sipha_model = np.array(self.sipha_coeff)
        self.air_model = np.array(self.air_coeff)

        self.e = 1.6022e-16
        self.al_length = 1
        self.airsample_length = 0
        self.detdiode_length = 45.0

        self.detector_distance_hwobj = None
        self.energy_hwobj = None
        self.air_length = None
        self.energy = None
        self.bcu_transmission_hwobj = None
        self.shutter_hwobj = None
        self.shutter_state = None
        self.timeout = 10
        self.ori_motors = None
        self.ori_phase = None

        self.current_flux = 0.0
        self.flux_density = -1.0
        self.flux_density_energy = 0.0
        self.channel_value = 0.0
        self.check_beam_result = False
        self.flux_aem = None
        self.flux_aem_dev = None

    def init(self):
        super(BIOMAXFlux, self).init()
        self.logger = logging.getLogger("HWR")

        self.cmd_macro = self.get_command_object("calculate_flux_mxcube")
        self.cmd_macro.connect_signal("macroResultUpdated", self.macro_finished)

        self.check_beam_macro = self.get_command_object("checkbeam")
        # is the following really needed? mmm...
        self.check_beam_macro.connect_signal("macroResultUpdated", self.macro_finished)

        self._event = gevent.event.Event()
        self.detector_distance_hwobj = self.get_object_by_role("detector_distance")
        self.energy_hwobj = self.get_object_by_role("energy")
        self.connect(self.energy_hwobj, "energyChanged", self.energy_changed)
        self.bcu_transmission_hwobj = self.get_object_by_role("transmission")
        self.shutter_hwobj = self.get_object_by_role("shutter")
        self.diffractometer_hwobj = self.get_object_by_role("diffractometer")
        self.detector_cover_hwobj = self.get_object_by_role("detector_cover")
        self.beam_info_hwobj = self.get_object_by_role("beam_info")

        self.air_length = (
            self.detector_distance_hwobj.get_value() * 1000 + self.airsample_length
        )
        self.flux_aem = self.get_property("flux_aem", None)
        if self.flux_aem is not None:
            self.flux_aem_dev = PyTango.DeviceProxy(self.flux_aem)

    def macro_finished(self, *args):
        # listen to door.result once the macro finishes execution
        # in this case, checkbeam returns True/false and calculate_flux Float
        self.macro_result = args[0]
        try:
            self.channel_value = float(self.macro_result)
        except:
            # string result
            self.check_beam_result = self.macro_result
        # self.logger.info("New channel value: %s" %str(self.channel_value))
        self._event.set()

    def acquire(self):
        time.sleep(0.1)
        self._event.clear()
        self.cmd_macro()
        self._event.wait()

    def check_beam(self):
        # checks if beam is stable
        time.sleep(0.1)
        self._event.clear()
        self.check_beam_macro()
        self._event.wait()

    def get_flux(self):
        return self.current_flux

    def calculate_flux(self):
        """
        calculate the current flux, complete version
         1. Close fast shutter
         2. Open safety shutter (if closed)
         3. Check beam stability
          If beam stable:
         4. Set MD3 phase and beamstop and motor positions
         5. Ensure detector cover is closed
         6. Measure flux value (sardana macro call and some math)
         7. Put MD3 back to normal position
        """
        energy = self.energy_hwobj.get_current_energy()
        transmission = self.bcu_transmission_hwobj.get_att_factor()
        self.check_beam_result = False
        self.logger.info("Flux calculation started!")

        # close fast shutter
        try:
            self.diffractometer_hwobj.close_fast_shutter()
            self.logger.info("Fast shutter closed!")
        except Exception as ex:
            self.logger.error("Cannot close fast shutter! %s", str(ex))
            return

        # open safety shutter
        try:
            self.shutter_state = self.shutter_hwobj.readShutterState()
            if self.shutter_state != "opened":
                self.shutter_hwobj.openShutter()
                self.wait_safety_shutter_open()
                self.logger.info("Safety shutter open!")
        except Exception as ex:
            self.logger.error("Cannot close shutter! %s", str(ex))
            return

        # checkbeam macro, it returns T/F
        try:
            self.check_beam()
        except Exception as ex:
            self.logger.error("ERROR Checking beam! %s", str(ex))
            return

        if self.check_beam_result == "False":
            self.logger.error("Beam is not stable")
            return

        # set MD3 phase
        try:
            (
                self.ori_motors,
                self.ori_phase,
            ) = self.diffractometer_hwobj.set_calculate_flux_phase()
        except Exception as ex:
            self.logger.error("Cannot set MD3 phase for flux calculatio! %s", str(ex))
            return

        # check detector cover is closed
        try:
            if self.detector_cover_hwobj.readShutterState() == "opened":
                logging.getLogger("HWR").info("Closing the detector cover")
                self.detector_cover_hwobj.closeShutter()
        except:
            logging.getLogger("HWR").exception("Could not close the detector cover")
            return

        # get_instant_flux
        try:
            self.current_flux = self.get_instant_flux()
        except Exception as ex:
            self.logger.error("ERROR acquiring! %s", str(ex))

        try:
            self.diffractometer_hwobj.close_fast_shutter()
            self.logger.info("Fast shutter closed!")
        except Exception as ex:
            self.logger.error("Cannot close fast shutter! %s", str(ex))

        self.diffractometer_hwobj.finish_calculate_flux(self.ori_motors, self.ori_phase)

    def wait_safety_shutter_open(self):
        with gevent.Timeout(
            10, RuntimeError("Timeout waiting for safety shutter open")
        ):
            while self.shutter_hwobj.readShutterState() != "opened":
                gevent.sleep(0.2)

    def wait_fast_shutter_open(self, timeout=5):
        with gevent.Timeout(
            timeout, RuntimeError("Timeout waiting for safety shutter open")
        ):
            while not self.diffractometer_hwobj.is_fast_shutter_open():
                gevent.sleep(0.2)

    def flux_value_changed(self):
        try:
            self.update_flux_density()
            self.emit("valueChanged", (self.current_flux))
        except e:
            print(e)

    def transmit(self, length, energy, model):
        att_l = (
            model[0] * energy**7
            + model[1] * energy**6
            + model[2] * energy**5
            + model[3] * energy**4
            + model[4] * energy**3
            + model[5] * energy**2
            + model[6] * energy
            + model[7]
        )
        transmission = np.exp(-length / att_l)
        return transmission

    def si_diode_flux(self, current, transmission, absorption, energy):
        sipha_absorp = absorption
        epsilon = 3.66e-3

        if abs(self.e * energy * sipha_absorp * transmission) == 0:
            return 0
        else:
            flux = current * epsilon / (self.e * energy * sipha_absorp * transmission)
            return float(flux)

    def get_value(self):
        return self.current_flux

    def get_instant_flux(self):
        flux = self._get_instant_flux()
        # if flux is 0, remeasure it
        if float(flux) < 1:
            flux = self._get_instant_flux()
        return flux

    def _get_instant_flux(self):
        """
        calculate the current flux, a simpler and faster version
         - assuming safety shutter is open
         - no check of beam stability
        """
        energy = self.energy_hwobj.get_current_energy()
        transmission = self.bcu_transmission_hwobj.get_att_factor()

        self.logger.info("Start to measure flux")
        try:
            self.acquire()
            current_offset = self.channel_value
        except Exception as ex:
            self.logger.error("ERROR reading offset! %s", str(ex))
            return -101

        self.logger.info("Current Offset: {}".format(current_offset))

        try:
            self.diffractometer_hwobj.open_fast_shutter()
            self.wait_fast_shutter_open()
            self.logger.info("Fast shutter opened!")
        except Exception as ex:
            self.logger.error("Cannot open fast shutter! %s", str(ex))
            return -102

        time.sleep(2)
        try:
            self.acquire()
        except Exception as ex:
            self.logger.error("ERROR Acquiring! %s", str(ex))
            self.diffractometer_hwobj.close_fast_shutter()
            return -103
        self.diffractometer_hwobj.close_fast_shutter()
        current_meas = self.channel_value
        self.logger.info("Current Measurement: {}".format(current_meas))

        current = current_meas - current_offset

        air_length = (
            self.detector_distance_hwobj.get_value() * 1000 + self.airsample_length
        )
        total_transmission = self.transmit(
            self.al_length, energy, self.al_model
        ) * self.transmit(air_length, energy, self.air_model)

        sipha_absorp = 1 - self.transmit(self.detdiode_length, energy, self.sipha_model)

        flux = self.si_diode_flux(current, total_transmission, sipha_absorp, energy)

        if flux < 0:
            flux = 0
        # multiply the flux value by 1000 due to some issue with AlbaEM
        flux = flux * 1000
        if flux < 50000000:
            flux = 0
        self.current_flux = flux  # "{:.2E}".format(flux)
        self.flux_value_changed()
        self.logger.info("Flux Measurement: {}".format(flux))
        return flux  # "{:.2E}".format(flux)

    def energy_changed(self, en, wl):
        self.flux_density = -1.0

    def update_flux_density(self):
        try:
            beamx, beamy = self.beam_info_hwobj.get_beam_size()  # in mm, float
            transmission = self.bcu_transmission_hwobj.get_att_factor()  # string
            self.flux_density = (
                float(self.current_flux) / float(transmission) / beamx / beamy / 10000
            )
            self.flux_density_energy = self.energy_hwobj.get_current_energy()
        except Exception as ex:
            self.current_flux = -1.0
            self.flux_density = -1.0
            self.logger.error("ERROR calculating flux density %s", str(ex))

    def get_average_flux_density(self, transmission=None):
        flux_at_100 = self.flux_density
        if flux_at_100 < 0:
            return None
        ref_transmission = transmission or HWR.beamline.transmission.get_value()
        return flux_at_100 * ref_transmission / 100.0

    def estimate_flux(self):
        """
        flux estimation based on BCU. Derived from the biomax macro which estimates the flux from
        the intensity readings of the BCU XBPM 1 (xbpm/01/S) does not take into account the MD3 apertures,
        so the flux at the sample will be less.
        as it's before the attenuator, so transmission is 100%
        """
        energy = self.energy_hwobj.get_current_energy()
        energy_ev = energy * 1000

        if self.flux_aem_dev is None:
            msg = (
                "Error: AEM for esitmating flux is not defined or cannot connect to it"
            )
            self.logger.error(msg)
            raise Exception(msg)
        else:
            current = self.flux_aem_dev.S
        flux = (
            current
            * (2.70541e-06 * energy_ev * energy_ev - 0.00978719 * energy_ev - 30.1795)
            * 7.96e14
        )

        self.logger.info("Estimated flux at %s: %1.3e photons/s", self.flux_aem, flux)
        return flux
