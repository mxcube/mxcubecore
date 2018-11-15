import os
import logging
import jsonpickle
import queue_model_objects_v1 as queue_model_objects

from HardwareRepository.BaseHardwareObjects import HardwareObject
from XSDataMXCuBEv1_3 import XSDataInputMXCuBE
import queue_model_enumerables_v1 as queue_model_enumerables

from HardwareRepository.HardwareRepository import HardwareRepository


class BeamlineSetup(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._object_by_path = {}
        self._plate_mode = False

    def init(self):
        """
        Framework 2 init, inherited from HardwareObject.
        """

        self.sample_changer_hwobj = None
        self.plate_manipulator_hwobj = None

        for role in self.getRoles():
            self._get_object_by_role(role)

        self._object_by_path['/beamline/energy'] = self.energy_hwobj
        self._object_by_path['/beamline/resolution'] = self.resolution_hwobj
        self._object_by_path['/beamline/transmission'] = self.transmission_hwobj

        self.advanced_methods = []

        try:
            self.advanced_methods = eval(self.getProperty("advancedMethods", "[]"))
        except:
            pass

        self.autoprocessing_methods = []
        try:
            self.autoprocessing_methods = eval(self.getProperty("autoprocessingMethods"))
            queue_model_objects.DataCollection.set_processing_methods(self.autoprocessing_methods)
        except:
            pass

        self.run_processing_parallel = self.getProperty("run_processing_parallel", False)

    def _get_object_by_role(self, role):
        """
        Gets the object with the role <role>' and adds the attribute
        <role>_hwobj to the current instance.
        """
        try:
            value = self.getObjectByRole(role)
        except:
            value = None
            logging.getLogger('HWR').exception('Could not get object with ' +\
                'role:' + role + 'from hardware repository.')

        setattr(self, role + '_hwobj', value)

    def read_value(self, path):
        """
        Reads the value of the hardware object at the given path. The
        hardware object must have the get_value method.

        :param path: Path to a hardware object.
        :type path: str

        :returns: The 'value' of the hardware object.
        :rtype: Return type of get_value of the hardware object.
        """
        value = None

        if path == '/beamline/default-acquisition-parameters/':
            value = jsonpickle.encode(self.get_default_acquisition_parameters())
        elif path == '/beamline/default-path-template/':
            value = jsonpickle.encode(self.get_default_path_template())
        else:
            hwobj = None

            try:
                hwobj = self._object_by_path[path]
                value = hwobj.get_value()
            except KeyError:
                raise KeyError('Invalid path')

        return value

    def get_advanced_methods(self):
        return self.advanced_methods

    def set_plate_mode(self, state):
        """
        Sets plate mode, if crystal plates are used instead of ordinary sample
        pints

        :param state: True if palte is used False if pin is used.
        :type state: bool
        """
        self._plate_mode = state

    def detector_has_shutterless(self):
        """
        :returns: True if the detector is capable of shuterless.
        :rtype: bool
        """
        try:
            return self.detector_hwobj.has_shutterless()
        except AttributeError:
            return False

    def tunable_wavelength(self):
        """
        :returns: Returns True if the beamline has tunable wavelength.
        :rtype: bool
        """
        tw = False

        try:
            tw = bool(self.getProperty('tunable_wavelength'))
        except TypeError:
            tw = False

        return tw

    def has_aperture(self):
        """
        :returns: True if the beamline has apertures and false otherwise.
        """
        ap = False

        try:
            ap = bool(self.getProperty('has_aperture'))
        except TypeError:
            ap = False

        return ap

    def disable_num_passes(self):
        """
        :returns: Returns True if it is possible to use the number of passes
                  collection parameter.
        :rtype: bool
        """
        disable_num_passes = False

        try:
            disable_num_passes = self.getProperty('disable_num_passes')

            if disable_num_passes is None:
                disable_num_passes = False

        except:
            disable_num_passes = False

        return disable_num_passes

    def get_default_char_acq_parameters(self):
        """
        :returns: A AcquisitionParameters object with all default parameters.
        """
        acq_parameters = queue_model_objects.AcquisitionParameters()
        parent_key = "default_characterisation_values"

        img_start_num = self[parent_key].getProperty('start_image_number')
        num_images = self[parent_key].getProperty('number_of_images')
        osc_range = round(float(self[parent_key].getProperty('range')), 2)
        overlap = round(float(self[parent_key].getProperty('overlap')), 2)
        exp_time = round(float(self[parent_key].getProperty('exposure_time')), 4)
        num_passes = int(self[parent_key].getProperty('number_of_passes'))
        shutterless = self.detector_has_shutterless()
        try:
            detector_mode = self.detector_hwobj.default_mode()
        except AttributeError:
            detector_mode = None

        acq_parameters.first_image = int(img_start_num)
        acq_parameters.num_images = int(num_images)
        acq_parameters.osc_start = self._get_omega_axis_position()
        acq_parameters.osc_range = osc_range
        acq_parameters.kappa = self._get_kappa_axis_position()
        acq_parameters.kappa_phi = self._get_kappa_phi_axis_position()
        acq_parameters.overlap = overlap
        acq_parameters.exp_time = exp_time
        acq_parameters.num_passes = num_passes
        acq_parameters.resolution = self._get_resolution()
        acq_parameters.energy = self._get_energy()
        acq_parameters.transmission = self._get_transmission()

        acq_parameters.shutterless = self._has_shutterless()
        acq_parameters.detector_mode = self.detector_hwobj.get_detector_mode()

        acq_parameters.inverse_beam = False
        acq_parameters.take_dark_current = True
        acq_parameters.skip_existing_images = False
        acq_parameters.take_snapshots = True

        return acq_parameters

    def get_default_characterisation_parameters(self):
        """
        :returns: A CharacterisationsParameters object with default parameters.
        """
        input_fname = self.data_analysis_hwobj.edna_default_file
        fp = HardwareRepository().findInRepository(input_fname)
        if fp is None:
            raise ValueError("File %s not found in repository" % input_fname)
        with open(fp, 'r') as f:
            edna_default_input = ''.join(f.readlines())

        edna_input = XSDataInputMXCuBE.parseString(edna_default_input)
        diff_plan = edna_input.getDiffractionPlan()

        edna_sample = edna_input.getSample()
        char_params = queue_model_objects.CharacterisationParameters()
        char_params.experiment_type = queue_model_enumerables.EXPERIMENT_TYPE.OSC

        # Optimisation parameters
        char_params.use_aimed_resolution = False
        try:
            char_params.aimed_resolution = diff_plan.getAimedResolution().getValue()
        except:
            char_params.aimed_resolution = None

        char_params.use_aimed_multiplicity = False
        try:
            char_params.aimed_i_sigma = diff_plan.getAimedIOverSigmaAtHighestResolution().getValue()
            char_params.aimed_completness = diff_plan.getAimedCompleteness().getValue()
        except:
            char_params.aimed_i_sigma = None
            char_params.aimed_completness = None

        char_params.strategy_complexity = 0
        char_params.induce_burn = False
        char_params.use_permitted_rotation = False
        char_params.permitted_phi_start = 0.0
        char_params.permitted_phi_end = 360
        char_params.low_res_pass_strat = False

        # Crystal
        char_params.max_crystal_vdim = edna_sample.getSize().getY().getValue()
        char_params.min_crystal_vdim = edna_sample.getSize().getZ().getValue()
        char_params.max_crystal_vphi = 90
        char_params.min_crystal_vphi = 0.0
        char_params.space_group = ""

        # Characterisation type
        char_params.use_min_dose = True
        char_params.use_min_time = False
        char_params.min_dose = 30.0
        char_params.min_time = 0.0
        char_params.account_rad_damage = True
        char_params.auto_res = True
        char_params.opt_sad = False
        char_params.sad_res = 0.5
        char_params.determine_rad_params = False
        char_params.burn_osc_start = 0.0
        char_params.burn_osc_interval = 3

        # Radiation damage model
        char_params.rad_suscept = edna_sample.getSusceptibility().getValue()
        char_params.beta = 1
        char_params.gamma = 0.06

        return char_params

    def get_default_acquisition_parameters(self, parent_key=None):
        """
        :returns: A AcquisitionParameters object with all default parameters.
        """
        default_key = "default_acquisition_values"
        if parent_key is None:
            parent_key = default_key

        acq_parameters = queue_model_objects.AcquisitionParameters()

        try:
            self[parent_key]
        except KeyError:
            logging.warning("No key %s in beamline setup, using %s", parent_key, default_key)
            parent_key = default_key

        img_start_num = self[parent_key].getProperty('start_image_number')
        num_images = self[parent_key].getProperty('number_of_images')
        osc_range = round(float(self[parent_key].getProperty('range')), 2)
        overlap = round(float(self[parent_key].getProperty('overlap')), 2)
        exp_time = round(float(self[parent_key].getProperty('exposure_time')), 4)
        num_passes = int(self[parent_key].getProperty('number_of_passes'))
        shutterless = self.detector_has_shutterless()

        try:
            detector_mode = self.detector_hwobj.default_mode()
        except AttributeError:
            detector_mode = None

        acq_parameters.first_image = img_start_num
        acq_parameters.num_images = num_images
        acq_parameters.osc_start = self._get_omega_axis_position()
        acq_parameters.osc_range = osc_range
        acq_parameters.kappa = self._get_kappa_axis_position()
        acq_parameters.kappa_phi = self._get_kappa_phi_axis_position()
        acq_parameters.overlap = overlap
        acq_parameters.exp_time = exp_time
        acq_parameters.num_passes = num_passes
        acq_parameters.resolution = self._get_resolution()
        acq_parameters.energy = self._get_energy()
        acq_parameters.transmission = self._get_transmission()

        acq_parameters.shutterless = self._has_shutterless()
        acq_parameters.detector_mode = self._get_detector_mode()

        acq_parameters.inverse_beam = False
        acq_parameters.take_dark_current = True
        acq_parameters.skip_existing_images = False
        acq_parameters.take_snapshots = True

        return acq_parameters

    def get_acquisition_limit_values(self,
                                     parent_key="acquisition_limit_values"):
        limits = {}
        try:
            exp_time_limit = self[parent_key].getProperty('exposure_time')
        except IndexError:
            # set default exposure time limits [s] if nothing configured
            limits['exposure_time'] = '0, 1000'
            return limits
        
        if exp_time_limit is not None:
            if isinstance(exp_time_limit, str):
                try:
                    exp_time_limit = '%f, 1000' % float(exp_time_limit)
                except ValueError:
                    pass
            limits['exposure_time'] = exp_time_limit
        else:
            # set default exposure time limits [s] if not configured
            limits['exposure_time'] = '0, 1000'       

        try:
            range_limit = self[parent_key].getProperty('osc_range')
            if range_limit is not None:
                limits['osc_range'] = range_limit
        except:
            pass

        try:
            num_images_limit = self[parent_key].getProperty('number_of_images')
            if num_images_limit is not None:
                limits['number_of_images'] = num_images_limit
        except:
            pass

        try:
            kappa_limit = self[parent_key].getProperty('kappa')
            if kappa_limit is not None:
                limits['kappa'] = kappa_limit
        except:
            pass

        try:
            kappa_phi_limit = self[parent_key].getProperty('kappa_phi')
            if kappa_phi_limit is not None:
                limits['kappa_phi'] = kappa_phi_limit
        except:
            pass

        return limits

    def get_default_path_template(self):
        """
        :returns: A PathTemplate object with default parameters.
        """
        path_template = queue_model_objects.PathTemplate()
        parent_key = "default_acquisition_values"

        path_template.directory = str()
        path_template.process_directory = str()
        path_template.base_prefix = str()
        path_template.mad_prefix = ''
        path_template.reference_image_prefix = ''
        path_template.wedge_prefix = ''
        path_template.run_number = self[parent_key].getProperty('run_number')
        path_template.suffix = self.session_hwobj["file_info"].getProperty('file_suffix')
        path_template.precision = '04'

        try:
            if self.session_hwobj["file_info"].getProperty('precision'):
                path_template.precision = eval(self.session_hwobj["file_info"].getProperty('precision'))
        except:
            pass

        path_template.start_num = int(self[parent_key].getProperty('start_image_number'))
        path_template.num_files = int(self[parent_key].getProperty('number_of_images'))

        return path_template

    def _get_energy(self):
        try:
            energy = self.energy_hwobj.getCurrentEnergy()
        except AttributeError:
            energy = 0
        except TypeError:
            energy = 0

        return energy

    def _get_transmission(self):
        try:
            transmission = self.transmission_hwobj.get_value()
        except AttributeError:
            transmission = 0
        except TypeError:
            transmission = 0

        return transmission

    def _get_resolution(self):
        try:
            resolution = self.resolution_hwobj.getPosition()
        except AttributeError:
            resolution = 0
        except TypeError:
            resolution = 0

        return resolution

    def _get_omega_axis_position(self):
        result = 0

        try:
            result = round(float(self.omega_axis_hwobj.getPosition()), 2)
        except TypeError:
            parent_key = "default_acquisition_values"
            result = round(float(self[parent_key].getProperty('start_angle')), 2)
        except AttributeError:
            parent_key = "default_acquisition_values"
            result = round(float(self[parent_key].getProperty('start_angle')), 2)

        return result

    def _get_kappa_axis_position(self):
        """
        Descript. :
        """
        result = 0
        try:
            result = round(float(self.kappa_axis_hwobj.getPosition()), 2)
        except:
            pass
        return result

    def _get_kappa_phi_axis_position(self):
        """
        Descript. :
        """
        result = 0
        try:
            result = round(float(self.kappa_phi_axis_hwobj.getPosition()), 2)
        except:
            pass
        return result

    def _has_shutterless(self):
        """
        Descript. :
        """
        result = False
        try:
            result = self.detector_hwobj.has_shutterless()
        except:
            pass
        return result


    def _get_detector_mode(self):
        """
        Descript. :
        """
        result = ""
        try: 
           result = self.detector_hwobj.get_detector_mode()
        except:
            pass
        return result

    def _get_run_processing_parallel(self):
        return self.run_processing_parallel

    def check_collection_parameters(self, parameters_list):
        invalid_parameters_list = []
        for parameter_item in parameters_list:
            (bottom, top) = self.energy_hwobj.getEnergyLimits()
            if parameter_item['energy'] > top or \
               parameter_item['energy'] < bottom:
               invalid_parameters_list.append('Energy')
            [bottom, top] = self.detector_hwobj.get_exposure_time_limits()
            if parameter_item['exp_time'] > top or \
               parameter_item['exp_time'] < bottom:
               invalid_parameters_list.append('Exposure time')
        return invalid_parameters_list
