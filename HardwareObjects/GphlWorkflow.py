#! /usr/bin/env python
# encoding: utf-8
"""Global phasing workflow runner
"""

__copyright__ = """
  * Copyright © 2016 - 2017 by Global Phasing Ltd.
"""
__author__ = "rhfogh"
__date__ = "06/04/17"

import logging
import uuid
import time
import os
import subprocess
import f90nml

import gevent
import gevent.event
import gevent._threading
from dispatcher import dispatcher

import ConvertUtils
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareRepository import HardwareRepository

import queue_model_objects_v1 as queue_model_objects
import queue_model_enumerables_v1 as queue_model_enumerables
from queue_entry import QUEUE_ENTRY_STATUS

import GphlMessages

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

States = queue_model_enumerables.States

# Used to pass to priorInformation when no wavelengths are set (DiffractCal)
DUMMY_WAVELENGTH = 999.999


class GphlWorkflow(HardwareObject, object):
    """Global Phasing workflow runner.
    """

    # Imported here to keep it out of the shared top namespace
    # NB, by the time the code gets here, HardwareObjects is on the PYTHONPATH
    # as is HardwareRepository
    # NB accessed as self.GphlMessages
    import GphlMessages

    # object states
    valid_states = [
        States.OFF,     # Not active
        States.ON,      # Active, awaiting execution order
        States.OPEN,    # Active, awaiting input
        States.RUNNING, # Active, executing workflow
    ]

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._state = States.OFF

        # HO that handles connection to GPhL workflow runner
        self._workflow_connection = None

        # Needed to allow methods to put new actions on the queue
        # And as a place to get hold of other objects
        self._queue_entry = None

        # event to handle waiting for parameter input
        self._return_parameters = None

        # Message - processing function map
        self._processor_functions = {}

        # Subprocess names to track which subprocess is getting info
        self._server_subprocess_names = {}

        # Rotation axis role names, ordered from holder towards sample
        self.rotation_axis_roles = []

        # Translation axis role names
        self.translation_axis_roles = []

        # Switch for 'move-to-fine-zoom' message for translational calibration
        self._use_fine_zoom = False

        # Configurable file paths
        self.file_paths = {}

    def _init(self):
        pass

    def init(self):

        # Set standard configurable file paths
        file_paths = self.file_paths
        gphl_beamline_config = HardwareRepository().findInRepository(
            self.getProperty('gphl_beamline_config')
        )
        file_paths['gphl_beamline_config'] = gphl_beamline_config
        file_paths['instrumentation_file'] = fp = os.path.join(
            gphl_beamline_config, 'instrumentation.nml'
        )
        dd = f90nml.read(fp)['sdcp_instrument_list']
        self.rotation_axis_roles = dd['gonio_axis_names']
        self.translation_axis_roles = dd['gonio_centring_axis_names']

        file_paths['transcal_file'] = os.path.join(
            gphl_beamline_config, 'transcal.nml'
        )
        file_paths['diffractcal_file'] = os.path.join(
            gphl_beamline_config, 'diffractcal.nml'
        )

        gphl_config = HardwareRepository().findInRepository(
            self.getProperty('gphl_config')
        )
        file_paths['test_samples'] = os.path.join(gphl_config, 'test_samples')
        file_paths['scripts'] = os.path.join(gphl_config, 'scripts')

        # Set up processing functions map
        self._processor_functions = {
            'String':self.echo_info_string,
            'SubprocessStarted':self.echo_subprocess_started,
            'SubprocessStopped':self.echo_subprocess_stopped,
            'RequestConfiguration':self.get_configuration_data,
            'GeometricStrategy':self.setup_data_collection,
            'CollectionProposal':self.collect_data,
            'ChooseLattice':self.select_lattice,
            'RequestCentring':self.process_centring_request,
            'PrepareForCentring':self.prepare_for_centring,
            'ObtainPriorInformation':self.obtain_prior_information,
            'WorkflowAborted':self.workflow_aborted,
            'WorkflowCompleted':self.workflow_completed,
            'WorkflowFailed':self.workflow_failed,
        }

    def pre_execute(self, queue_entry):

        self._queue_entry = queue_entry

        #If not already active, set up connections and turn ON
        if self.get_state() == States.OFF:
            workflow_connection = queue_entry.beamline_setup.getObjectByRole(
                'gphl_connection'
            )
            self._workflow_connection = workflow_connection
            workflow_connection._initialize_connection(self)
            workflow_connection._open_connection()
            self.set_state(States.ON)

    def shutdown(self):
        """Shut down workflow and connection. Triggered on program quit."""
        workflow_connection = self._workflow_connection
        if workflow_connection is not None:
            workflow_connection._workflow_ended()
            workflow_connection._close_connection()


    def get_available_workflows(self):
        """Get list of workflow description dictionaries."""

        # TODO this could be cached for speed


        instcfgout_dir = self.getProperty('instcfgout_dir')

        result = OrderedDict()
        if self.hasObject('workflow_properties'):
            properties = self['workflow_properties'].getProperties()
        else:
            properties = {}

        if self.hasObject('workflow_options'):
            options = self['workflow_options'].getProperties()
        else:
            options = {}
        if self.hasObject('invocation_options'):
            invocation_options = self['invocation_options'].getProperties()
        else:
            invocation_options = {}
        if self.hasObject('invocation_properties'):
            invocation_properties = self['invocation_properties'].getProperties()
        else:
            invocation_properties = {}

        for wf_node in self['workflows']:
            name = wf_node.name()
            wf_dict = {'name':name,
                       'strategy_type':wf_node.getProperty('strategy_type'),
                       'application':wf_node.getProperty('application'),
                       'documentation':wf_node.getProperty('documentation',
                                                           default_value=''),
                       'interleaveOrder':wf_node.getProperty('interleave_order',
                                                             default_value=''),
            }
            result[name] = wf_dict
            wf_dict['options'] = dd = options.copy()
            if wf_node.hasObject('options'):
                dd.update(wf_node['options'].getProperties())
                relative_file_path = dd.get('file')
                if relative_file_path is not None:
                    # Special case - this option must be modified before use
                    dd['file'] = os.path.join(
                        self.file_paths['gphl_beamline_config'],
                        relative_file_path
                    )
                instcfgout = dd.get('instcfgout')
                if instcfgout is not None and instcfgout_dir is not None:
                    # Special case - this option must be modified before use
                    dd['instcfgout'] = os.path.join(instcfgout_dir, instcfgout)
            wf_dict['properties'] = dd = properties.copy()
            if wf_node.hasObject('properties'):
                dd.update(wf_node['properties'].getProperties())
            wf_dict['invocation_properties'] = dd = invocation_properties.copy()
            if wf_node.hasObject('invocation_properties'):
                dd.update(wf_node['invocation_properties'].getProperties())
            wf_dict['invocation_options'] = dd = invocation_options.copy()
            if wf_node.hasObject('invocation_options'):
                dd.update(wf_node['invocation_options'].getProperties())

            if wf_node.hasObject('beam_energies'):
                wf_dict['beam_energies'] = dd = OrderedDict()
                for wavelength in wf_node['beam_energies']:
                    dd[wavelength.getProperty('role')] = (
                        wavelength.getProperty('value')
                    )
        #
        return result

    def get_state(self):
        return self._state

    def set_state(self, value):
        if value in self.valid_states:
            self._state = value
            self.emit('stateChanged', (value, ))
        else:
            raise RuntimeError("GphlWorlflow set to invalid state: s"
                               % value)

    def workflow_end(self):
        """
        The workflow has finished, sets the state to 'ON'
        """

        self._queue_entry = None
        # if not self._gevent_event.is_set():
        #     self._gevent_event.set()
        self.set_state(States.ON)
        self._server_subprocess_names.clear()
        workflow_connection = self._workflow_connection
        if workflow_connection is not None:
            workflow_connection._workflow_ended()


    def abort(self, message=None):
        logging.getLogger("HWR").info('MXCuBE aborting current GPhL workflow')
        workflow_connection = self._workflow_connection
        if workflow_connection is not None:
            workflow_connection.abort_workflow(message=message)

    def execute(self):

        try:
            self.set_state(States.RUNNING)

            workflow_queue = gevent._threading.Queue()
            # Fork off workflow server process
            workflow_connection = self._workflow_connection
            if workflow_connection is not None:
                workflow_connection.start_workflow(
                    workflow_queue, self._queue_entry.get_data_model()
                )

            while True:
                while workflow_queue.empty():
                    time.sleep(0.1)

                tt = workflow_queue.get_nowait()
                if tt is StopIteration:
                    break

                message_type, payload, correlation_id, result_list = tt
                func = self._processor_functions.get(message_type)
                if func is None:
                    logging.getLogger("HWR").error(
                        "GPhL message %s not recognised by MXCuBE. Terminating..."
                        % message_type
                    )
                    break
                else:
                    logging.getLogger("HWR").info("GPhL queue processing %s"
                                                  % message_type)
                    response = func(payload, correlation_id)
                    if result_list is not None:
                        result_list.append((response, correlation_id))

        except:
            self.workflow_end()
            logging.getLogger("HWR").error(
                "Uncaught error during GPhL workflow execution",
                exc_info=True
            )
            raise

    def _add_to_queue(self, parent_model_obj, child_model_obj):
        # There should be a better way, but apparently there isn't
        qmo = HardwareRepository().getHardwareObject('/queue-model')
        qmo.add_child(parent_model_obj, child_model_obj)


    # Message handlers:

    def workflow_aborted(self, payload, correlation_id):
        logging.getLogger("user_level_log").info(
            "GPhL Workflow aborted."
        )

    def workflow_completed(self, payload, correlation_id):
        logging.getLogger("user_level_log").info(
            "GPhL Workflow completed."
        )

    def workflow_failed(self, payload, correlation_id):
        logging.getLogger("user_level_log").info(
            "GPhL Workflow failed."
        )

    def echo_info_string(self, payload, correlation_id=None):
        """Print text info to console,. log etc."""
        subprocess_name = self._server_subprocess_names.get(correlation_id)
        if subprocess_name:
            logging.info ('%s: %s' % (subprocess_name, payload))
        else:
            logging.info(payload)

    def echo_subprocess_started(self, payload, correlation_id):
        name = payload.name
        if correlation_id:
            self._server_subprocess_names[correlation_id] = name
        logging.info('%s : STARTING' % name)

    def echo_subprocess_stopped(self, payload, correlation_id):
        try:
            name = self._server_subprocess_names.pop(correlation_id)
        except KeyError:
            name = 'Unknown process'
        logging.info('%s : FINISHED' % name)

    def get_configuration_data(self, payload, correlation_id):
        return self.GphlMessages.ConfigurationData(
            self.file_paths['gphl_beamline_config']
        )

    def query_collection_strategy(self, geometric_strategy):
        """Display collection strategy for user approval,
        and query parameters needed"""

        data_model = self._queue_entry.get_data_model()

        isInterleaved = geometric_strategy.isInterleaved
        allowed_widths = geometric_strategy.allowedWidths
        if allowed_widths:
            default_width_index = geometric_strategy.defaultWidthIdx or 0
        else:
            allowed_widths = [float(x) for x in
                              self.getProperty('default_image_widths').split()]
            val = allowed_widths[0]
            allowed_widths.sort()
            default_width_index = allowed_widths.index(val)
            logging.getLogger('HWR').info(
                "No allowed image widths returned by strategy - use defaults")

        # NBNB TODO userModifiable

        # NBNB The geometric strategy is only given for ONE beamsetting
        # The strategy is (for now) repeated identical for all wavelengths
        # When this changes, more info will become available

        # NBNB

        axis_names = self.rotation_axis_roles

        orientations = OrderedDict()
        strategy_length = 0
        detectorSetting = None
        beamSetting = None
        for sweep in geometric_strategy.sweeps:
            if detectorSetting is None:
                detectorSetting = sweep.detectorSetting
            if beamSetting is None:
                beamSetting = sweep.beamSetting
            strategy_length += sweep.width
            rotation_id = sweep.goniostatSweepSetting.id
            sweeps = orientations.get(rotation_id, [])
            sweeps.append(sweep)
            orientations[rotation_id] = sweeps

        lines = ["Geometric strategy   :"]
        if data_model.lattice_selected:
            # Data collection TODO: Use workflow info to distinguish
            total_width = 0
            beam_energies = data_model.get_beam_energies()
            for tag, energy in beam_energies.items():
                # NB beam_energies is an ordered dictionary
                lines.append("- %-18s %6.1f degrees at %s keV"
                             % (tag, strategy_length, energy))
                total_width += strategy_length
            lines.append("%-18s:  %6.1f degrees" % ("Total rotation",
                                                    total_width))
        else:
            # Charcterisation TODO: Use workflow info to distinguish
            lines.append("    - Beam Energy    : %7.1f keV"
                         % (ConvertUtils.h_over_e / beamSetting.wavelength))
            lines.append("    - Total rotation : %7.1f degrees"
                         % strategy_length)


        for rotation_id, sweeps in sorted(orientations.items()):
            goniostatRotation = sweeps[0].goniostatSweepSetting
            axis_settings = goniostatRotation.axisSettings
            scan_axis = goniostatRotation.scanAxis
            ss = ("\nOrientation: "
                  + ', '.join('%s= %6.1f' % (x, axis_settings.get(x))
                              for x in axis_names if x != scan_axis)
                  )
            lines.append(ss)
            for sweep in sweeps:
                start = sweep.start
                width = sweep.width
                ss = ("    - sweep %s=%8.1f, width= %s degrees"
                      % (scan_axis, start, width))
                lines.append(ss)
        info_text = '\n'.join(lines)

        acq_parameters = (
            self._queue_entry.beamline_setup.get_default_acquisition_parameters()
        )
        # For now return default values
        field_list = [
            {'variableName':'_info',
             'uiLabel':'Data collection plan',
             'type':'textarea',
             'defaultValue':info_text,
             },
            {'variableName':'imageWidth',
             'uiLabel':'Oscillation range',
             'type':'combo',
             'defaultValue':str(allowed_widths[default_width_index]),
             'textChoices':[str(x) for x in allowed_widths],
             },

            # NB Transmission is in % in UI, but in 0-1 in workflow
            {'variableName':'transmission',
             'uiLabel':'Transmission',
             'type':'text',
             'defaultValue':str(acq_parameters.transmission),
             'unit':'%',
             'lowerBound':0.0,
             'upperBound':100.0,
             },
            {'variableName':'exposure',
             'uiLabel':'Exposure Time',
             'type':'text',
             'defaultValue':str(acq_parameters.exp_time),
             'unit':'s',
             # NBNB TODO fill in from config
             'lowerBound':0.003,
             'upperBound':6000,
             },
        ]


        # First set beam_energy and give it time to settle,
        # so detector distance will trigger correct resolution later
        collect_hwobj = self._queue_entry.beamline_setup.getObjectByRole(
            'collect'
        )
        collect_hwobj.set_wavelength(beamSetting.wavelength)

        detectorDistance = detectorSetting.axisSettings.get('Distance')
        if detectorDistance:
            # NBNB If this is ever set to editable, distance and resolution
            # must be varied in sync
            collect_hwobj.move_detector(detectorDistance)
            resolution = collect_hwobj.get_resolution()
            field_list.append(
                {'variableName':'detector_distance',
                 'uiLabel':'Detector distance',
                 'type':'text',
                 'defaultValue':str(detectorDistance),
                 'readOnly':True,
                 }
            )
            field_list.append(
                {'variableName':'detector_resolution',
                 'uiLabel':'Equivalent detector resolution (A)',
                 'type':'text',
                 'defaultValue':str(resolution),
                 'readOnly':True,
                 }
            )
        else:
            logging.getLogger('HWR').warning(
                "Detector distance not set by workflow runner"
            )

        if isInterleaved:
            field_list.append({'variableName':'wedgeWidth',
                              'uiLabel':'Images per wedge',
                              'type':'text',
                              'defaultValue':'10',
                              'unit':'',
                              'lowerBound':0,
                              'upperBound':1000,}
                          )
        self._return_parameters = gevent.event.AsyncResult()
        responses = dispatcher.send('gphlParametersNeeded', self,
                                    field_list, self._return_parameters)
        if not responses:
            self._return_parameters.set_exception(
                RuntimeError("Signal 'gphlParametersNeeded' is not connected")
            )

        params = self._return_parameters.get()
        self._return_parameters = None
        result = {}
        tag = 'imageWidth'
        value = params.get(tag)
        if value:
            result[tag] = float(value)
        tag = 'exposure'
        value = params.get(tag)
        if value:
            result[tag] = float(value)
        tag = 'transmission'
        value = params.get(tag)
        if value:
            # Convert from % to fraction
            result[tag] = float(value)/100
        tag = 'wedgeWidth'
        value = params.get(tag)
        if value:
            result[tag] = int(value)
        # TODO NBNB must be modified if we make distance/resolution editable
        tag = 'detector_distance'
        value = params.get(tag)
        if value:
            collect_hwobj.move_detector(float(value))
            resolution = collect_hwobj.get_resolution()
            result['resolution'] = resolution
        if isInterleaved:
            result['interleaveOrder'] = data_model.get_interleave_order()

        return result

    def setup_data_collection(self, payload, correlation_id):
        geometric_strategy = payload
        # NB this call also asks for OK/abort of strategy, hence put first
        parameters = self.query_collection_strategy(geometric_strategy)
        # Put resolution value in workflow model object
        gphl_workflow_model = self._queue_entry.get_data_model()
        gphl_workflow_model.set_detector_resolution(parameters.pop('resolution'))

        user_modifiable = geometric_strategy.isUserModifiable
        if user_modifiable:
            # Query user for new rotationSetting and make it,
            logging.getLogger('HWR').warning(
                "User modification of sweep settings not implemented. Ignored"
            )

        goniostatSweepSettings = {}
        goniostatTranslations = []
        recen_parameters = {}
        sweeps = list(geometric_strategy.sweeps)
        sweepSetting = sweeps[0].goniostatSweepSetting
        translation = sweepSetting.translation
        startloop = 0
        if translation is None:
            recen_parameters = self.load_transcal_parameters()
            if recen_parameters:
                # Do first centring, by itself, so you can use the result for recen
                startloop = 1
                goniostatSweepSettings[sweepSetting.id] = sweepSetting
                qe = self.enqueue_sample_centring(
                    goniostatRotation=sweepSetting)
                translation = self.execute_sample_centring(
                        qe, sweepSetting, sweepSetting.id
                    )
                goniostatTranslations.append(translation)
                recen_parameters['ref_xyz'] = tuple(
                    translation.axisSettings[x]
                    for x in self.translation_axis_roles
                )
                recen_parameters['ref_okp'] = tuple(
                    sweepSetting.axisSettings[x]
                    for x in self.rotation_axis_roles
                )
                logging.getLogger('HWR').debug(
                    "Recentring set-up. Parameters are: %s"
                    % sorted(recen_parameters.items())
                )

            else:
                logging.getLogger('HWR').info(
                    "transcal.nml file not found - Automatic recentering skipped"
                )

        queue_entries = []
        for sweep in sweeps[startloop:]:
            sweepSetting = sweep.goniostatSweepSetting
            requestedRotationId = sweepSetting.id
            if requestedRotationId not in goniostatSweepSettings:
                okp = tuple(sweepSetting.axisSettings[x]
                            for x in self.rotation_axis_roles
                            )
                if recen_parameters and sweepSetting.translation is None:
                    dd = self.calculate_recentring(okp, **recen_parameters)

                    # Creating the Translation adds it to the Rotation
                    GphlMessages.GoniostatTranslation(
                        rotation=sweepSetting,
                        requestedRotationId=requestedRotationId, **dd
                    )
                    logging.getLogger('HWR').debug("Recentring. okp=%s, %s"
                                                   % (okp, sorted(dd.items())))
                else:
                    if sweepSetting.translation is None:
                        xx = "No translation settings."
                    else:
                        xx = sorted(
                            sweepSetting.translation.axisSettings.items()
                        )
                    logging.getLogger('HWR').debug(
                        "No recentring. okp=%s, %s" % (okp, xx)
                    )

                goniostatSweepSettings[requestedRotationId] = sweepSetting
                # NB there is no provision for NOT making a new translation
                # object if you are making no changes
                qe = self.enqueue_sample_centring(
                    goniostatRotation=sweepSetting)
                queue_entries.append(
                    (qe, sweepSetting, requestedRotationId)
                )

        # NB, split in two loops to get all centrings on queue (and so visible) before execution

        for qe, goniostatRotation, requestedRotationId in queue_entries:
            goniostatTranslations.append(
                self.execute_sample_centring(
                    qe, goniostatRotation, requestedRotationId
                )
            )

        sampleCentred = self.GphlMessages.SampleCentred(
            goniostatTranslations=goniostatTranslations,
            **parameters
        )
        return sampleCentred

    def load_transcal_parameters(self):
        """Load home_position and cross_sec_of_soc from transcal.nml"""
        fp = self.file_paths.get('transcal_file')
        if os.path.isfile(fp):
            try:
                transcal_data = f90nml.read(fp)['sdcp_instrument_list']
            except:
                logging.getLogger('HWR').error(
                    "Error reading transcal.nml file: %s" % fp
                )
            else:
                result = {}
                result['home_position'] = transcal_data.get('trans_home')
                result['cross_sec_of_soc'] = transcal_data.get(
                    'trans_cross_sec_of_soc'
                )
                if None in result.values():
                    logging.getLogger('HWR').warning(
                        "load_transcal_parameters failed"
                    )
                else:
                    return result
        else:
            logging.getLogger('HWR').warning(
                "transcal.nml file not found: %s" % fp
            )
        # If we get here reading failed
        return {}

    def calculate_recentring(self, okp, home_position, cross_sec_of_soc,
                             ref_okp, ref_xyz):
        """Add predicted traslation values using recen
        okp is the omega,gamma,phi tuple of the target position,
        home_position is the translation calibration home position,
        and cross_sec_of_soc is the cross-section of the sphere of confusion
        ref_okp and ref_xyz are the reference omega,gamma,phi and the
        corresponding x,y,z translation position"""

        # Make input file
        gphl_workflow_model = self._queue_entry.get_data_model()
        infile = os.path.join(
            gphl_workflow_model.path_template.process_directory,
            'temp_recen.in'
        )
        recen_data = OrderedDict()
        indata = {'recen_list':recen_data}

        fp = self.file_paths.get('instrumentation_file')
        instrumentation_data = f90nml.read(fp)['sdcp_instrument_list']
        diffractcal_data = instrumentation_data

        fp = self.file_paths.get('diffractcal_file')
        try:
            diffractcal_data = f90nml.read(fp)['sdcp_instrument_list']
        except:
            logging.getLogger('HWR').debug(
                "diffractcal file not present - using instrumentation.nml %s"
                % fp
            )
        ll = diffractcal_data['gonio_axis_dirs']
        recen_data['omega_axis'] = ll[:3]
        recen_data['kappa_axis'] = ll[3:6]
        recen_data['phi_axis'] = ll[6:]
        ll = instrumentation_data['gonio_centring_axis_dirs']
        recen_data['trans_1_axis'] = ll[:3]
        recen_data['trans_2_axis'] = ll[3:6]
        recen_data['trans_3_axis'] = ll[6:]
        recen_data['cross_sec_of_soc'] = cross_sec_of_soc
        recen_data['home'] = home_position
        #
        f90nml.write(indata, infile, force=True)

        # Get program locations
        recen_executable = self._workflow_connection.software_paths[
            'co.gphl.wf.recen.bin'
        ]
        # Get environmental variables
        envs = {'BDG_home':
                    self._workflow_connection.software_paths['BDG_home']
                }
        # Run recen
        command_list = [recen_executable,
                        '--input', infile,
                        '--init-xyz', "%s %s %s" % ref_xyz,
                        '--init-okp', "%s %s %s" % ref_okp,
                        '--okp', "%s %s %s" % okp,
                        ]
        #NB the universal_newlines has the NECESSARY side effect of converting
        # output from bytes to string (with default encoding),
        # avoiding an explicit decoding step.
        result = {}
        logging.getLogger('HWR').debug("Running Recen command: %s"
                                       % ' '.join(command_list))
        try:
            output = subprocess.check_output(command_list, env=envs,
                                             stderr=subprocess.STDOUT,
                                             universal_newlines=True)
        except subprocess.CalledProcessError as err:
            logging.getLogger('HWR').error(
                "Recen failed with returncode %s. Output was:\n%s"
                % (err.returncode, err.output)
            )
            return result

        terminated_ok = False
        for line in reversed(output.splitlines()):
            ss = line.strip()
            if terminated_ok:
                if 'X,Y,Z' in ss:
                    ll = ss.split()[-3:]
                    for ii, tag in enumerate(self.translation_axis_roles):
                        result[tag] = float(ll[ii])
                    break

            elif ss == 'NORMAL termination':
                terminated_ok = True
        else:
            logging.getLogger('HWR').error(
                "Recen failed with normal termination=%s. Output was:\n"
                % terminated_ok
                + output
            )
        #
        return result

    def collect_data(self, payload, correlation_id):
        collection_proposal = payload

        beamline_setup_hwobj = self._queue_entry.beamline_setup
        queue_manager = self._queue_entry.get_queue_controller()

        # NBNB creation and use of master_path_template is NOT in testing version yet
        gphl_workflow_model = self._queue_entry.get_data_model()
        master_path_template = gphl_workflow_model.path_template
        relative_image_dir = collection_proposal.relativeImageDir

        new_dcg_name = 'GPhL Data Collection'
        new_dcg_model = queue_model_objects.TaskGroup()
        new_dcg_model.set_enabled(True)
        new_dcg_model.set_name(new_dcg_name)
        new_dcg_model.set_number(
            gphl_workflow_model.get_next_number_for_name(new_dcg_name)
        )
        self._add_to_queue(gphl_workflow_model, new_dcg_model)

        sample = gphl_workflow_model.get_sample_node()
        # There will be exactly one for the kinds of collection we are doing
        crystal = sample.crystals[0]
        data_collections = []
        snapshot_count = gphl_workflow_model.get_snapshot_count()
        for scan in collection_proposal.scans:
            sweep = scan.sweep
            acq = queue_model_objects.Acquisition()

            # Get defaults, even though we override most of them
            acq_parameters = (
                beamline_setup_hwobj.get_default_acquisition_parameters()
            )
            acq.acquisition_parameters = acq_parameters

            acq_parameters.first_image = scan.imageStartNum
            acq_parameters.num_images = scan.width.numImages
            acq_parameters.osc_start = scan.start
            acq_parameters.osc_range = scan.width.imageWidth
            logging.getLogger('HWR').info(
                "Scan: %s images of %s deg. starting at %s (%s deg)"
                % (acq_parameters.num_images, acq_parameters.osc_range,
                   acq_parameters.first_image, acq_parameters.osc_start)
            )
            # acq_parameters.kappa = self._get_kappa_axis_position()
            # acq_parameters.kappa_phi = self._get_kappa_phi_axis_position()
            # acq_parameters.overlap = overlap
            acq_parameters.exp_time = scan.exposure.time
            acq_parameters.num_passes = 1
            acq_parameters.resolution = gphl_workflow_model.get_detector_resolution()
            acq_parameters.energy = (ConvertUtils.h_over_e
                                     / sweep.beamSetting.wavelength)
            acq_parameters.transmission = scan.exposure.transmission * 100
            # acq_parameters.shutterless = self._has_shutterless()
            # acq_parameters.detector_mode = self._get_roi_modes()
            acq_parameters.inverse_beam = False
            # acq_parameters.take_dark_current = True
            # acq_parameters.skip_existing_images = False

            # Only snapshots before first scan
            acq_parameters.take_snapshots = snapshot_count
            snapshot_count = 0

            # Edna also sets screening_id
            # Edna also sets osc_end

            goniostatRotation = sweep.goniostatSweepSetting
            goniostatTranslation = goniostatRotation.translation
            dd = dict((x, goniostatRotation.axisSettings[x])
                      for x in self.rotation_axis_roles)

            if goniostatTranslation is not None:
                for tag in self.translation_axis_roles:
                    val = goniostatTranslation.axisSettings.get(tag)
                    if val is not None:
                        dd[tag] = val
            dd[goniostatRotation.scanAxis] = scan.start
            acq_parameters.centred_position = (
                queue_model_objects.CentredPosition(dd)
            )

            # Path_template
            path_template = queue_model_objects.PathTemplate()
            # Naughty, but we want a clone, right?
            # NBNB this ONLY works because all the attributes are immutable values
            path_template.__dict__.update(master_path_template.__dict__)
            if relative_image_dir:
                path_template.directory = os.path.join(
                    path_template.directory, relative_image_dir
                )
                path_template.process_directory = os.path.join(
                    path_template.process_directory, relative_image_dir
                )
            acq.path_template = path_template
            filename_params = scan.filenameParams
            subdir = filename_params.get('subdir')
            if subdir:
                path_template.directory = os.path.join(path_template.directory,
                                                       subdir)
                path_template.process_directory = os.path.join(
                    path_template.process_directory, subdir
                )
            ss = filename_params.get('run')
            path_template.run_number = int(ss) if ss else 1
            prefix = filename_params.get('prefix', '')
            ib_component = filename_params.get('inverse_beam_component_sign',
                                               '')
            ll = []
            if prefix:
                ll.append(prefix)
            if ib_component:
                ll.append(ib_component)
            path_template.base_prefix = '_'.join(ll)
            path_template.mad_prefix = (
                filename_params.get('beam_setting_index') or ''
            )
            path_template.wedge_prefix = (
                filename_params.get('gonio_setting_index') or ''
            )
            path_template.start_num = acq_parameters.first_image
            path_template.num_files = acq_parameters.num_images

            data_collection = queue_model_objects.DataCollection([acq], crystal)
            data_collections.append(data_collection)

            data_collection.set_enabled(True)
            data_collection.set_name(path_template.get_prefix())
            data_collection.set_number(path_template.run_number)
            self._add_to_queue(new_dcg_model, data_collection)

        data_collection_entry = queue_manager.get_entry_with_model(
            new_dcg_model
        )
        queue_manager.execute_entry(data_collection_entry)

        if data_collection_entry.status == QUEUE_ENTRY_STATUS.FAILED:
            # TODO NBNB check if these status codes are corerct
            status = 1
        else:
            status = 0

        # NB, uses last path_template,
        # but directory should be the same for all
        return self.GphlMessages.CollectionDone(
            status=status,
            proposalId=collection_proposal.id,
            # Only if you want to override prior information rootdir, which we do not
            # imageRoot=path_template.directory
        )

    def select_lattice(self, payload, correlation_id):
        choose_lattice = payload

        solution_format = choose_lattice.format

        # Must match bravaisLattices column
        lattices = choose_lattice.lattices

        # First letter must match first letter of BravaisLattice
        crystal_system = choose_lattice.crystalSystem

        # Color green (figuratively) if matches lattices,
        # or otherwise if matches crystalSystem

        dd = self.parse_indexing_solution(solution_format,
                                          choose_lattice.solutions)

        field_list = [
            {'variableName':'_cplx',
             'uiLabel':'Select indexing solution:',
             'type':'selection_table',
             'header':dd['header'],
             'colours':None,
             'defaultValue':(dd['solutions'],),
             },
        ]

        # colour matching lattices green
        colour_check = lattices
        if crystal_system and not colour_check:
            colour_check = (crystal_system,)
        if colour_check:
            colours = [None] * len(dd['solutions'])
            for ii, line in enumerate(dd['solutions']):
                if any(x in line for x in colour_check):
                    colours[ii] = 'LIGHT_GREEN'
            field_list[0]['colours'] = colours

        self._return_parameters = gevent.event.AsyncResult()
        responses = dispatcher.send('gphlParametersNeeded', self,
                                    field_list, self._return_parameters)
        if not responses:
            self._return_parameters.set_exception(
                RuntimeError("Signal 'gphlParametersNeeded' is not connected")
            )

        params = self._return_parameters.get()
        ll = str(params['_cplx'][0]).split()
        if ll[0] == '*':
            del ll[0]
        #
        self._queue_entry.get_data_model().lattice_selected = True
        return  self.GphlMessages.SelectedLattice(format=solution_format,
                                                  solution=ll)

    def parse_indexing_solution(self, solution_format, text):

        # Solution table. for format IDXREF will look like
        """
*********** DETERMINATION OF LATTICE CHARACTER AND BRAVAIS LATTICE ***********

 The CHARACTER OF A LATTICE is defined by the metrical parameters of its
 reduced cell as described in the INTERNATIONAL TABLES FOR CRYSTALLOGRAPHY
 Volume A, p. 746 (KLUWER ACADEMIC PUBLISHERS, DORDRECHT/BOSTON/LONDON, 1989).
 Note that more than one lattice character may have the same BRAVAIS LATTICE.

 A lattice character is marked "*" to indicate a lattice consistent with the
 observed locations of the diffraction spots. These marked lattices must have
 low values for the QUALITY OF FIT and their implicated UNIT CELL CONSTANTS
 should not violate the ideal values by more than
 MAXIMUM_ALLOWED_CELL_AXIS_RELATIVE_ERROR=  0.03
 MAXIMUM_ALLOWED_CELL_ANGLE_ERROR=           1.5 (Degrees)

  LATTICE-  BRAVAIS-   QUALITY  UNIT CELL CONSTANTS (ANGSTROEM & DEGREES)
 CHARACTER  LATTICE     OF FIT      a      b      c   alpha  beta gamma

 *  44        aP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  31        aP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  33        mP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  35        mP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  34        mP          0.0      56.3  102.3   56.3  90.0  90.0  90.0
 *  32        oP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  14        mC          0.1      79.6   79.6  102.3  90.0  90.0  90.0
 *  10        mC          0.1      79.6   79.6  102.3  90.0  90.0  90.0
 *  13        oC          0.1      79.6   79.6  102.3  90.0  90.0  90.0
 *  11        tP          0.1      56.3   56.3  102.3  90.0  90.0  90.0
    37        mC        250.0     212.2   56.3   56.3  90.0  90.0  74.6
    36        oC        250.0      56.3  212.2   56.3  90.0  90.0 105.4
    28        mC        250.0      56.3  212.2   56.3  90.0  90.0  74.6
    29        mC        250.0      56.3  125.8  102.3  90.0  90.0  63.4
    41        mC        250.0     212.3   56.3   56.3  90.0  90.0  74.6
    40        oC        250.0      56.3  212.2   56.3  90.0  90.0 105.4
    39        mC        250.0     125.8   56.3  102.3  90.0  90.0  63.4
    30        mC        250.0      56.3  212.2   56.3  90.0  90.0  74.6
    38        oC        250.0      56.3  125.8  102.3  90.0  90.0 116.6
    12        hP        250.1      56.3   56.3  102.3  90.0  90.0  90.0
    27        mC        500.0     125.8   56.3  116.8  90.0 115.5  63.4
    42        oI        500.0      56.3   56.3  219.6 104.8 104.8  90.0
    15        tI        500.0      56.3   56.3  219.6  75.2  75.2  90.0
    26        oF        625.0      56.3  125.8  212.2  83.2 105.4 116.6
     9        hR        750.0      56.3   79.6  317.1  90.0 100.2 135.0
     1        cF        999.0     129.6  129.6  129.6 128.6  75.7 128.6
     2        hR        999.0      79.6  116.8  129.6 118.9  90.0 109.9
     3        cP        999.0      56.3   56.3  102.3  90.0  90.0  90.0
     5        cI        999.0     116.8   79.6  116.8  70.1  39.8  70.1
     4        hR        999.0      79.6  116.8  129.6 118.9  90.0 109.9
     6        tI        999.0     116.8  116.8   79.6  70.1  70.1  39.8
     7        tI        999.0     116.8   79.6  116.8  70.1  39.8  70.1
     8        oI        999.0      79.6  116.8  116.8  39.8  70.1  70.1
    16        oF        999.0      79.6   79.6  219.6  90.0 111.2  90.0
    17        mC        999.0      79.6   79.6  116.8  70.1 109.9  90.0
    18        tI        999.0     116.8  129.6   56.3  64.3  90.0 118.9
    19        oI        999.0      56.3  116.8  129.6  61.1  64.3  90.0
    20        mC        999.0     116.8  116.8   56.3  90.0  90.0 122.4
    21        tP        999.0      56.3  102.3   56.3  90.0  90.0  90.0
    22        hP        999.0      56.3  102.3   56.3  90.0  90.0  90.0
    23        oC        999.0     116.8  116.8   56.3  90.0  90.0  57.6
    24        hR        999.0     162.2  116.8   56.3  90.0  69.7  77.4
    25        mC        999.0     116.8  116.8   56.3  90.0  90.0  57.6
    43        mI        999.0      79.6  219.6   56.3 104.8 135.0  68.8

 For protein crystals the possible space group numbers corresponding  to"""

        # find headers lines
        solutions = []
        if solution_format == 'IDXREF':
            lines = text.splitlines()
            for indx in range(len(lines)):
                if 'BRAVAIS-' in lines[indx]:
                    # Used as marker for first header line
                    header = ['%s\n%s' % (lines[indx], lines[indx + 1])]
                    break
            else:
                raise ValueError(
                    "Substring 'BRAVAIS-' missing in %s indexing solution")

            for indx in range(indx, len(lines)):
                line = lines[indx]
                ss = line.strip()
                if ss:
                    # we are skipping blank line at the start
                    if solutions or ss[0] == '*':
                        # First real line will start with a '*
                        # Subsequent non=-empty lines will also be used
                        solutions.append(line)
                elif solutions:
                    # we have finished - empty non-initial line
                    break

            #
            return {'header':header, 'solutions':solutions}
        else:
            raise ValueError("GPhL: Indexing format %s is not known"
                             % repr(solution_format))

    def process_centring_request(self, payload, correlation_id):
        # Used for transcal only - anything else is data collection related
        request_centring = payload

        logging.getLogger('user_level_log').info ('Start centring no. %s of %s'
                      % (request_centring.currentSettingNo,
                         request_centring.totalRotations))

        ## Rotate sample to RotationSetting
        goniostatRotation = request_centring.goniostatRotation
        # goniostatTranslation = goniostatRotation.translation
        #

        if request_centring.currentSettingNo < 2:
            # Start without fine zoom setting
            self._use_fine_zoom = False
        elif (not self._use_fine_zoom
              and goniostatRotation.translation is not None):
            # We are moving to having recentered positions -
            # Set or prompt for fine zoom
            self._use_fine_zoom = True
            # TODO Check correct way to get hold of zoom motor
            zoom_motor = self._queue_entry.beamline_setup.getObjectByRole('zoom')
            if zoom_motor:
                # Zoom to the last predefined position
                # - that should be the largest magnification
                ll = zoom_motor.getPredefinedPositionsList()
                if ll:
                    logging.getLogger('user_level_log').info (
                        'Sample re-centering now active - Zooming in.')
                    zoom_motor.moveToPosition(ll[-1])
                else:
                    logging.getLogger('HWR').warning (
                        'No predefined positions for zoom motor.')
            else:
                # Ask user to zoom
                info_text = """Automatic sample re-centering is now active
    Switch to maximum zoom before continuing"""
                field_list = [
                    {'variableName':'_info',
                     'uiLabel':'Data collection plan',
                     'type':'textarea',
                     'defaultValue':info_text,
                     },
                ]
                self._return_parameters = gevent.event.AsyncResult()
                responses = dispatcher.send('gphlParametersNeeded', self,
                                            field_list, self._return_parameters)
                if not responses:
                    self._return_parameters.set_exception(
                        RuntimeError("Signal 'gphlParametersNeeded' is not connected")
                    )

                dummy = self._return_parameters.get()
                self._return_parameters = None

        centring_queue_entry = self.enqueue_sample_centring(goniostatRotation)
        goniostatTranslation = self.execute_sample_centring(centring_queue_entry,
                                                            goniostatRotation)

        if (request_centring.currentSettingNo >=
                request_centring.totalRotations):
            returnStatus = 'DONE'
        else:
            returnStatus = 'NEXT'
        #
        return self.GphlMessages.CentringDone(
            returnStatus, timestamp=time.time(),
            goniostatTranslation=goniostatTranslation
        )

    def enqueue_sample_centring(self, goniostatRotation):

        queue_manager = self._queue_entry.get_queue_controller()

        goniostatTranslation = goniostatRotation.translation

        dd = dict((x, goniostatRotation.axisSettings[x])
                  for x in self.rotation_axis_roles)
        if goniostatTranslation is not None:
            for tag in self.translation_axis_roles:
                val = goniostatTranslation.axisSettings.get(tag)
                if val is not None:
                    dd[tag] = val

        centring_model = queue_model_objects.SampleCentring(motor_positions=dd)
        self._add_to_queue(self._queue_entry.get_data_model(), centring_model)
        centring_entry = queue_manager.get_entry_with_model(centring_model)

        return centring_entry

    def execute_sample_centring(self, centring_entry, goniostatRotation,
                                requestedRotationId=None):

        queue_manager = self._queue_entry.get_queue_controller()
        queue_manager.execute_entry(centring_entry)

        centring_result = centring_entry.get_data_model().get_centring_result()
        if centring_result:
            positionsDict = centring_result.as_dict()
            dd = dict((x, positionsDict[x])
                      for x in self.translation_axis_roles)
            return self.GphlMessages.GoniostatTranslation(
                rotation=goniostatRotation,
                requestedRotationId=requestedRotationId, **dd
            )
        else:
            self.abort("No Centring result found")

    def prepare_for_centring(self, payload, correlation_id):

        # TODO Add pop-up confirmation box ('Ready for centring?')

        return self.GphlMessages.ReadyForCentring()

    def obtain_prior_information(self, payload, correlation_id):

        workflow_model = self._queue_entry.get_data_model()
        sample_model = workflow_model.get_sample_node()

        wavelengths = []
        beam_energies = workflow_model.get_beam_energies()
        if beam_energies:
            for role, value in beam_energies.items():
                wavelength = ConvertUtils.h_over_e / value
                wavelengths.append(
                    self.GphlMessages.PhasingWavelength(wavelength=wavelength,
                                                        role=role)
                )
        else:
            wavelengths.append(
                self.GphlMessages.PhasingWavelength(wavelength=DUMMY_WAVELENGTH)
            )

        cell_params = workflow_model.get_cell_parameters()
        if cell_params:
            unitCell = self.GphlMessages.UnitCell(*cell_params)
        else:
            unitCell = None

        obj = queue_model_enumerables.SPACEGROUP_MAP.get(
            workflow_model.get_space_group()
        )
        space_group = obj.number if obj else None

        crystal_system = workflow_model.get_crystal_system()
        if crystal_system:
            crystal_system = crystal_system.upper()

        userProvidedInfo = self.GphlMessages.UserProvidedInfo(
            scatterers=(),
            lattice=crystal_system,
            pointGroup=workflow_model.get_point_group(),
            spaceGroup=space_group,
            cell=unitCell,
            expectedResolution=workflow_model.get_expected_resolution(),
            isAnisotropic=None,
            phasingWavelengths=wavelengths
        )
        ll = ['PriorInformation']
        for tag in ('expectedResolution', 'isAnisotropic', 'lattice',
                    'pointGroup', 'scatterers', 'spaceGroup'):
            val = getattr(userProvidedInfo, tag)
            if val:
                ll.append('%s=%s' % (tag, val))
        if beam_energies:
            ll.extend('%s=%s' % (x.role, x.wavelength) for x in wavelengths)
        if cell_params:
            ll.append('cell_parameters=%s' % (cell_params,))
        logging.getLogger('HWR').debug(', '.join(ll))

        # Look for existing uuid
        for text in sample_model.lims_code, sample_model.code, sample_model.name:
            if text:
                try:
                    sampleId = uuid.UUID(text)
                except:
                    # The error expected if this goes wrong is ValueError.
                    # But whatever the error we want to continue
                    pass
                else:
                    # Text was a valid uuid string. Use the uuid.
                    break
        else:
            sampleId = uuid.uuid1()

        # TODO re-check if this is correct
        rootDirectory = workflow_model.path_template.directory

        priorInformation = self.GphlMessages.PriorInformation(
            sampleId=sampleId,
            sampleName=(sample_model.name or sample_model.code
                        or sample_model.lims_code or
                        workflow_model.path_template.get_prefix()
                        or str(sampleId)),
            rootDirectory=rootDirectory,
            userProvidedInfo=userProvidedInfo
        )
        #
        return priorInformation
