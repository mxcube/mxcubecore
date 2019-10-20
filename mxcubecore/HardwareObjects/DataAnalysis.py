import os
import logging
import gevent.event
import subprocess

from XSDataMXCuBEv1_3 import XSDataInputMXCuBE
from XSDataMXCuBEv1_3 import XSDataMXCuBEDataSet
from XSDataMXCuBEv1_3 import XSDataResultMXCuBE

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

from HardwareRepository.HardwareObjects.abstract import AbstractDataAnalysis
from HardwareRepository.HardwareObjects import queue_model_enumerables as qme
from HardwareRepository.HardwareObjects import queue_model_objects as qmo
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR

# from edna_test_data import EDNA_DEFAULT_INPUT
# from edna_test_data import EDNA_TEST_DATA


class DataAnalysis(AbstractDataAnalysis.AbstractDataAnalysis, HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.result = None
        self.processing_done_event = gevent.event.Event()

    def init(self):
        self.collect_obj = self.getObjectByRole("collect")
        self.start_edna_command = self.getProperty("edna_command")
        self.edna_default_file = self.getProperty("edna_default_file")

        if not os.path.isfile(self.edna_default_file):
            raise ValueError("File %s not found" % self.edna_default_file)
        with open(self.edna_default_file, "r") as f:
            self.edna_default_input = "".join(f.readlines())

    def get_html_report(self, edna_result):
        html_report = None

        try:
            html_report = str(edna_result.getHtmlPage().getPath().getValue())
        except AttributeError:
            pass

        return html_report

    def modify_strategy_option(self, diff_plan, strategy_option):
        """Method for modifying the diffraction plan 'strategyOption' entry"""
        if diff_plan.getStrategyOption() is None:
            new_strategy_option = strategy_option
        else:
            new_strategy_option = (
                diff_plan.getStrategyOption().getValue() + " " + strategy_option
            )
        diff_plan.setStrategyOption(XSDataString(new_strategy_option))

    def get_default_characterisation_parameters(self):
        """
        :returns: A CharacterisationsParameters object with default parameters.
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
        except BaseException:
            char_params.aimed_resolution = None

        char_params.use_aimed_multiplicity = False
        try:
            char_params.aimed_i_sigma = (
                diff_plan.getAimedIOverSigmaAtHighestResolution().getValue()
            )
            char_params.aimed_completness = diff_plan.getAimedCompleteness().getValue()
        except BaseException:
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

    def from_params(self, data_collection, char_params):
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

            logging.getLogger("HWR").debug("DataAnalysis. transmission not saved ")
            logging.getLogger("HWR").debug(traceback.format_exc())

        try:
            wavelength = HWR.beamline.energy.get_current_wavelength()
            beam.setWavelength(XSDataWavelength(wavelength))
        except AttributeError:
            pass

        try:
            beam.setFlux(XSDataFlux(HWR.beamline.flux.get_flux()))
        except AttributeError:
            pass

        try:
            min_exp_time = HWR.beamline.detector.get_exposure_time_limits()[0]
            beam.setMinExposureTimePerImage(XSDataTime(min_exp_time))
        except AttributeError:
            pass

        try:
            beamsize = HWR.beamline.beam.get_beam_size()
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
            self.modify_strategy_option(diff_plan, "-DamPar")

        # Characterisation type - SAD
        if char_params.opt_sad:
            if char_params.auto_res:
                diff_plan.setAnomalousData(XSDataBoolean(True))
            else:
                diff_plan.setAnomalousData(XSDataBoolean(False))
                self.modify_strategy_option(diff_plan, "-SAD yes")
                diff_plan.setAimedResolution(XSDataDouble(char_params.sad_res))
        else:
            diff_plan.setAnomalousData(XSDataBoolean(False))

        # Data set
        data_set = XSDataMXCuBEDataSet()
        acquisition_parameters = data_collection.acquisitions[0].acquisition_parameters
        path_template = data_collection.acquisitions[0].path_template
        path_str = os.path.join(
            path_template.directory, path_template.get_image_file_name()
        )

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
        self.prepare_edna_input(edna_input)
        path = edna_input.process_directory

        # if there is no data collection id, the id will be a random number
        # this is to give a unique number to the EDNA input and result files;
        # something more clever might be done to give a more significant
        # name, if there is no dc id.
        try:
            dc_id = edna_input.getDataCollectionId().getValue()
        except BaseException:
            dc_id = id(edna_input)

        if hasattr(edna_input, "process_directory"):
            edna_input_file = os.path.join(path, "EDNAInput_%s.xml" % dc_id)
            edna_input.exportToFile(edna_input_file)
            edna_results_file = os.path.join(path, "EDNAOutput_%s.xml" % dc_id)

            if not os.path.isdir(path):
                os.makedirs(path)
        else:
            raise RuntimeError("No process directory specified in edna_input")

        self.result = self.run_edna(edna_input_file, edna_results_file, path)

        return self.result

    def prepare_edna_input(self, edna_input):
        """
        Allows to manipulate edna_input object before exporting it to file
        Example: to set a site specific output directory
        """

    def run_edna(self, input_file, results_file, process_directory):

        msg = "Starting EDNA characterisation using xml file %s" % input_file
        logging.getLogger("queue_exec").info(msg)

        args = (self.start_edna_command, input_file, results_file, process_directory)
        subprocess.call("%s %s %s %s" % args, shell=True)

        self.result = None
        if os.path.exists(results_file):
            self.result = XSDataResultMXCuBE.parseFile(results_file)

        return self.result

    def is_running(self):
        return not self.processing_done_event.is_set()
