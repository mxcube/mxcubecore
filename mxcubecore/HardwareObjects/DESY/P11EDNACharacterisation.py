import os
import logging
import time
import copy

from mxcubecore.model import queue_model_objects as qmo
from mxcubecore.model import queue_model_enumerables as qme

from mxcubecore.HardwareObjects.SecureXMLRpcRequestHandler import (
    SecureXMLRpcRequestHandler,
)
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractCharacterisation import (
    AbstractCharacterisation,
)

from mxcubecore.HardwareObjects.EDNACharacterisation import EDNACharacterisation

from XSDataMXCuBEv1_4 import XSDataInputMXCuBE
from XSDataMXCuBEv1_4 import XSDataMXCuBEDataSet
from XSDataMXCuBEv1_4 import XSDataResultMXCuBE

from XSDataCommon import XSDataAngle
from XSDataCommon import XSDataBoolean
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataImage
from XSDataCommon import XSDataFlux
from XSDataCommon import XSDataLength
from XSDataCommon import XSDataTime
from XSDataCommon import XSDataWavelength
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataSize
from XSDataCommon import XSDataString

# from edna_test_data import EDNA_DEFAULT_INPUT
# from edna_test_data import EDNA_TEST_DATA


class P11EDNACharacterisation(EDNACharacterisation):
    def __init__(self, name):
        super().__init__(name)

        self.collect_obj = None
        self.result = None
        self.edna_default_file = None
        self.start_edna_command = None

    def _run_edna(self, input_file, results_file, process_directory):
        # First submit MOSFLM job
        self.mosflm_maxwell()

        """Starts EDNA"""
        msg = "Starting EDNA characterisation using xml file %s" % input_file
        logging.getLogger("queue_exec").info(msg)

        args = (self.start_edna_command, input_file, results_file, process_directory)
        # subprocess.call("%s %s %s %s" % args, shell=True)

        # Test run DESY
        self.edna_maxwell(process_directory, input_file, results_file)

        self.result = None
        if os.path.exists(results_file):
            self.result = XSDataResultMXCuBE.parseFile(results_file)

        return self.result

    def mosflm_maxwell(self):
        self.log.debug("==== MOSFLM CHARACTERISATION IN PROGRESS ==========")

        # Retrieve resolution value and number of frames
        resolution = HWR.beamline.resolution.get_value()
        frames = HWR.beamline.collect.current_dc_parameters["oscillation_sequence"][0][
            "number_of_images"
        ]

        # Fetch the latest local master image filename
        latest_h5_filename = HWR.beamline.detector.get_latest_local_master_image_name()

        # Prepare local and remote image directory paths
        image_dir_local, filename = os.path.split(latest_h5_filename)
        remote_base_path = HWR.beamline.session.get_beamtime_metadata()[2]
        image_dir = image_dir_local.replace("/gpfs/current", remote_base_path)
        process_dir_local = image_dir_local.replace("/raw/", "/processed/")
        process_dir = image_dir.replace("/raw/", "/processed/")
        mosflm_path_local = os.path.join(process_dir_local, "mosflm")
        mosflm_path = os.path.join(process_dir, "mosflm")

        self.log.debug(f'============MOSFLM======== mosflm_path="{mosflm_path}"')
        self.log.debug(
            f'============MOSFLM======== mosflm_path_local="{mosflm_path_local}"'
        )

        # Create local MOSFLM directory
        try:
            self.mkdir_with_mode(mosflm_path_local, mode=0o777)
            self.log.debug("=========== MOSFLM ============ Mosflm directory created")
        except OSError as e:
            self.log.debug(f"Cannot create mosflm directory: {e}")

        # Update datasets.txt file for presenterd
        base_process_dir = HWR.beamline.collect.base_dir(process_dir_local, "processed")
        datasets_file = os.path.join(base_process_dir, "datasets.txt")
        try:
            with open(datasets_file, "a") as file:
                file.write(
                    f"{mosflm_path_local.split('/gpfs/current/processed/')[1]}\n"
                )
        except (OSError, RuntimeWarning) as err:
            self.log.debug(f"Cannot write to datasets.txt: {err}")

        # Create SBATCH command
        ssh = HWR.beamline.session.get_ssh_command()
        log_file_path = (
            mosflm_path.replace(remote_base_path, "/beamline/p11/current")
            + "/mosflm.log"
        )
        sbatch = HWR.beamline.session.get_sbatch_command(
            jobname_prefix="mosflm", logfile_path=log_file_path
        )

        # Formulate processing command
        cmd = (
            f"/asap3/petra3/gpfs/common/p11/processing/mosflm_sbatch.sh "
            f"{image_dir} {filename} {mosflm_path.replace(remote_base_path, '/beamline/p11/current')} "
            f"{frames} {resolution}"
        )

        # Log and execute the command
        self.log.debug(f'=======MOSFLM========== ssh="{ssh}"')
        self.log.debug(f'=======MOSFLM========== sbatch="{sbatch}"')
        self.log.debug(f'=======MOSFLM========== executing process cmd="{cmd}"')
        full_cmd = f'{ssh} "{sbatch} --wrap \\"{cmd}\\""'
        self.log.debug(f"=======MOSFLM========== {full_cmd}")

        os.system(full_cmd)

    def edna_maxwell(self, process_directory, inputxml, outputxml):
        """
        Executes a command on a remote cluster using SSH and SBATCH for EDNA processing.

        :param process_directory: Directory where the processing will take place.
        :param inputxml: Path to the input XML file.
        :param outputxml: Path to the output XML file that will be generated.
        """
        self.log.debug(f'=======EDNA========== PROCESS DIRECTORY="{process_directory}"')
        self.log.debug(f'=======EDNA========== IN (XML INPUT)="{inputxml}"')
        self.log.debug(f'=======EDNA========== OUT (XML OUTPUT)="{outputxml}"')

        ssh = HWR.beamline.session.get_ssh_command()
        sbatch = HWR.beamline.session.get_sbatch_command(
            jobname_prefix="edna",
            logfile_path=process_directory.replace("/gpfs", "/beamline/p11")
            + "/edna.log",
        )

        inxml = inputxml.replace("/gpfs", "/beamline/p11")
        outxml = outputxml.replace(
            "/gpfs/current/processed", "/beamline/p11/current/processed"
        )

        processpath = process_directory.replace(
            "/gpfs/current/processed", "/beamline/p11/current/processed"
        )

        self.log.debug(
            f'=======EDNA========== CLUSTER PROCESS DIRECTORY="{processpath}"'
        )
        self.log.debug(f'=======EDNA========== CLUSTER IN="{inxml}"')
        self.log.debug(f'=======EDNA========== CLUSTER OUT="{outxml}"')
        self.log.debug(f'=======EDNA========== ssh="{ssh}"')
        self.log.debug(f'=======EDNA========== sbatch="{sbatch}"')

        cmd = f"/asap3/petra3/gpfs/common/p11/processing/edna_sbatch.sh {inxml} {outxml} {processpath}"

        self.log.debug(f'=======EDNA========== executing process cmd="{cmd}"')
        self.log.debug(f'=======EDNA========== {ssh} "{sbatch} --wrap \\"{cmd}\\""')
        logging.info(f'{ssh} "{sbatch} --wrap \\"{cmd}\\""')

        waitforxml = outputxml.replace("/raw/", "/processed/")
        self.log.debug(f"=======EDNA========== WAITING FOR OUTPUTXML IN {waitforxml}")

        self.log.debug(f'=======EDNA Script========== {ssh} "{cmd}"')
        os.system(f'{ssh} "{cmd}"')

        self.wait_for_file(waitforxml, timeout=60)

        # Update datasets.txt file for presenterd
        base_process_dir = "/gpfs/current/processed"
        datasets_file = os.path.join(base_process_dir, "datasets.txt")
        try:
            with open(datasets_file, "a") as file:
                file.write(
                    f"{process_directory.split('/gpfs/current/processed/')[1]}\n"
                )
        except (OSError, RuntimeWarning) as err:
            self.log.debug(f"Cannot write to datasets.txt: {err}")

    def wait_for_file(self, file_path, timeout=60, check_interval=1):
        start_time = time.time()
        while not os.path.exists(file_path):
            elapsed_time = time.time() - start_time
            if elapsed_time >= timeout:
                self.log.debug(
                    f"Timeout reached. File '{file_path}' not found within {timeout} seconds."
                )
                raise RuntimeWarning(
                    f"Timeout reached. File '{file_path}' not found within {timeout} seconds."
                )
            self.log.info(
                f"Waiting for file '{file_path}'... ({elapsed_time:.1f}/{timeout} seconds elapsed)"
            )
            time.sleep(check_interval)
        self.log.info(f"File '{file_path}' found.")

    def input_from_params(self, data_collection, char_params):
        edna_input = XSDataInputMXCuBE.parseString(self.edna_default_input)

        if data_collection.id:
            edna_input.setDataCollectionId(XSDataInteger(data_collection.id))

        # Beam object
        beam = edna_input.getExperimentalCondition().getBeam()

        try:
            transmission = HWR.beamline.transmission.get_value()
            beam.setTransmission(XSDataDouble(transmission))
        except AttributeError:
            import traceback

            logging.getLogger("HWR").debug(
                "EDNACharacterisation. transmission not saved "
            )
            logging.getLogger("HWR").debug(traceback.format_exc())

        try:
            wavelength = HWR.beamline.energy.get_wavelength()
            beam.setWavelength(XSDataWavelength(wavelength))
        except AttributeError:
            pass

        try:
            # Flux get_value() subsequently executing measure_flux() to fill in the dictionary

            beam.setFlux(XSDataFlux(HWR.beamline.flux.get_value()))
        except AttributeError:
            pass

        try:
            min_exp_time = self.collect_obj.detector_hwobj.get_exposure_time_limits()[0]
            beam.setMinExposureTimePerImage(XSDataTime(min_exp_time))
        except AttributeError:
            pass

        try:
            beamsize = self.collect_obj.beam_info_hwobj.get_beam_size()

            if None not in beamsize:
                beam.setSize(
                    XSDataSize(
                        x=XSDataLength(float(beamsize[0])),
                        y=XSDataLength(float(beamsize[1])),
                    )
                )
        except AttributeError:
            pass

        # Optimization parameters
        diff_plan = edna_input.getDiffractionPlan()

        aimed_i_sigma = XSDataDouble(char_params.aimed_i_sigma)
        aimed_completness = XSDataDouble(char_params.aimed_completness)
        aimed_multiplicity = XSDataDouble(char_params.aimed_multiplicity)
        aimed_resolution = XSDataDouble(char_params.aimed_resolution)

        complexity = char_params.strategy_complexity
        complexity = XSDataString(qme.STRATEGY_COMPLEXITY[complexity])

        permitted_phi_start = XSDataAngle(char_params.permitted_phi_start)
        _range = char_params.permitted_phi_end - char_params.permitted_phi_start
        rotation_range = XSDataAngle(_range)

        if char_params.aimed_i_sigma:
            diff_plan.setAimedIOverSigmaAtHighestResolution(aimed_i_sigma)

        if char_params.aimed_completness:
            diff_plan.setAimedCompleteness(aimed_completness)

        if char_params.use_aimed_multiplicity:
            diff_plan.setAimedMultiplicity(aimed_multiplicity)

        if char_params.use_aimed_resolution:
            diff_plan.setAimedResolution(aimed_resolution)

        diff_plan.setComplexity(complexity)
        diff_plan.setStrategyType(XSDataString(char_params.strategy_program))

        if char_params.use_permitted_rotation:
            diff_plan.setUserDefinedRotationStart(permitted_phi_start)
            diff_plan.setUserDefinedRotationRange(rotation_range)

        # Vertical crystal dimension
        sample = edna_input.getSample()
        sample.getSize().setY(XSDataLength(char_params.max_crystal_vdim))
        sample.getSize().setZ(XSDataLength(char_params.min_crystal_vdim))

        # Radiation damage model
        sample.setSusceptibility(XSDataDouble(char_params.rad_suscept))
        sample.setChemicalComposition(None)
        sample.setRadiationDamageModelBeta(XSDataDouble(char_params.beta / 1e6))
        sample.setRadiationDamageModelGamma(XSDataDouble(char_params.gamma / 1e6))

        diff_plan.setForcedSpaceGroup(XSDataString(char_params.space_group))

        # Characterisation type - Routine DC
        if char_params.use_min_dose:
            pass

        if char_params.use_min_time:
            time = XSDataTime(char_params.min_time)
            diff_plan.setMaxExposureTimePerDataCollection(time)

        # Account for radiation damage
        if char_params.induce_burn:
            self._modify_strategy_option(diff_plan, "-DamPar")

        # Characterisation type - SAD
        if char_params.opt_sad:
            if char_params.auto_res:
                diff_plan.setAnomalousData(XSDataBoolean(True))
            else:
                diff_plan.setAnomalousData(XSDataBoolean(False))
                self._modify_strategy_option(diff_plan, "-SAD yes")
                diff_plan.setAimedResolution(XSDataDouble(char_params.sad_res))
        else:
            diff_plan.setAnomalousData(XSDataBoolean(False))

        # Data set
        data_set = XSDataMXCuBEDataSet()
        acquisition_parameters = data_collection.acquisitions[0].acquisition_parameters
        path_template = data_collection.acquisitions[0].path_template

        # NB!: path_template content is in queue_model_objects.py
        logging.info(
            "======= Characterisation path template directory ====%s",
            path_template.directory,
        )
        logging.info(
            "======= Characterisation path template process_directory ====%s",
            path_template.process_directory,
        )
        logging.info(
            "======= Characterisation path template xds_dir ====%s",
            path_template.xds_dir,
        )
        logging.info(
            "======= Characterisation path template base_prefix ====%s",
            path_template.base_prefix,
        )
        logging.info(
            "======= Characterisation path template mad_prefix ====%s",
            path_template.mad_prefix,
        )
        logging.info(
            "======= Characterisation path template reference_image_prefix ====%s",
            path_template.reference_image_prefix,
        )
        logging.info(
            "======= Characterisation path template wedge_prefix ====%s",
            path_template.wedge_prefix,
        )
        logging.info(
            "======= Characterisation path template run_number ====%s",
            str(path_template.run_number),
        )
        logging.info(
            "======= Characterisation path template suffix ====%s", path_template.suffix
        )
        logging.info(
            "======= Characterisation path template precision ====%s",
            str(path_template.precision),
        )
        logging.info(
            "======= Characterisation path template start_num ====%s",
            str(path_template.start_num),
        )
        logging.info(
            "======= Characterisation path template num_files ====%s",
            str(path_template.num_files),
        )
        logging.info(
            "======= Characterisation path template compression ====%s",
            path_template.compression,
        )

        # Make sure there is a proper path conversion between different mount points

        # This is where the folder with h5 files is located.
        # It is straightforward to construct it from xds_dir
        image_dir = path_template.xds_dir.replace(
            "/gpfs/current/processed/", "/beamline/p11/current/raw/"
        ).replace("/edna", "")

        # This is needed because EDNA needs to concert eiger2cbf in place
        # The directory is created by local user, EDNA process is executed by another without
        # access rights.
        raw_char_directory = path_template.xds_dir.replace(
            "/gpfs/current/processed/", "/gpfs/current/raw/"
        ).replace("/edna", "")
        os.system(f"chmod +777 {raw_char_directory}")

        # Here is actual path to the *.h5 data are defined:
        # It is expected to be %5d (4 zeros), but files are generated %6d (5 leading zeros).
        # It also requires _data_%6d.h5
        # TODO: Fix elsewhere.
        path_template.precision = 6

        path_str = os.path.join(image_dir, path_template.get_image_file_name())

        logging.info(
            "======= Characterisation path of what image filename is expected ====%s",
            path_template.get_image_file_name(),
        )
        logging.info(
            "======= Characterisation path where to search for images ====%s", path_str
        )

        # NB!: Directories at this point are created elswhere (data_collection_hook)
        # xds_dir at this point already has all the needed substitutions.
        characterisation_dir = path_template.xds_dir

        # pattern = r"(_\d{6}\.h5)$"

        for img_num in range(int(acquisition_parameters.num_images)):
            image_file = XSDataImage()
            path = XSDataString()
            path.value = path_str % (img_num + 1)
            image_file.path = path
            image_file.path.value,
            image_file.number = XSDataInteger(img_num + 1)
            data_set.addImageFile(image_file)

        edna_input.addDataSet(data_set)
        edna_input.process_directory = characterisation_dir

        return edna_input

    def dc_from_output(self, edna_result, reference_image_collection):
        data_collections = []

        crystal = copy.deepcopy(reference_image_collection.crystal)
        ref_proc_params = reference_image_collection.processing_parameters
        processing_parameters = copy.deepcopy(ref_proc_params)

        try:
            char_results = edna_result.getCharacterisationResult()
            edna_strategy = char_results.getStrategyResult()
            collection_plan = edna_strategy.getCollectionPlan()[0]
            wedges = collection_plan.getCollectionStrategy().getSubWedge()
        except Exception:
            pass
        else:
            try:
                resolution = (
                    collection_plan.getStrategySummary().getResolution().getValue()
                )
                resolution = round(resolution, 3)
            except AttributeError:
                resolution = None

            try:
                transmission = (
                    collection_plan.getStrategySummary().getAttenuation().getValue()
                )
                transmission = round(transmission, 2)
            except AttributeError:
                transmission = None

            try:
                screening_id = edna_result.getScreeningId().getValue()
            except AttributeError:
                screening_id = None

            # GB merging wedges wedges
            osc_very_end = (
                wedges[-1]
                .getExperimentalCondition()
                .getGoniostat()
                .getRotationAxisEnd()
                .getValue()
            )

            for i in range(0, 1):  # GB len(wedges)):
                wedge = wedges[i]
                exp_condition = wedge.getExperimentalCondition()
                goniostat = exp_condition.getGoniostat()
                beam = exp_condition.getBeam()

                acq = qmo.Acquisition()
                acq.acquisition_parameters = (
                    HWR.beamline.get_default_acquisition_parameters()
                )
                acquisition_parameters = acq.acquisition_parameters

                acquisition_parameters.centred_position = (
                    reference_image_collection.acquisitions[
                        0
                    ].acquisition_parameters.centred_position
                )

                acq.path_template = HWR.beamline.get_default_path_template()

                # Use the same path template as the reference_collection
                # and update the members the needs to be changed. Keeping
                # the directories of the reference collection.
                ref_pt = reference_image_collection.acquisitions[0].path_template

                acq.path_template = copy.deepcopy(ref_pt)

                # This part was removing the "raw" from final directory and failing to collect data from EDNA-generated diffraction plan.
                # Keep it here until it is clear that it is not propagating further.
                # acq.path_template.directory = "/".join(
                #     ref_pt.directory.split("/")[0:-2]
                # )

                # acq.path_template.wedge_prefix = "w" + str(i + 1)
                acq.path_template.reference_image_prefix = str()

                if resolution:
                    acquisition_parameters.resolution = resolution

                if transmission:
                    acquisition_parameters.transmission = transmission

                if screening_id:
                    acquisition_parameters.screening_id = screening_id

                try:
                    acquisition_parameters.osc_start = (
                        goniostat.getRotationAxisStart().getValue()
                    )
                except AttributeError:
                    pass
                """ GB:
                try:
                    acquisition_parameters.osc_end = (
                        goniostat.getRotationAxisEnd().getValue()
                    )
                except AttributeError:
                    pass
                """
                acquisition_parameters.osc_end = osc_very_end

                try:
                    acquisition_parameters.osc_range = (
                        goniostat.getOscillationWidth().getValue()
                    )
                except AttributeError:
                    pass

                try:
                    num_images = int(
                        abs(
                            acquisition_parameters.osc_end
                            - acquisition_parameters.osc_start
                        )
                        / acquisition_parameters.osc_range
                    )

                    acquisition_parameters.first_image = 1
                    acquisition_parameters.num_images = num_images
                    acq.path_template.num_files = num_images
                    acq.path_template.start_num = 1

                except AttributeError:
                    pass

                try:
                    acquisition_parameters.transmission = (
                        beam.getTransmission().getValue()
                    )
                except AttributeError:
                    pass

                try:
                    acquisition_parameters.energy = round(
                        (123_984.0 / beam.getWavelength().getValue()) / 10000.0, 4
                    )
                except AttributeError:
                    pass

                try:
                    acquisition_parameters.exp_time = beam.getExposureTime().getValue()
                except AttributeError:
                    pass

                dc = qmo.DataCollection([acq], crystal, processing_parameters)
                data_collections.append(dc)

        return data_collections

    def mkdir_with_mode(self, directory, mode):
        """
        The function creates a directory with a specified mode if it does not already exist.

        :param directory: The "directory" parameter is the path of the directory that you want to
        create. It can be an absolute path or a relative path
        :param mode: The "mode" parameter in the above code refers to the permissions that will be set
        for the newly created directory. It is an optional parameter that specifies the access mode for
        the directory. The access mode is a numeric value that represents the permissions for the
        directory
        """
        if not os.path.isdir(directory):
            oldmask = os.umask(000)
            os.makedirs(directory, mode=mode)
            os.umask(oldmask)
            # self.checkPath(directory,force=True)

            self.log.debug("local directory created")

    def get_html_report(self, edna_result):
        """
        Args:
            output (EDNAResult) EDNAResult object

        Returns:
            (str) The path to the html result report generated by the characterisation
            software
        """
        html_report = None

        try:
            html_report = str(edna_result.getHtmlPage().getPath().getValue())
            html_report = html_report.replace("/beamline/p11", "/gpfs")

        except AttributeError:
            pass

        return html_report
