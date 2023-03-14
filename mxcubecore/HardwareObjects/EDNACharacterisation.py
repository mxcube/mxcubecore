import os
import copy
import logging
import binascii
import subprocess

from mxcubecore.HardwareObjects import queue_model_objects as qmo
from mxcubecore.HardwareObjects import queue_model_enumerables as qme

from mxcubecore.HardwareObjects.SecureXMLRpcRequestHandler import SecureXMLRpcRequestHandler
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractCharacterisation import AbstractCharacterisation

from XSDataMXCuBEv1_4 import XSDataInputMXCuBE
from XSDataMXCuBEv1_4 import XSDataMXCuBEDataSet
from XSDataMXCuBEv1_4 import XSDataResultMXCuBE

from XSDataCommon import XSDataAngle
from XSDataCommon import XSDataBoolean
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataFlux
from XSDataCommon import XSDataLength
from XSDataCommon import XSDataTime
from XSDataCommon import XSDataWavelength
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataSize
from XSDataCommon import XSDataString

import triggerUtils

# from edna_test_data import EDNA_DEFAULT_INPUT
# from edna_test_data import EDNA_TEST_DATA


class EDNACharacterisation(AbstractCharacterisation):
    def __init__(self, name):
        super(EDNACharacterisation, self).__init__(name)

        self.collect_obj = None
        self.result = None
        self.edna_default_file = None
        self.start_edna_command = None

    def init(self):
        self.collect_obj = self.get_object_by_role("collect")
        self.start_edna_command = self.get_property("edna_command")
        self.edna_default_file = self.get_property("edna_default_file")

        fp = HWR.get_hardware_repository().find_in_repository(self.edna_default_file)

        if fp is None:
            fp = self.edna_default_file

            if not os.path.exists(fp):
                raise ValueError("File %s not found in repository" % fp)

        with open(fp, "r") as f:
            self.edna_default_input = "".join(f.readlines())

    def _modify_strategy_option(self, diff_plan, strategy_option):
        """Method for modifying the diffraction plan 'strategyOption' entry"""
        if diff_plan.getStrategyOption() is None:
            new_strategy_option = strategy_option
        else:
            new_strategy_option = (
                diff_plan.getStrategyOption().getValue() + " " + strategy_option
            )

        diff_plan.setStrategyOption(XSDataString(new_strategy_option))

    def _run_edna(self, input_file, results_file, process_directory):
        """Starts EDNA"""
        msg = "Starting EDNA characterisation using xml file %s" % input_file
        logging.getLogger("queue_exec").info(msg)

        args = (self.start_edna_command, input_file, results_file, process_directory)
        # subprocess.call("%s %s %s %s" % args, shell=True)

        # Test run DESY
        self.edna_maxwell(process_directory,input_file, results_file)



        self.result = None
        if os.path.exists(results_file):
            self.result = XSDataResultMXCuBE.parseFile(results_file)

        return self.result
    
    def edna_maxwell(self,process_directory,inputxml, outputxml):

        self.log.debug("=======EDNA========== PROCESS DIRECTORY=\"%s\"" % process_directory)
        self.log.debug("=======EDNA========== IN=\"%s\"" % inputxml)
        self.log.debug("=======EDNA========== OUT=\"%s\"" % outputxml)

        btHelper = triggerUtils.Trigger()
        ssh = btHelper.get_ssh_command()
        sbatch = btHelper.get_sbatch_command(jobname_prefix = "edna",job_dependency='singleton', logfile_path=process_directory.replace("/gpfs","/beamline/p11")+"/edna.log")

        cmd = ("/asap3/petra3/gpfs/common/p11/processing/edna_sbatch.sh " + \
                    "{inxml:s} {outxml:s} {processpath:s}").format(
            inxml = inputxml.replace("/gpfs","/beamline/p11"),
            outxml = outputxml.replace("/gpfs","/beamline/p11"),
            processpath = process_directory.replace("/gpfs","/beamline/p11")
        )

        # Check path conversion
        inxml = inputxml.replace("/gpfs","/beamline/p11")
        outxml = outputxml.replace("/gpfs","/beamline/p11")
        processpath = process_directory.replace("/gpfs","/beamline/p11")
        self.log.debug("=======EDNA========== CLUSTER PROCESS DIRECTORY=\"%s\"" % processpath)
        self.log.debug("=======EDNA========== CLUSTER IN=\"%s\"" % inxml)
        self.log.debug("=======EDNA========== CLUSTER OUT=\"%s\"" % outxml)



        self.log.debug("=======EDNA========== ssh=\"%s\"" % ssh)
        self.log.debug("=======EDNA========== sbatch=\"%s\"" % sbatch)
        self.log.debug("=======EDNA========== executing process cmd=\"%s\"" % cmd)
        self.log.debug("=======EDNA========== {ssh:s} \"{sbatch:s} --wrap \\\"{cmd:s}\\\"\"".format(
            ssh = ssh,
            sbatch = sbatch,
            cmd = cmd
        ))


        os.system("{ssh:s} \"{sbatch:s} --wrap \\\"{cmd:s}\"\\\"".format(
            ssh = ssh,
            sbatch = sbatch,
            cmd = cmd
        ))

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
        except AttributeError:
            pass

        return html_report

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

        image_dir=path_template.directory.replace("/gpfs/current",triggerUtils.get_beamtime_metadata()[2])
        path_str = os.path.join(
           image_dir, path_template.get_image_file_name()
           )


        #path_str = os.path.join(
        #    path_template.directory, path_template.get_image_file_name()
        #)


        for img_num in range(int(acquisition_parameters.num_images)):
            image_file = XSDataFile()
            path = XSDataString()
            path.setValue(path_str % (img_num + 1))
            image_file.setPath(path)
            data_set.addImageFile(image_file)

        edna_input.addDataSet(data_set)
        edna_input.process_directory = path_template.process_directory

        return edna_input

    def characterise(self, edna_input):
        """
        Args:
            input (EDNAInput) EDNA input object

        Returns:
            (str) The Characterisation result
        """
        self.processing_done_event.set()
        self.prepare_input(edna_input)
        path = edna_input.process_directory

        # if there is no data collection id, the id will be a random number
        # this is to give a unique number to the EDNA input and result files;
        # something more clever might be done to give a more significant
        # name, if there is no dc id.
        try:
            dc_id = edna_input.getDataCollectionId().getValue()
        except Exception:
            dc_id = id(edna_input)

        token = self.generate_new_token()
        edna_input.token = XSDataString(token)

        if hasattr(edna_input, "process_directory"):
            edna_input_file = os.path.join(path, "EDNAInput_%s.xml" % dc_id)
            edna_input.exportToFile(edna_input_file)
            edna_results_file = os.path.join(path, "EDNAOutput_%s.xml" % dc_id)

            self.log.debug("------- %s %s"%(path,os.path.isdir(path)))
            if not os.path.isdir(path):
                oldmask=os.umask(000)
                os.makedirs(path,mode=0o777)
                os.umask(oldmask)
        else:
            raise RuntimeError("No process directory specified in edna_input")

        self.result = self._run_edna(edna_input_file, edna_results_file, path)

        self.processing_done_event.clear()
        return self.result

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

            for i in range(0, len(wedges)):
                wedge = wedges[i]
                exp_condition = wedge.getExperimentalCondition()
                goniostat = exp_condition.getGoniostat()
                beam = exp_condition.getBeam()

                acq = qmo.Acquisition()
                acq.acquisition_parameters = (
                    HWR.beamline.get_default_acquisition_parameters()
                )
                acquisition_parameters = acq.acquisition_parameters

                acquisition_parameters.centred_position = reference_image_collection.acquisitions[
                    0
                ].acquisition_parameters.centred_position

                acq.path_template = HWR.beamline.get_default_path_template()

                # Use the same path template as the reference_collection
                # and update the members the needs to be changed. Keeping
                # the directories of the reference collection.
                ref_pt = reference_image_collection.acquisitions[0].path_template
                acq.path_template = copy.deepcopy(ref_pt)
                acq.path_template.wedge_prefix = "w" + str(i + 1)
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

                try:
                    acquisition_parameters.osc_end = (
                        goniostat.getRotationAxisEnd().getValue()
                    )
                except AttributeError:
                    pass

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
                        (123984.0 / beam.getWavelength().getValue()) / 10000.0, 4
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

    def get_default_characterisation_parameters(self):
        """
        Returns:
            (queue_model_objects.CharacterisationsParameters) object with default
            parameters.
        """
        edna_input = XSDataInputMXCuBE.parseString(self.edna_default_input)
        diff_plan = edna_input.getDiffractionPlan()

        edna_sample = edna_input.getSample()
        char_params = qmo.CharacterisationParameters()
        char_params.experiment_type = qme.EXPERIMENT_TYPE.OSC

        # Optimisation parameters
        char_params.use_aimed_resolution = False
        try:
            char_params.aimed_resolution = diff_plan.getAimedResolution().getValue()
        except Exception:
            char_params.aimed_resolution = None

        char_params.use_aimed_multiplicity = False
        try:
            char_params.aimed_i_sigma = (
                diff_plan.getAimedIOverSigmaAtHighestResolution().getValue()
            )
            char_params.aimed_completness = diff_plan.getAimedCompleteness().getValue()
        except Exception:
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

    def generate_new_token(self):
        # See: https://wyattbaldwin.com/2014/01/09/generating-random-tokens-in-python/
        token = binascii.hexlify(os.urandom(5)).decode('utf-8')
        SecureXMLRpcRequestHandler.setReferenceToken(token)
        return token

