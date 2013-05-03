 # -*- coding: latin-1 -*-
"""
 Abstract base classes for mxCuBE related hardware objects.
"""

import abc
    
class AbstractEnergyScan(object):
    """
    """

    __metaclass__ = abc.ABCMeta

    
    @abc.abstractmethod
    def isSpecConected(self):
        """
        :returns: True if spec false otherwise.
        :rtype: bool
        """
        return

    
    @abc.abstractmethod
    def resolution_position_changed(self, res):
        """
        TODO: Verify this documentation.
        :param res: Resolution in ångström.
        :type res: float
        """
        return
    

    @abc.abstractmethod
    def energy_state_changed(self, state):
        """
        :param state: Motor state one of, NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT
        
        :returns: 
        :rtype: float

        """
        return


    @abc.abstractmethod
    def s_connected(self):
        """
        Spec specific method. Handles the connection to spec.
        Emits the signal "connected" when ready.
        """
        return


    @abc.abstractmethod
    def s_disconected(self):
        """
        Spec specific method, handles spec dissconnect.
        Emits the signal "disconnected". 
        """
        return

    
    @abc.abstractmethod
    def can_scan_energy(self):
        """
        :rtype: bool
        """
        return


    @abc.abstractmethod
    def start_energy_scan(self, element, edge, directory, 
                          prefix, session_id, blsample_id):
        """
        Starts an energy scan.
        Emits the signal "scanStatusChanged", with a status message.

        :param element: Element symbol, defined in the device configuration xml file. See the example energyscan.xml for more information.
        :type element: str
        
        :param edge: Energy, ie 'K'. See example device xml file for more information.
        :type edge: str
        
        :param directory: 
        :type directory: str
        
        :param prefix:
        :type prefix: str
        
        :param session_id: 
        :type session_id: str
        
        :param blsample_id: 
        :type blsample_id: int

        :returns: True if it was possible to start the scan, false otherwise.
        :rtype: bool
        """
        return

    
    @abc.abstractmethod
    def cancel_energy_scan(self):
        return


    @abc.abstractmethod
    def scan_command_ready(self):
        """ Emits the signal "energyScanReady" with the argument True, 
        if the device is not scanning. """
        return


    @abc.abstractmethod
    def scan_command_not_ready(self):
        """ Emits the signal "energyScanReady" with the argument False, 
        if the device is not scanning """
        return


    @abc.abstractmethod
    def scan_command_failed(self):
        """
        Stores the current energyscan and emits the signal
        "energyScanFaild".
        """
        return


    @abc.abstractmethod
    def scan_command_aborted(self):
        return

    
    @abc.abstractmethod
    def scan_command_finished(self, result):
        """
        Emits the signal "energyScanFinished" with the list of result 
        parameters as argument.

        :param result: List of result parameters.
        """
        return


    @abc.abstractmethod
    def do_chooch(self, scan_object, elt, edge, 
                  scan_archive_file_prefix, scan_file_prefix):
        """
        Extract some signal parameters using chooch.
        """
        return


    @abc.abstractmethod
    def scan_status_changed(self, status):
        """
        Emits the signal "scanStatusChanged" with the argument status.
       
        :param status: str
        """
        return


    @abc.abstractmethod
    def store_energy_scan(self):
        """
        Stores the result parameters in ISPyB.
        """
        return
    

    @abc.abstractmethod
    def update_energy_scan(self, scan_id, jpeg_scan_filename):
        return


    @abc.abstractmethod
    def can_move_energy(self):
        """
        :rtype: bool
        """
        return


    @abc.abstractmethod
    def get_current_energy(self):
        """
        :rtype: float
        """
        return


    @abc.abstractmethod
    def get_current_wavelength(self):
        """
        :rtype: float
        """
        return


    @abc.abstractmethod
    def get_wavelength_limits(self):
        """
        :rtype: float
        """
        return

    
    @abc.abstractmethod
    def start_move_energy(self, value):
        """
        Moves energy to specefied value.

        :param value: Energy to move to.
        :type value: float

        :rtype: bool
        """
        return


    @abc.abstractmethod
    def start_move_wavelength(self, value):
        """
        Calculates corresponding energy from the given wavelength and 
        calls :func:`start_move_energy`.

        :param value: Wavelength
        :type value: float

        """
        return

    
    @abc.abstractmethod
    def cancel_move_energy(self):
        return


    @abc.abstractmethod
    def energy_2_wavelength(self, val):
        """
        Calculates the wavelength from the given energy.

        :param val: The energy.
        :type val: float

        :returns: A wavelength.
        :rtype: float
        """

        return


    @abc.abstractmethod
    def energy_position_changed(self, pos):
        return


    @abc.abstractmethod
    def energy_limits_changed(self, limits):
        """
        Emits the signal "wavelengthLimitsChanged" with the wavelength limits
        as arguments.
        """
        return


    @abc.abstractmethod
    def move_energy_cmd_ready(self):
        return


    @abc.abstractmethod
    def move_energy_cmd_not_ready(self):
        return


    @abc.abstractmethod
    def move_energy_cmd_started(self):
        return


    @abc.abstractmethod
    def move_energy_cmd_ready(self):
        return


    @abc.abstractmethod
    def move_energy_cmd_not_ready(self):
        return


    @abc.abstractmethod
    def move_energy_cmd_started(self):
        return


    @abc.abstractmethod
    def move_energy_cmd_failed(self):
        return


    @abc.abstractmethod
    def move_energy_cmd_aborted(self):
        return


    @abc.abstractmethod
    def move_energy_cmd_finished(self, result):
        return


    @abc.abstractmethod
    def get_previous_resolution(self):
        return


    @abc.abstractmethod
    def restore_resolution(self):
        return


    @abc.abstractmethod
    def get_elements(self):
        return


    @abc.abstractmethod
    def get_default_mad_energies(self):
        return


class AbstractMicrodiffApertureAlign(object):
    """
    
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def move_to_position(self, name):
        return


    @abc.abstractmethod    
    def connect_notify(self, signal):
        return


    @abc.abstractmethod
    def equipment_not_ready(self, *args):
        return


    @abc.abstractmethod
    def is_ready(self):
        return


    @abc.abstractmethod
    def get_state(self):
        return


    @abc.abstractmethod
    def get_position(self):
        return


    @abc.abstractmethod
    def check_position(self, pos, no_emit):
        return

    
    @abc.abstractmethod
    def set_new_positions(self, name, new_positions):
        return

    
    @abc.abstractmethod
    def set_roles(self):
        return

    
class AbstarctMicrodiffAperture(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def sort_predefined_positions_list(self):
        return


    @abc.abstractmethod
    def connect_notify(self):
        return


    @abc.abstractmethod
    def get_limits(self):
        return

    
    @abc.abstractmethod
    def get_predefined_positions_list(self):
        return


    @abc.abstractmethod
    def motor_position_changed(self, absolute_position, private):
        return


    @abc.abstractmethod
    def get_current_position_name(self, pos):
        return


    @abc.abstractmethod
    def move_to_position(self, position_name):
        return


    @abc.abstractmethod
    def set_new_predefined_position(self, position_name, position_offset):
        return


class MicrodiffBeamstop(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def move_to_position(self, name):
        return


    @abc.abstractmethod
    def connect_notify(self, signal):
        return


    @abc.abstractmethod
    def equipment_ready(self, *args):
        return


    @abc.abstractmethod
    def equipment_not_ready(self, *args):
        return

    
    @abc.abstractmethod
    def is_ready(self):
        return


    @abc.abstractmethod
    def get_state(self):
        return

    
    @abc.abstractmethod
    def get_position(self):
        return

    
    @abc.abstractmethod
    def check_position(self, pos, no_emit):
        return


    @abc.abstractmethod
    def set_new_psoition(self, name, new_position):
        return

    
    @abc.abstractmethod
    def get_roles(self):
        return

class AbstractMicrodiffCamera(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def take_snapshot(self, *args):
        return


class AbstractMicrodiffHolderlength(object):
    """
    """

    __metaclass__ = abc.ABCMeta

    
    @abc.abstractmethod
    def offset_changed(self, new_offset):
        return


    @abc.abstractmethod
    def motor_position_changed(self, absolute_position, private):
        return


    @abc.abstractmethod
    def get_position(self):
        return


    @abc.abstractmethod
    def move(self, absolute_position):
        return


class AbstractMicrodiffLight(object):
    """
    """


    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def __init__(self, name):
        return


    @abc.abstractmethod
    def connect_notify(self, signal):
        return


    @abc.abstractmethod
    def update_state(self):
        return


    @abc.abstractmethod
    def global_state_changed(self, state):
        return

    
    @abc.abstractmethod
    def motor_state_changed(self, state):
        return


    @abc.abstractmethod
    def get_state(self):
        return


    @abc.abstractmethod
    def motor_limits_changed(self):
        return


    @abc.abstractmethod
    def get_limits(self):
        return

    
    @abc.abstractmethod
    def motor_position_changed(self, absolute_position, private):
        return


    @abc.abstractmethod
    def get_position(self):
        return


    @abc.abstractmethod
    def move(self, absolute_position):
        return

    
    @abc.abstractmethod
    def move_relative(self, relative_position):
        return


    @abc.abstractmethod
    def sync_move(self, position):
        return


    @abc.abstractmethod
    def sync_move_relative(self, position):
        return

    
    @abc.abstractmethod
    def get_motor_mnemonic(self):
        return


    @abc.abstractmethod
    def stop(self):
        return


class AbstractMicrodiffMotor(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def connect_notify(self, signal):
        return


    @abc.abstractmethod
    def update_state(self):
        return


    @abc.abstractmethod
    def global_state_changed(self, motor_states):
        return


    @abc.abstractmethod
    def get_state(self):
        return


    @abc.abstractmethod
    def motor_limits_changed(self):
        return

    
    @abc.abstractmethod
    def get_limits(self):
        return


    @abc.abstractmethod
    def motor_position_changed(self):
        return

    
    @abc.abstractmethod
    def get_position(self):
        return


    @abc.abstractmethod
    def get_dial_position(self):
        return


    @abc.abstractmethod
    def move(self, absolute_position):
        return


    @abc.abstractmethod
    def move_relative(self, relative_position):
        return


    @abc.abstractmethod
    def sync_move(self, position, timeout):
        return

    
    @abc.abstractmethod
    def motor_is_moving(self):
        return


    @abc.abstractmethod
    def sync_move_relative(self, position, timeout):
        return

    
    @abc.abstractmethod
    def get_motor_mnemonic(self):
        return

    
    @abc.abstractmethod
    def top(self):
        return


class AbstractMicroDiff(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def __init__(self, *args):
        return


    @abc.abstractmethod
    def is_ready(self):
        return


    @abc.abstractmethod
    def equipment_ready(self):
        return


    @abc.abstractmethod
    def equipment_not_ready(self):
        return


    @abc.abstractmethod
    def phi_motor_state_changed(self, state):
        return

    
    @abc.abstractmethod
    def phiz_motor_state_changed(self, state):
        return


    @abc.abstractmethod
    def phiy_motor_state_changed(self, state):
        return


    @abc.abstractmethod
    def get_calibration_data(self, offset):
        return


    @abc.abstractmethod
    def zoom_motor_predefined_position_changed(self, position_name, offset):
        return


    @abc.abstractmethod
    def zoom_motor_state_changed(self, state):
        return


    @abc.abstractmethod
    def sample_x_motor_state_changed(self, state):
        return


    @abc.abstractmethod
    def sample_y_motor_state_changed(self, state):
        return

    
    @abc.abstractmethod
    def invalidate_centering(self):
        return

    
    @abc.abstractmethod
    def phiz_motor_moved(self, pos):
        return

    
    @abc.abstractmethod
    def phiy_motor_moved(self, pos):
        return
    

    @abc.abstractmethod
    def sample_x_motor_moved(self, pos):
        return


    @abc.abstractmethod
    def sample_y_motor_moved(self, pos):
        return


    @abc.abstractmethod
    def sample_changer_sample_is_loaded(self, state):
        return


    @abc.abstractmethod
    def move_to_beam(self, x, y):
        return


    @abc.abstractmethod
    def get_available_centering_methods(self):
        return


    @abc.abstractmethod
    def start_centering_method(self, method, sample_info):
        return


    @abc.abstractmethod
    def cancel_centering_method(self, reject):
        return


    @abc.abstractmethod
    def current_centering_method(self):
        return


    @abc.abstractmethod
    def start_3_click_centering(self, sample_info):
        return


    @abc.abstractmethod
    def start_move_to_beam_centering(self, sample_info):
        return


    @abc.abstractmethod
    def start_auto_centering(self, sample_info, loop_only):
        return

    
    @abc.abstractmethod
    def image_clicked(self, x, y, xi, yi):
        return


    @abc.abstractmethod
    def emit_centring_started(self, method, flexible):
        return


    @abc.abstractmethod
    def accept_centring(self):
        return


    @abc.abstractmethod
    def reject_centring(self):
        return


    @abc.abstractmethod
    def emit_centring_moveing(self):
        return


    @abc.abstractmethod
    def emit_centring_failed(self):
        return


    @abc.abstractmethod
    def emit_centring_successful(self):
        return


    @abc.abstractmethod
    def emit_progress_message(self, msg):
        return


    @abc.abstractmethod
    def get_centring_status(self):
        return


    @abc.abstractmethod
    def take_snapshots(self):
        return

    
    @abc.abstractmethod
    def simulate_auto_centring(self, sample_info):
        return


class AbstractMicrodiffZoom(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def __init__(self, name):
        return

    
    @abc.abstractmethod
    def sort_predfeined_positions_list(self):
        return

    
    @abc.abstractmethod
    def connect_notify(self, signal):
        return


    @abc.abstractmethod
    def get_limits(self):
        return

    
    @abc.abstractmethod
    def get_predefined_positions_list(self):
        return


    @abc.abstractmethod
    def motor_position_changed(self, absolute_position, private):
        return


    @abc.abstractmethod
    def get_current_position_name(self, pos):
        return


    @abc.abstractmethod
    def move_to_position(self, position_name):
        return


    @abc.abstractmethod
    def set_new_predefined_position(self, position_name, position_offset):
        return


class AbstractMinidiff(object):
    """
    """
    
    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def __init__(self, *args):
        return


    @abc.abstractmethod
    def set_sample_info(self, smaple_info):
        return


    @abc.abstractmethod
    def do_auto_loop_centring(self, n, old):
        return

    
    @abc.abstractmethod
    def is_ready(self):
        return


    @abc.abstractmethod
    def is_valid(self):
        return


    @abc.abstractmethod
    def centring_motors_state_changed(self):
        return


    @abc.abstractmethod
    def equipment_ready(self):
        return


    @abc.abstractmethod
    def equipment_not_ready(self):
        return


    @abc.abstractmethod    
    def wago_light_state_changed(self, state):
        return


    @abc.abstractmethod
    def phi_motor_state_changed(self, state):
        return


    @abc.abstractmethod
    def phiz_motor_state_changed(self, state):
        return



    @abc.abstractmethod    
    def phiy_motor_sate_changed(self, state):
        return

    
    @abc.abstractmethod
    def get_calibration_data(self, offset):
        return


    @abc.abstractmethod
    def zoom_motor_predefined_position_changed(self, position_name, offset):
        return


    @abc.abstractmethod
    def zoom_motor_state_changed(self, state):
        return


    @abc.abstractmethod
    def sample_x_motor_state_changed(self, state):
        return


    @abc.abstractmethod
    def sample_y_motor_sate_changed(self, state):
        return


    @abc.abstractmethod
    def invalidate_centring(self):
        return


    @abc.abstractmethod
    def phiz_motor_moved(self, pos):
        return

    
    @abc.abstractmethod
    def phiy_motor_moved(self, pos):
        return


    @abc.abstractmethod
    def sample_x_motor_moved(self, pos):
        return


    @abc.abstractmethod
    def sample_y_motor_moved(self, pos):
        return


    @abc.abstractmethod
    def sample_changer_sample_is_loaded(self, state):
        return


    @abc.abstractmethod
    def move_to_beam(self, x, y):
        return


    @abc.abstractmethod
    def get_available_centring_methods(self):
        return


    @abc.abstractmethod
    def start_centring_method(self, method, sample_info):
        return


    @abc.abstractmethod
    def cancel_centring_mehtod(self, reject):
        return


    @abc.abstractmethod
    def current_centring_method(self):
        return


    @abc.abstractmethod
    def start_3_click_centring(self, sample_info):
        return

    
    @abc.abstractmethod
    def start_move_to_beam_centring(self, sample_info):
        return


    @abc.abstractmethod
    def start_auto_centring(self, sample_info, loop_only):
        return


    @abc.abstractmethod
    def image_clicked(self, x, y, xi, yi):
        return


    @abc.abstractmethod
    def emit_centring_started(self, method, flexible):
        return


    @abc.abstractmethod
    def accept_centring(self):
        return


    @abc.abstractmethod
    def reject_centring(self):
        return


    @abc.abstractmethod
    def emit_centring_moving(self):
        return


    @abc.abstractmethod
    def emit_centring_failed(self):
        return


    @abc.abstractmethod
    def emit_centring_successgfull(Self):
        return


    @abc.abstractmethod
    def emit_progress_message(self, msg):
        return

    
    @abc.abstractmethod
    def get_centring_status(self):
        return

    
    @abc.abstractmethod
    def take_snappshots(self):
        return

    
    @abc.abstractmethod
    def simulate_auto_centring(self, sample_info):
        return


class AbstractPhotonFlux(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def connect_notify(self, signal):
        return


    @abc.abstractmethod
    def update_flux(self):
        return


    @abc.abstractmethod
    def counts_updated(self, counts, ignore_shutter_state):
        return


    @abc.abstractmethod
    def emit_value_changed(self, counts):
        return


class AbstractResolution(object):
    """
    """


    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def get_radius(self):
        return


    @abc.abstractmethod
    def get_wavelength(self):
        return

    
    @abc.abstractmethod
    def detector_radius(self, radius):
        return


    @abc.abstractmethod
    def fixed_wavelength(self, wavelength):
        return


    @abc.abstractmethod
    def wavelength_cahnged(self, pos):
        return

    
    @abc.abstractmethod
    def energy_changed(self, energy):
        return


    @abc.abstractmethod
    def res_2_dist(self, res):
        return


    @abc.abstractmethod
    def dist_2_res(self, dist):
        return


    @abc.abstractmethod
    def recalculate_resolution(self):
        return


    @abc.abstractmethod
    def equipment_ready(self):
        return


    @abc.abstractmethod
    def equipment_not_ready(self):
        return

    
    @abc.abstractmethod
    def get_position(self):
        return


    @abc.abstractmethod
    def new_resolution(self, res):
        return


    @abc.abstractmethod
    def get_state(self):
        return


    @abc.abstractmethod
    def connect_notify(self, signal):
        return


    @abc.abstractmethod
    def detm_state_changed(self, state):
        return


    @abc.abstractmethod
    def get_limits(self, callback, error_callback):
        return

    
    @abc.abstractmethod
    def move(self, pos):
        return


    @abc.abstractmethod
    def new_distance(self, dist):
        return

    
    @abc.abstractmethod
    def stop(self):
        return


class AbstractQ315dist(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def equipment_ready(self):
        return


    @abc.abstractmethod
    def equipment_not_ready(self):
        return


    @abc.abstractmethod
    def is_valid(self):
        return


    @abc.abstractmethod
    def connect_notify(self, signal):
        return


    @abc.abstractmethod
    def detm_state_changed(self, state):
        return

    
    @abc.abstractmethod
    def dtox_limits_changed(self, limits):
        return


    @abc.abstractmethod
    def detm_positions_changed(self, pos):
        return


class AbstractSampleChanger(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod    
    def task_finished(self, exception):
        return


    @abc.abstractmethod
    def spec_disconnected(self):
        return


    @abc.abstractmethod
    def connect_notify(self, signal):
        return


    @abc.abstractmethod
    def loadded_sample_cahnged(self, loaded_sample, force):
        return


    @abc.abstractmethod
    def get_loaded_sample(self, loaded_sample_ext_dict):
        return


    @abc.abstractmethod
    def set_loaded_sample(self, loaded_sample_dict, extendedn):
        return


    @abc.abstractmethod
    def extend_loaded_sample(self, loaded_sample_ext_dict):
        return


    @abc.abstractmethod
    def set_loaded_sample(self, loaded_sample_dict, extended):
        return


    @abc.abstractmethod
    def reset(self):
        return


    @abc.abstractmethod
    def reset_basket_information(self):
        return


    @abc.abstractmethod
    def set_basket_information(self):
        return


    @abc.abstractmethod
    def set_basket_sample_information(self, input_):
        return


    @abc.abstractmethod
    def sample_load_state_changed(slef, laoded):
        return


    @abc.abstractmethod
    def procedure_prepare(self):
        return


    @abc.abstractmethod
    def procedure_exception_cleanup(self, state, problem, 
                                    md_get_ctrl, in_abort):
        return


    @abc.abstractmethod
    def current_procedure_name(self):
        return


    @abc.abstractmethod
    def sample_changer_state_changed(self, state):
        return


    @abc.abstractmethod
    def sample_changer_status_changed(self, status):
        return

    
    @abc.abstractmethod
    def sample_is_loaded(self):
        return

    
    @abc.abstractmethod
    def scan_basket(self, basket):
        return


    @abc.abstractmethod
    def scan_all_baskets(self, scan_finished_callback, failure_callback):
        return


    @abc.abstractmethod    
    def scan_baskets(self, baskets_to_scan, 
                     scan_finished_callback, failure_callback):
        return


    @abc.abstractmethod
    def stop_scan_all_baskets(self):
        return


    @abc.abstractmethod
    def scan_current_basket(self, scan_finished_callback, failure_callback):
        return


    @abc.abstractmethod
    def change_selected_basket(self, new_basket):
        return


    @abc.abstractmethod
    def change_selected_sample(self, new_sample):
        return

    
    @abc.abstractmethod
    def selected_basket_changed(self, basket):
        return


    @abc.abstractmethod
    def selected_sample_changed(self, sample):
        return


    @abc.abstractmethod
    def load_sample(self, holder_lenght, sample_id, sample_location,
                    sample_is_loaded_callback, failure_callback, 
                    prepare_centring, prepare_centring_motors):
        
        return


    @abc.abstractmethod
    def unload_sample(self, holder_length, sample_id, sample_location, 
                      sample_is_unloaded_callback, failure_callback):

        return


    @abc.abstractmethod
    def move_to_data_matrix(self, sample_id, moved_to_data_matrix_callback,
                            failure_callback):
        return


    @abc.abstractmethod
    def move_to_location(self, sample_location, moved_to_location_callback,
                         failure_callback):
        return


    @abc.abstractmethod
    def move_to_loading_position_retry(self, holder_lenght):
        return


    @abc.abstractmethod
    def move_to_unloading_position_retry(self, holder_lenght):
        return


    @abc.abstractmethod
    def move_cryo_in(self):
        return

    
    @abc.abstractmethod
    def move_light_in(self):
        return


    @abc.abstractmethod
    def update_data_matriced(self, matrices):
        return

    
    @abc.abstractmethod
    def get_matrix_codes(self, force):
        return


    @abc.abstractmethod
    def get_state(self):
        return


    @abc.abstractmethod
    def get_sc_holdeR_length(self):
        return


    @abc.abstractmethod
    def selected_sample_data_matrix_changed(self, matrix_code):
        return


    @abc.abstractmethod
    def is_microdiff(self):
        return


    @abc.abstractmethod
    def get_loaded_sample_data_matrix(self):
        return


    @abc.abstractmethod
    def get_loaded_sample_location(self):
        return


    @abc.abstractmethod
    def get_loaded_holder_length(self):
        return


    @abc.abstractmethod
    def get_basket_presence(self):
        return

    
    @abc.abstractmethod
    def can_load_sample(self, sample_code, sample_location,
                        holder_lenght):
        return


    @abc.abstractmethod
    def operational_flags_changed(self, val):
        return


    @abc.abstractmethod
    def sample_changer_in_use(self):
        return


    @abc.abstractmethod
    def sample_changer_can_load(self):
        return


    @abc.abstractmethod
    def minidiff_can_move(self):
        return


    @abc.abstractmethod
    def minidiff_get_control(self):
        return


    @abc.abstractmethod
    def sample_changer_to_loading_position(self):
        return

    
    @abc.abstractmethod
    def basket_tranfer_mode_changed(self, basket_transfer):
        return


    @abc.abstractmethod
    def get_basket_transfer_mode(self):
        return

    
    @abc.abstractmethod
    def switch_to_sample_transfer_mode(self):
        return
    

class AbstractXfeSpectrum(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def is_spec_connected(self):
        return


    @abc.abstractmethod
    def s_connected(self):
        return


    @abc.abstractmethod
    def s_disconnected(self):
        return


    @abc.abstractmethod
    def can_spectrum(self):
        return


    @abc.abstractmethod
    def start_xfe_spectrum(self, ct, directory, prefix, 
                           session_id, blsample_id):
        return


    @abc.abstractmethod
    def cancel_xfe_spectrum(self):
        return


    @abc.abstractmethod
    def spectrum_command_ready(self):
        return

    
    @abc.abstractmethod
    def spectrum_command_not_ready(self):
        return


    @abc.abstractmethod
    def spectrum_command_started(self):
        return

    
    @abc.abstractmethod
    def spectrum_command_failed(self):
        return


    @abc.abstractmethod
    def spectrum_command_aborted(self):
        return


    @abc.abstractmethod
    def spectrum_command_finished(self, result):
        return


    @abc.abstractmethod
    def spectrum_status_changed(self, status):
        return


    @abc.abstractmethod
    def store_xfe_spectrum(self):
        return


    @abc.abstractmethod
    def update_xfe_spectrum(self):
        return


    @abc.abstractmethod
    def get_spectrum_params(self):
        return


    @abc.abstractmethod
    def set_spectrum_params(self, pars):
        return



