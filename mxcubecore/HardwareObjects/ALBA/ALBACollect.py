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
ALBACollect
"""
import os
import logging
import gevent
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractCollect import AbstractCollect


__author__ = "Vicente Rey Bakaikoa"
__credits__ = ["MXCuBE colaboration"]
__version__ = "2.2."


class ALBACollect(AbstractCollect, HardwareObject):
    """Main data collection class. Inherited from AbstractMulticollect
       Collection is done by setting collection parameters and 
       executing collect command  
    """
    def __init__(self, name):
        """

        :param name: name of the object
        :type name: string
        """

        AbstractCollect.__init__(self)
        HardwareObject.__init__(self, name)

        self.ready_event = None

        self.diffractometer_hwobj = None
        self.omega_hwobj = None
        self.lims_client_hwobj = None
        self.machine_info_hwobj = None
        self.energy_hwobj = None
        self.resolution_hwobj = None
        self.transmission_hwobj = None
        self.detector_hwobj = None
        self.beam_info_hwobj = None
        self.autoprocessing_hwobj = None
        self.graphics_manager_hwobj = None

        self.helical_positions = None

        self.saved_omega_velocity = None

    def init(self):
        """
        Init method
        """

        self.ready_event = gevent.event.Event()

        self.supervisor_hwobj = self.getObjectByRole("supervisor")

        self.fastshut_hwobj = self.getObjectByRole("fast_shutter")
        self.slowshut_hwobj = self.getObjectByRole("slow_shutter")
        self.photonshut_hwobj = self.getObjectByRole("photon_shutter")
        self.frontend_hwobj = self.getObjectByRole("frontend")

        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")
        self.omega_hwobj = self.getObjectByRole("omega")
        self.lims_client_hwobj = self.getObjectByRole("lims_client")
        self.machine_info_hwobj = self.getObjectByRole("machine_info")
        self.energy_hwobj = self.getObjectByRole("energy")
        self.resolution_hwobj = self.getObjectByRole("resolution")
        self.transmission_hwobj = self.getObjectByRole("transmission")
        self.detector_hwobj = self.getObjectByRole("detector")
        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        self.autoprocessing_hwobj = self.getObjectByRole("auto_processing")
        self.graphics_manager_hwobj = self.getObjectByRole("graphics_manager")

        self.ni_conf_cmd = self.getCommandObject("ni_configure")
        self.ni_unconf_cmd = self.getCommandObject("ni_unconfigure")

        undulators = []
        try:
            for undulator in self["undulators"]:
                undulators.append(undulator)
        except:
            pass

        self.exp_type_dict = {'Mesh': 'raster',
                              'Helical': 'Helical'}

        det_px, det_py = self.detector_hwobj.get_pixel_size()

        self.set_beamline_configuration(\
             synchrotron_name="ALBA",
             directory_prefix=self.getProperty("directory_prefix"),
             default_exposure_time=self.detector_hwobj.get_default_exposure_time(),
             minimum_exposure_time=self.detector_hwobj.get_minimum_exposure_time(),
             detector_fileext=self.detector_hwobj.get_file_suffix(),
             detector_type=self.detector_hwobj.get_detector_type(),
             detector_manufacturer=self.detector_hwobj.get_manufacturer(),
             detector_model=self.detector_hwobj.get_model(),
             detector_px=det_px,
             detector_py=det_py,
             undulators=undulators,
             focusing_optic=self.getProperty('focusing_optic'),
             monochromator_type=self.getProperty('monochromator'),
             beam_divergence_vertical=self.beam_info_hwobj.get_beam_divergence_hor(),
             beam_divergence_horizontal=self.beam_info_hwobj.get_beam_divergence_ver(),
             polarisation=self.getProperty('polarisation'),
             input_files_server=self.getProperty("input_files_server"))

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))

    def data_collection_hook(self):
        """Main collection hook
        """

        logging.getLogger("HWR").info( "Running ALBA data collection hook" )

        if self.aborted_by_user:
            self.emit_collection_failed("Aborted by user")
            self.aborted_by_user = False
            return

        osc_seq = self.current_dc_parameters['oscillation_sequence'][0]

        ready = self.prepare_collection()

        if not ready:
            self.data_collection_failed()
            return

        #
        # Run
        #
        self.configure_ni(self.current_dc_parameters)

        self.detector_hwobj.start_collection(self.current_dc_parameters)

        self.omega_hwobj.moveRelative(osc_seq['range'])
        self.omega_hwobj.wait_end_of_move(timeout=100)

        self.data_collection_end()

    def prepare_collection(self):

        osc_seq = self.current_dc_parameters['oscillation_sequence'][0]
        fileinfo = self.current_dc_parameters['fileinfo']

        basedir = fileinfo['directory']

        #  save omega velocity
        self.saved_omega_velocity = self.omega_hwobj.get_velocity()

        # create directories if needed
        self.check_directory(basedir)

        # check fast shutter closed. others opened
        shutok = self.check_shutters()

        if not shutok:
            logging.getLogger("HWR").info(" Shutters not ready")
            return False

        # go to collect phase
        if not self.is_collect_phase():
            logging.getLogger("HWR").info(" Not in collect phase. Asking supervisor to go")
            success = self.go_to_collect()
            if not success:
                logging.getLogger("HWR").info("Cannot set COLLECT phase")
                return False

        # move omega to start angle
        start_angle = osc_seq['start']

        nb_images = osc_seq['number_of_images']
        img_range = osc_seq['range']
        exp_time = osc_seq['exposure_time']

        total_dist = nb_images * img_range
        omega_speed = float( total_dist / exp_time)

        self.omega_hwobj.set_velocity(60)

        omega_acceltime = self.omega_hwobj.get_acceleration()

        safe_delta =  3.0 * omega_speed * omega_acceltime

        init_pos = start_angle - safedelta
        self.final_pos = start_angle + total_dist + safe_delta

        self.omega_hwobj.move(init_pos)

        detok = self.detector_hwobj.prepare_collection(self.current_dc_parameters)

        self.omega_hwobj.wait_end_of_move(timeout=10)

        # program omega speed depending on exposure time
        self.omega_hwobj.set_velocity(omega_speed)
        if omega_speed != 0:
            self.configure_ni(start_angle, total_dist)
     
        return detok

    def check_shutters(self):

        # Check fast shutter
        if self.fastshut_hwobj.getState() != 0:
            return False

        # Check slow shutter
        if self.slowshut_hwobj.getState() != 1:
            return False

        # Check photon shutter
        if self.photonshut_hwobj.getState() != 1:
            return False

        # Check front end
        if self.frontend_hwobj.getState() != 1:
            return False

        return True

    def data_collection_end(self):
        # 
        # data collection end (or abort)
        #  
        self.fastshut_hwobj.cmdOut()

        self.detector_hwobj.stop_collection()

        self.omega_hwobj.stop()
        self.omega_hwobj.set_velocity(self.saved_omega_velocity)

        self.unconfigure_ni()

    def check_directory(self, basedir):
        if not os.path.exists(basedir):
            try:
                os.makedirs(basedir)
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise

    def collect_finished(self, green):
        logging.info("Data collection finished")

    def collect_failed(self, par):
        logging.exception("Data collection failed")
        self.current_dc_parameters["status"] = 'failed'
        exc_type, exc_value, exc_tb = sys.exc_info()
        failed_msg = 'Data collection failed!\n%s' % exc_value
        self.emit("collectOscillationFailed", (owner, False, failed_msg,
           self.current_dc_parameters.get('collection_id'), 1))

    def go_to_collect(self):
        self.supervisor_hwobj.go_collect()

        while True:
            super_state = str(self.supervisor_hwobj.get_state()).upper()
            if super_state != "MOVING":
                break
            gevent.sleep(0.2)

        return self.is_collect_phase()

    def is_collect_phase(self):
        return self.supervisor_hwobj.get_current_phase() == "COLLECT" 

    def configure_ni(self, startang, total_dist):
        self.ni_conf_cmd(0.0, startang, total_dist,0, 1)

    def unconfigure_ni(self):
        self.ni_unconf_cmd()

    def open_safety_shutter(self):
        """ implements prepare_shutters in collect macro """ 

        # prepare ALL shutters

           # close fast shutter
        if self.fastshut_hwobj.getState() != 0:
            self.fastshut_hwobj.close()

           # open slow shutter
        if self.slowshut_hwobj.getState() != 1:
            self.slowshut_hwobj.open()

           # open photon shutter
        if self.photonshut_hwobj.getState() != 1:
            self.photonshut_hwobj.open()

           # open front end
        if self.frontend_hwobj.getState() != 0:
            self.frontend_hwobj.open()

    def open_detector_cover(self):
        self.supervisor_hwobj.open_detector_cover()

    def open_fast_shutter(self):
        # self.fastshut_hwobj.open()
        #   this function is empty for ALBA. we are not opening the fast shutter.
        #   on the contrary open_safety_shutter (equivalent to prepare_shutters in original
        #   collect macro will first close the fast shutter and open the other three
        pass
            
    def close_fast_shutter(self):
        self.fastshut_hwobj.cmdOut()

    def close_safety_shutter(self):
        #  we will not close safety shutter during collections
        pass

    def close_detector_cover(self):
        #  we will not close detcover during collections
        #  self.supervisor.close_detector_cover()
        pass

    def set_helical_pos(self, arg):
        """
        Descript. : 8 floats describe
        p1AlignmY, p1AlignmZ, p1CentrX, p1CentrY
        p2AlignmY, p2AlignmZ, p2CentrX, p2CentrY               
        """
        self.helical_positions = [arg["1"]["phiy"],  arg["1"]["phiz"], 
                             arg["1"]["sampx"], arg["1"]["sampy"],
                             arg["2"]["phiy"],  arg["2"]["phiz"],
                             arg["2"]["sampx"], arg["2"]["sampy"]]

    def setMeshScanParameters(self, num_lines, num_images_per_line, mesh_range):
        """
        Descript. : 
        """
        pass

    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. : 
        """
        self.graphics_manager_hwobj.save_scene_snapshot(filename)

    def set_energy(self, value):
        """
        Descript. : 
        """
        #   program energy 
        #   prepare detector for diffraction
        self.energy_hwobj.move_energy(value)

    def set_wavelength(self, value):
        """
        Descript. : 
        """
        #   program energy 
        #   prepare detector for diffraction
        self.energy_hwobj.move_wavelength(value)

    def get_energy(self):
        return self.energy_hwobj.get_energy()

    def set_transmission(self, value):
        """
        Descript. : 
        """
        self.transmission_hwobj.set_value(value)

    def set_resolution(self, value):
        """
        Descript. : resolution is a motor in out system
        """
        self.resolution_hwobj.move(value)

    def move_detector(self,value):
        self.detector_hwobj.move_distance(value)

    @task 
    def move_motors(self, motor_position_dict):
        """
        Descript. : 
        """        
        self.diffractometer_hwobj.move_motors(motor_position_dict)

    def prepare_input_files(self):
        """
        Descript. : 
        """
        i = 1
        log = logging.getLogger("user_level_log")
        while True:
            xds_input_file_dirname = "xds_%s_%s_%d" % (\
                self.current_dc_parameters['fileinfo']['prefix'],
                self.current_dc_parameters['fileinfo']['run_number'],
                i)
            xds_directory = os.path.join(\
                self.current_dc_parameters['fileinfo']['process_directory'],
                xds_input_file_dirname)
            if not os.path.exists(xds_directory):
                break
            i += 1
        self.current_dc_parameters["xds_dir"] = xds_directory

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (\
                self.current_dc_parameters['fileinfo']['prefix'],
                self.current_dc_parameters['fileinfo']['run_number'],
                i)
        mosflm_directory = os.path.join(\
                self.current_dc_parameters['fileinfo']['process_directory'],
                mosflm_input_file_dirname)

        log.info("  - xds: %s / mosflm: %s" % (xds_directory, mosflm_directory))
        return xds_directory, mosflm_directory, ""


    def get_wavelength(self):
        """
        Descript. : 
            Called to save wavelength in lims
        """
        if self.energy_hwobj is not None:
            return self.energy_hwobj.get_wavelength()

    def get_detector_distance(self):
        """
        Descript. : 
            Called to save detector_distance in lims
        """
        if self.detector_hwobj is not None:	
            return self.detector_hwobj.get_distance()

    def get_resolution(self):
        """
        Descript. : 
            Called to save resolution in lims
        """
        if self.resolution_hwobj is not None:
            return self.resolution_hwobj.getPosition()

    def get_transmission(self):
        """
        Descript. : 
            Called to save transmission in lims
        """
        if self.transmission_hwobj is not None:
            return self.transmission_hwobj.getAttFactor()

    def get_undulators_gaps(self):
        """
        Descript. : return triplet with gaps. In our case we have one gap, 
                    others are 0        
        """
        #TODO 
        try:
            if self.chan_undulator_gap:
                und_gaps = self.chan_undulator_gap.getValue()
                if type(und_gaps) in (list, tuple):
                    return und_gaps
                else: 
                    return (und_gaps)
        except:
            pass
        return {} 

    def get_beam_size(self):
        """
        Descript. : 
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_beam_size()

    def get_slit_gaps(self):
        """
        Descript. : 
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_slits_gap()
        return None,None

    def get_beam_shape(self):
        """
        Descript. : 
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_beam_shape()
    
    def get_measured_intensity(self):
        """
        Descript. : 
        """
        flux = 0.0
        return float("%.3e" % flux)

    def get_machine_current(self):
        """
        Descript. : 
        """
        if self.machine_info_hwobj:
            return self.machine_info_hwobj.get_current()
        else:
            return 0

    def get_machine_message(self):
        """
        Descript. : 
        """
        if self.machine_info_hwobj:
            return self.machine_info_hwobj.get_message()
        else:
            return ''

    def get_machine_fill_mode(self):
        """
        Descript. : 
        """
        if self.machine_info_hwobj:
            return "FillMode not/impl"
            #fill_mode = str(self.machine_info_hwobj.get_message()) 
            #return fill_mode[:20]
        else:
            return ''

    def get_flux(self):
        """
        Descript. : 
        """
        return self.get_measured_intensity()


    def trigger_auto_processing(self):
        pass

def test_hwo(hwo):
    #print "Energy: ",hwo.set_energy(7.75)
    #print "Transm: ",hwo.set_transmission(100)
    #print "Resol: ",hwo.set_resolution(4.07929)
    print "Energy: ",hwo.get_energy()
    print "Transm: ",hwo.get_transmission()
    print "Resol: ",hwo.get_resolution()
    print "Shutters (ready for collect): ",hwo.check_shutters()
    print "Supervisor(collect phase): ",hwo.is_collect_phase()

