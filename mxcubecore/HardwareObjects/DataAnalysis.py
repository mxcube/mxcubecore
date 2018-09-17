import os
import logging
import gevent.event
import threading
import subprocess
import AbstractDataAnalysis

import queue_model_enumerables_v1 as qme

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareRepository import HardwareRepository

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

#from edna_test_data import EDNA_DEFAULT_INPUT
#from edna_test_data import EDNA_TEST_DATA


class DataAnalysis(AbstractDataAnalysis.AbstractDataAnalysis, HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.collect_obj = None
        self.result = None
        self.edna_processing_thread = None
        self.processing_done_event = gevent.event.Event()

    def init(self):
        self.collect_obj = self.getObjectByRole("collect")
        self.start_edna_command = self.getProperty("edna_command")
        self.edna_default_file = self.getProperty("edna_default_file")
        hwr_dir = HardwareRepository().getHardwareRepositoryPath()

        with open(os.path.join(hwr_dir, self.edna_default_file), 'r') as f:
            self.edna_default_input = ''.join(f.readlines())

    def get_html_report(self, edna_result):
        html_report = None

        try:
            html_report = str(edna_result.getHtmlPage().getPath().getValue())
        except AttributeError:
            pass

        return html_report

    def get_beam_size(self):
        return self.collect_obj.beam_info_hwobj.get_beam_size()

    def modify_strategy_option(self, diff_plan, strategy_option):
        """Method for modifying the diffraction plan 'strategyOption' entry"""
        if diff_plan.getStrategyOption() is None:
            new_strategy_option = strategy_option
        else:
            new_strategy_option = diff_plan.getStrategyOption().getValue() + ' ' + strategy_option
        diff_plan.setStrategyOption(XSDataString(new_strategy_option))


    def from_params(self, data_collection, char_params):
        edna_input = XSDataInputMXCuBE.parseString(self.edna_default_input)

        if data_collection.id:
            edna_input.setDataCollectionId(XSDataInteger(data_collection.id))

        #Beam object
        beam = edna_input.getExperimentalCondition().getBeam()

        try:
            transmission = self.collect_obj.get_transmission()
            beam.setTransmission(XSDataDouble(transmission))
        except AttributeError:
            pass

        try:
            wavelength = self.collect_obj.get_wavelength()
            beam.setWavelength(XSDataWavelength(wavelength))
        except AttributeError:
            pass

        try:
            beam.setFlux(XSDataFlux(self.collect_obj.get_measured_intensity()))
        except AttributeError:
            pass

        try:
            min_exp_time = self.collect_obj.detector_hwobj.get_exposure_time_limits()[0]
            beam.setMinExposureTimePerImage(XSDataTime(min_exp_time))
        except AttributeError:
            pass

        try:
            beamsize = self.get_beam_size()
            if not None in beamsize:
                beam.setSize(XSDataSize(x=XSDataLength(float(beamsize[0])),
                                        y=XSDataLength(float(beamsize[1]))))
        except AttributeError:
            pass

        #Optimization parameters
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

        diff_plan.setAimedIOverSigmaAtHighestResolution(aimed_i_sigma)
        diff_plan.setAimedCompleteness(aimed_completness)

        if char_params.use_aimed_multiplicity:
            diff_plan.setAimedMultiplicity(aimed_multiplicity)

        if char_params.use_aimed_resolution:
            diff_plan.setAimedResolution(aimed_resolution)

        diff_plan.setComplexity(complexity)

        if char_params.use_permitted_rotation:
            diff_plan.setUserDefinedRotationStart(permitted_phi_start)
            diff_plan.setUserDefinedRotationRange(rotation_range)

        #Vertical crystal dimension
        sample = edna_input.getSample()
        sample.getSize().setY(XSDataLength(char_params.max_crystal_vdim))
        sample.getSize().setZ(XSDataLength(char_params.min_crystal_vdim))

        #Radiation damage model
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

        #Data set
        data_set = XSDataMXCuBEDataSet()
        acquisition_parameters = data_collection.acquisitions[0].acquisition_parameters
        path_template = data_collection.acquisitions[0].path_template
        path_str = os.path.join(path_template.directory,
                                path_template.get_image_file_name())

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

        # if there is no data collection id, the id will be a random number
        # this is to give a unique number to the EDNA input and result files;
        # something more clever might be done to give a more significant
        # name, if there is no dc id.
        path = edna_input.process_directory

        # if there is no data collection id, the id will be a random number
        # this is to give a unique number to the EDNA input and result files;
        # something more clever might be done to give a more significant
        # name, if there is no dc id.
        try:
            dc_id = edna_input.getDataCollectionId().getValue()
        except:
            dc_id = id(edna_input)

        if hasattr(edna_input, "process_directory"):
            edna_input_file = os.path.join(path, "EDNAInput_%s.xml" % dc_id)
            edna_input.exportToFile(edna_input_file)
            edna_results_file = os.path.join(path, "EDNAOutput_%s.xml" % dc_id)

            if not os.path.isdir(path):
                os.makedirs(path)
        else:
            raise RuntimeError("No process directory specified in edna_input")

        msg = "Starting EDNA using xml file %r", edna_input_file
        logging.getLogger("queue_exec").info(msg)

        args = (self.start_edna_command, edna_input_file,
                edna_results_file, path)
        subprocess.call("%s %s %s %s" % args, shell=True)

        self.result = None
        if os.path.exists(edna_results_file):
            self.result = XSDataResultMXCuBE.parseFile(edna_results_file)

        return self.result

    def is_running(self):
        return not self.processing_done_event.is_set()

    def stop(self):
        if self.edna_processing_thread is not None:
            self.edna_processing_thread.stop()
