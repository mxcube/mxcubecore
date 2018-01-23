import os
import subprocess
import logging
import re
import f90nml
import General
from CollectMockup import CollectMockup
from HardwareRepository.HardwareRepository import HardwareRepository
from TaskUtils import task
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict


class CollectEmulator(CollectMockup):
    def __init__(self, name):
        CollectMockup.__init__(self, name)
        self.gphl_connection_hwobj = None
        self.gphl_workflow_hwobj = None

        # # TODO get appropriate value
        # # We must have a value for functions to work
        # # This ought to eb OK for a Pilatus 6M (See TangoResolution object)
        # self.det_radius = 212.

        # self._detector_distance = 300.
        # self._wavelength = 1.0

        self._counter = 1

    # def make_image_file_template(self, data_collect_parameters, suffix=None):
    #
    #     file_parameters = data_collect_parameters["fileinfo"]
    #     suffix = suffix or file_parameters.get('suffix')
    #     prefix = file_parameters.get('prefix')
    #     run_number = file_parameters.get('run_number')
    #
    #     image_file_template = ("%s_%s_????.%s" % (prefix, run_number, suffix))
    #     file_parameters["template"] = image_file_template

    def _get_simcal_input(self, data_collect_parameters, crystal_data):
        """Get ordered dict with simcal input from available data"""

        # Set up and add crystal data
        result = OrderedDict()
        setup_data = result['setup_list'] = crystal_data

        # update with instrument data
        config_dir = os.path.join(
            HardwareRepository().getHardwareRepositoryPath(),
            self.gphl_workflow_hwobj.getProperty('gphl_config_subdir')
        )
        instrument_input = f90nml.read(
            os.path.join(config_dir,'instrumentation.nml')
        )

        instrument_data = instrument_input['sdcp_instrument_list']
        segments = instrument_input['segment_list']
        if isinstance(segments, dict):
            segment_count = 1
        else:
            segment_count = len(segments)

        sweep_count = len(data_collect_parameters['oscillation_sequence'])

        # Move beamstop settings to top level
        ll = instrument_data.get('beamstop_param_names')
        ll2 = instrument_data.get('beamstop_param_vals')
        if ll and ll2:
            for tag, val in zip(ll, ll2):
                instrument_data[tag.lower()] = val

        # Setting parameters in order (may not be necessary, but ...)
        # Misssing: *mu*
        remap = {'beam':'nominal_beam_dir', 'det_coord_def':'det_org_dist',
                 'cone_s_height':'cone_height'}
        tags = ('lambda_sd', 'beam', 'beam_sd_deg', 'pol_plane_n', 'pol_frac',
                'd_sensor',
                'min_zeta', 'det_name', 'det_x_axis', 'det_y_axis', 'det_qx',
                'det_qy', 'det_nx', 'det_ny', 'det_org_x', 'det_org_y',
                'det_coord_def'
                )
        for tag in tags:
            val = instrument_data.get(remap.get(tag, tag))
            if val is not None:
                setup_data[tag] = val

        ll = instrument_data['gonio_axis_dirs']
        setup_data['omega_axis'] = ll[:3]
        setup_data['kappa_axis'] = ll[3:6]
        setup_data['phi_axis'] = ll[6:]
        ll = instrument_data['gonio_centring_axis_dirs']
        setup_data['trans_x_axis'] = ll[:3]
        setup_data['trans_y_axis'] = ll[3:6]
        setup_data['trans_z_axis'] = ll[6:]
        tags = ('cone_radius', 'cone_s_height', 'beam_stop_radius',
                'beam_stop_s_length', 'beam_stop_s_distance', 'gain', 'background',)
        for tag in tags:
            val = instrument_data.get(remap.get(tag, tag))
            if val is not None:
                setup_data[tag] = val


        # Add/overwrite parameters from emulator configuration
        conv = General.convert_string_value
        for key, val in self['simcal_parameters'].getProperties().items():
            setup_data[key] = conv(val)

        setup_data['n_vertices'] = 0
        setup_data['n_triangles'] = 0
        setup_data['n_segments'] = segment_count
        setup_data['n_orients'] = 0
        setup_data['n_sweeps'] = sweep_count

        # Add segments
        result['segment_list'] = segments

        # Adjustments
        val = instrument_data.get('beam')
        if val:
            setup_data['beam'] = val

        # update with diffractcal data
        # TODO check that this works also for updating segment list
        fp = os.path.join(config_dir, 'diffractcal.nml')
        if os.path.isfile(fp):
            diffractcal_data = f90nml.read(fp)['sdcp_instrument_list']
            for tag in setup_data.keys():
                val = diffractcal_data.get(tag)
                if val is not None:
                    setup_data[tag] = val
            ll = diffractcal_data['gonio_axis_dirs']
            setup_data['omega_axis'] = ll[:3]
            setup_data['kappa_axis'] = ll[3:6]
            setup_data['phi_axis'] = ll[6:]

        # Add sweeps
        sweeps = []
        for osc in data_collect_parameters['oscillation_sequence']:
            motors = data_collect_parameters['motors']
            # get resolution limit and detector distance
            resolution = data_collect_parameters['resolution']['upper']
            self.set_resolution(resolution)
            sweep = OrderedDict()

            sweep['lambda'] = General.h_over_e/data_collect_parameters['energy']
            sweep['res_limit'] = resolution
            sweep['exposure'] = osc['exposure_time']
            ll =  self. gphl_workflow_hwobj.translation_axis_roles
            sweep['trans_xyz'] = list(motors.get(x) or 0.0 for x in ll)
            sweep['det_coord'] = self.get_detector_distance()
            # NBNB hardwired for omega scan TODO
            sweep['axis_no'] = 3
            sweep['omega_deg'] = osc['start']
            # NB kappa and phi are overwritten from the motors dict, if set there
            sweep['kappa_deg'] = osc['kappaStart']
            sweep['phi_deg'] = osc['phiStart']
            sweep['step_deg'] = osc['range']
            sweep['n_frames'] = osc['number_of_images']
            sweep['image_no'] = osc['start_image_number']
            # self.make_image_file_template(data_collect_parameters, suffix='cbf')

            # Extract format statement from template,
            # and convert to fortran format
            template = data_collect_parameters['fileinfo']['template']
            ss = str(re.search('(%[0-9]+d)', template).group(0))
            template = template.replace(ss, '?' * int(ss[1:-1]))
            name_template = os.path.join(
                data_collect_parameters['fileinfo']['directory'], template
                # data_collect_parameters['fileinfo']['template']
            )
            sweep['name_template'] = General.to_ascii(name_template)

            # Overwrite kappa and phi from motors - if set
            val = motors.get('kappa')
            if val is not None:
                sweep['kappa_deg'] = val
            val = motors.get('kappa_phi')
            if val is not None:
                sweep['phi_deg'] = val

            # Skipped: spindle_deg=0.0, two_theta_deg=0.0, mu_air=-1, mu_sensor=-1

            sweeps.append(sweep)

        if sweep_count == 1:
            # NBNB in current code we can have only one sweep here,
            # but it will work for multiple
            result['sweep_list'] = sweep
        else:
            result['sweep_list'] = sweeps
        #
        return result

    @task
    def data_collection_hook(self):
        """Spawns data emulation using gphl simcal"""

        data_collect_parameters = self.current_dc_parameters

        logging.getLogger('HWR').debug("Emulator: nominal position "
            + ', '.join('%s=%s' % (tt)
                        for tt in sorted(data_collect_parameters['motors'].items())
                        if tt[1] is not None)
        )

        logging.getLogger('HWR').debug("Emulator:  actual position "
             + ', '.join('%s=%s' % tt
                         for tt in sorted(self.diffractometer_hwobj.get_positions().items())
                         if tt[1] is not None)
        )

        # Done here as there are what-happens-first conflicts
        # if you put it in init
        if self.gphl_workflow_hwobj is None:
            self.gphl_workflow_hwobj = HardwareRepository().getHardwareObject(
                'gphl-workflow'
            )
            if not self.gphl_workflow_hwobj:
                raise ValueError("Emulator requires GPhL workflow installation")
        if self.gphl_connection_hwobj is None:
            self.gphl_connection_hwobj = HardwareRepository().getHardwareObject(
                'gphl-setup'
            )
            if not self.gphl_connection_hwobj:
                raise ValueError("Emulator requires GPhL connection installation")

        # Get program locations
        gphl_installation_dir = self.gphl_connection_hwobj.getProperty(
            'gphl_installation_dir'
        )
        dd = self.gphl_connection_hwobj['gphl_program_locations'].getProperties()
        license_directory = dd['co.gphl.wf.bdg_licence_dir']
        simcal_executive = os.path.join(
            gphl_installation_dir, dd['co.gphl.wf.simcal.bin']
        )

        # Get environmental variables
        envs = {'BDG_home':license_directory or gphl_installation_dir}
        for tag, val in self['environment_variables'].getProperties().items():
            envs[str(tag)] = str(val)

        # get crystal data
        sample_dir = os.path.join(
            HardwareRepository().getHardwareRepositoryPath(),
            self.gphl_workflow_hwobj.getProperty('gphl_samples_subdir'),
            self.getProperty('sample_name')
        )
        # in spite of the simcal_crystal_list name this returns an OrderdDict
        crystal_data = f90nml.read(
            os.path.join(sample_dir, 'crystal.nml')
        )['simcal_crystal_list']

        input_data = self._get_simcal_input(data_collect_parameters,
                                            crystal_data)

        # NB outfile is the echo output of the input file;
        # image files templates are set in the input file
        file_info = data_collect_parameters['fileinfo']
        if not os.path.exists(file_info['process_directory']):
            os.makedirs(file_info['process_directory'])
        if not os.path.exists(file_info['directory']):
            os.makedirs(file_info['directory'])
        infile = os.path.join(file_info['process_directory'],
                              'simcal_in_%s.nml' % self._counter)

        f90nml.write(input_data, infile, force=True)
        outfile = os.path.join(file_info['process_directory'],
                               'simcal_out_%s.nml' % self._counter)
        self._counter += 1
        hklfile = os.path.join(sample_dir, 'sample.hkli')
        command_list = [simcal_executive, '--input', infile, '--output', outfile,
                        '--hkl', hklfile]

        for tag, val in self['simcal_options'].getProperties().items():
            command_list.extend(General.commandOption(tag, val, prefix='--'))
        logging.getLogger('HWR').info("Executing command: %s" % command_list)

        try:
            running_process = subprocess.Popen(command_list, stdout=None,
                                                     stderr=None, env=envs)
        except:
            logging.getLogger('HWR').error('Error in spawning workflow application')
            raise

        # This does waiting, so we want to collect the result afterwards
        super(CollectEmulator, self).data_collection_hook()

        logging.getLogger('HWR').info(
            'Waiting for simcal collection emulation.'
        )
        # NBNB TODO put in time-out, somehow
        if running_process is not None:
            return_code = running_process.wait()
            if return_code:
                raise RuntimeError("simcal process terminated with return code %s"
                                   % return_code)
            else:
                logging.getLogger('HWR').info(
                    'Simcal collection emulation successful'
                )

        return

    # TODO move these functions to CollectMockup
    def set_wavelength(self, wavelength):
        self.energy_hwobj.move_wavelength(wavelength)

    def set_energy(self, energy):
        self.energy_hwobj.start_move_energy(energy)

    def set_resolution(self, new_resolution):
        self.resolution_hwobj.move(new_resolution)

    def move_detector(self, detector_distance):
        self.detector_hwobj.set_distance(detector_distance)

    def move_motors(self, motor_position_dict):
        # TODO We copy as dictionary is reset in move_motors. CLEAR UP!!
        # TODO clear up this confusion between move_motors and moveMotors
        self.diffractometer_hwobj.move_motors(motor_position_dict.copy())

