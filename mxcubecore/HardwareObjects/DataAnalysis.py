"""ESRF implementation of AbstractDataAnalysis targetting EDNA

Example XML config. file:

<object class="DataAnalysis">
  <object href="/mxcollect" role="collect"/>
  <tangoname>id14eh1/das/1</tangoname>
  <channel type="tango" name="jobSuccess" polling="events">jobSuccess</channel>
  <channel type="tango" name="jobFailure" polling="events">jobFailure</channel>
  <command type="tango" name="getJobOutput">getJobOutput</command>
  <command type="tango" name="startJob">startJob</command>
</object>
"""
import logging
import gevent.event
import threading
import subprocess
import time
import os
import queue_model_objects_v1 as queue_model_objects

from AbstractDataAnalysis import *
from HardwareRepository.BaseHardwareObjects import HardwareObject

from XSDataMXCuBEv1_3 import XSDataInputMXCuBE
from XSDataMXCuBEv1_3 import XSDataMXCuBEDataSet
from XSDataMXCuBEv1_3 import XSDataResultMXCuBE

from XSDataCommon import XSData
from XSDataCommon import XSDataAngle
from XSDataCommon import XSDataBoolean
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataFloat
from XSDataCommon import XSDataInput
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataMatrixDouble
from XSDataCommon import XSDataResult
from XSDataCommon import XSDataSize
from XSDataCommon import XSDataString
from XSDataCommon import XSDataImage
from XSDataCommon import XSDataAbsorbedDoseRate
from XSDataCommon import XSDataAngularSpeed
from XSDataCommon import XSDataFlux
from XSDataCommon import XSDataLength
from XSDataCommon import XSDataTime
from XSDataCommon import XSDataWavelength

from edna_test_data import EDNA_DEFAULT_INPUT
from edna_test_data import EDNA_TEST_DATA

from collections import namedtuple


class EdnaProcessingThread(threading.Thread):
    def __init__(self, edna_cmd, edna_input_file, edna_output_file, base_dir):
        threading.Thread.__init__(self)
        
        self.edna_cmd = edna_cmd
        self.edna_input_file = edna_input_file
        self.edna_output_file = edna_output_file
        self.base_dir = base_dir

    def start(self):
        self.edna_processing_watcher = gevent.get_hub().loop.async()
        self.edna_processing_done = gevent.event.Event()
        threading.Thread.start(self)
        return self.edna_processing_done
        
    def run(self):
        self.edna_processing_watcher.start(self.edna_processing_done.set)
        subprocess.call("%s %s %s %s" % (self.edna_cmd, self.edna_input_file, self.edna_output_file, self.base_dir), shell=True)
        self.edna_processing_watcher.send()


class DataAnalysis(AbstractDataAnalysis, HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.collect_obj = None
        self.result = None
        self.processing_done_event = gevent.event.Event()

        
    def init(self):
        self.collect_obj = self.getObjectByRole("collect")
        self.start_edna_command = self.getProperty("edna_command")

  
    def get_html_report(self, edna_result):
        html_report = None

        try:
            html_report = str(edna_result.getHtmlPage().getPath().getValue())
        except AttributeError:
            pass

        return html_report


    def from_params(self, data_collection, char_params):
        edna_input = XSDataInputMXCuBE.parseString(EDNA_DEFAULT_INPUT)

        if data_collection.id:
            edna_input.setDataCollectionId(XSDataInteger(data_collection.id))

        #Beam object
        beam = edna_input.getExperimentalCondition().getBeam()

        try:
            beam.setTransmission(XSDataDouble(self.collect_obj.get_transmission()))
        except AttributeError:
            pass

        try:
            beam.setWavelength(XSDataWavelength(self.collect_obj.get_wavelength()))
        except AttributeError:
            pass

        try:
            beam.setFlux(XSDataFlux(self.collect_obj.get_measured_intensity()))
        except AttributeError:
            pass

        #Optimization parameters
        diff_plan = edna_input.getDiffractionPlan()

        diff_plan.setAimedIOverSigmaAtHighestResolution(\
            XSDataDouble(char_params.aimed_i_sigma))

        diff_plan.setAimedCompleteness(XSDataDouble(char_params.\
                                                    aimed_completness))

        if char_params.use_aimed_multiplicity:
            diff_plan.setAimedMultiplicity(XSDataDouble(char_params.\
                                                        aimed_multiplicity))
            
        if char_params.use_aimed_resolution:
            diff_plan.setAimedResolution(XSDataDouble(char_params.aimed_resolution))

        diff_plan.setComplexity(XSDataString(\
                queue_model_objects.STRATEGY_COMPLEXITY[char_params.strategy_complexity]))

        if char_params.use_permitted_rotation:
            diff_plan.setUserDefinedRotationStart(XSDataAngle(char_params.\
                                                              permitted_phi_start))

            diff_plan.setUserDefinedRotationRange(XSDataAngle(char_params.permitted_phi_end -\
                                                              char_params.permitted_phi_start))


        #Vertical crystal dimension
        sample = edna_input.getSample()
        sample.getSize().setY(XSDataLength(char_params.max_crystal_vdim))
        sample.getSize().setZ(XSDataLength(char_params.min_crystal_vdim))


        #Radiation damage model
        sample.setSusceptibility(XSDataDouble(char_params.rad_suscept))
        sample.setChemicalComposition(None)
        sample.setRadiationDamageModelBeta(XSDataDouble(char_params.beta/1e6))
        sample.setRadiationDamageModelGamma(XSDataDouble(char_params.gamma/1e6))
            

        diff_plan.setForcedSpaceGroup(XSDataString(char_params.\
                                                   space_group))


        # Characterisation type - Routine DC
        if char_params.use_min_dose:
            pass

        if char_params.use_min_time:
            diff_plan.setMaxExposureTimePerDataCollection(XSDataTime(char_params.\
                                                                     min_time))

        
        # Account for radiation damage
        if char_params.induce_burn:
            diff_plan.setStrategyOption(XSDataString("-DamPar")) # What is -DamPar ?
        else:
            diff_plan.setStrategyOption(None)


        # Characterisation type - SAD
        if queue_model_objects.EXPERIMENT_TYPE[char_params.experiment_type] is queue_model_objects.EXPERIMENT_TYPE.SAD:
            diff_plan.setAnomalousData(XSDataBoolean(True))
        else:
            diff_plan.setAnomalousData(XSDataBoolean(False))

        
        #Data set
        data_set = XSDataMXCuBEDataSet()
        acquisition_parameters = data_collection.previous_acquisition.acquisition_parameters
        path_str = os.path.join(data_collection.previous_acquisition.path_template.directory,
                                data_collection.previous_acquisition.path_template.get_image_file_name())
        
        for img_num in range(int(acquisition_parameters.num_images)):
            image_file = XSDataFile()
            path = XSDataString()
            path.setValue(path_str % (img_num + 1))
            image_file.setPath(path)
            data_set.addImageFile(image_file)

        edna_input.addDataSet(data_set)
        
        edna_input.process_directory = data_collection.acquisitions[0].path_template.process_directory
        
        return edna_input

    
    def characterise(self, edna_input):
        process_directory_path = edna_input.process_directory
        
        # if there is no data collection id, the id will be a random number
        # this is to give a unique number to the EDNA input and result files;
        # something more clever might be done to give a more significant
        # name, if there is no dc id.
        try:
          dc_id = edna_input.getDataCollectionId().getValue()
        except:
          dc_id = id(edna_input)
        
        if hasattr(edna_input, "process_directory"):
          edna_input_file = os.path.join(process_directory_path,"EDNAInput_%s.xml" % dc_id)
          edna_input.exportToFile(edna_input_file)
          edna_results_file = os.path.join(process_directory_path, "EDNAOutput_%s.xml" % dc_id)

          if not os.path.isdir(process_directory_path):
              os.makedirs(path)
        else:
          raise RuntimeError, "No process directory specified in edna_input"

        logging.getLogger("queue_exec").info("Starting EDNA using xml file %r", edna_input_file)

        edna_processing_thread = EdnaProcessingThread(self.start_edna_command, \
                                                      edna_input_file, \
                                                      edna_results_file,\
                                                      process_directory_path)
        self.processing_done_event = edna_processing_thread.start()
        self.processing_done_event.wait()
        
        self.result = XSDataResultMXCuBE.parseFile(edna_results_file)
        
        return self.result
       

    def is_running(self):
        return not self.processing_done_event.is_set()
