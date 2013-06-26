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


class DataAnalysis(AbstractDataAnalysis, HardwareObject):

    TANGO_SUBSCRIBE_MSG = 'Hello Tango world'
    
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.collect_obj = None
        self.success = None
        self.failure = None
        self.result = None
        self.job_id = None
        self.job_success_event = gevent.event.Event()

        
    def init(self):
        self.collect_obj = self.getObjectByRole("collect")

        try:
            self.getChannelObject('jobSuccess').connectSignal('update', self.success_cb)
            self.getChannelObject('jobFailure').connectSignal('update', self.failure_cb)
            self.startJob = self.getCommandObject("startJob")
            self.getJobOutput = self.getCommandObject("getJobOutput")
        except KeyError as ex:
            logging.getLogger('HWR').exception('Could most likely not connect'+\
                                               ' to tagno device server' +\
                                               str(ex))


    def success_cb(self, value):
        if value != DataAnalysis.TANGO_SUBSCRIBE_MSG:
            self.success = value
            logging.info(self.success)
            self.result = self.getJobOutput(value)
            self.job_success_event.set()


    def failure_cb(self, value):
        if value != DataAnalysis.TANGO_SUBSCRIBE_MSG:
            self.failure = value
            logging.info(self.failure)
            self.job_success_event.set()


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
        acquisition_parameters = data_collection.acquisitions[0].acquisition_parameters
        path_str = os.path.join(data_collection.acquisitions[0].path_template.directory,
                                data_collection.acquisitions[0].path_template.get_image_file_name())
        
        for img_num in range(int(acquisition_parameters.num_images)):
            image_file = XSDataFile()
            path = XSDataString()
            path.setValue(path_str % (img_num + 1))
            image_file.setPath(path)
            data_set.addImageFile(image_file)

        edna_input.addDataSet(data_set)

        return edna_input

    
    def characterise(self, edna_input):
        #edna_plugin = "EDPluginControlInterfaceToMXCuBEv1_3"
        edna_plugin = "EDPluginControlMXCuBEWrapperv1_3"
        edna_result = None


        self.job_success_event.clear()
        self.job_id = self.startJob([edna_plugin, 
                                     edna_input.marshal()])
        logging.info("Running %s" % edna_plugin)

        self.job_success_event.wait(timeout = 180)

        if self.result is not None:
            if self.result.find("CharacterisationResult.xml") != -1:

                logging.getLogger('queue_exec').\
                    info('EDNA-Characterisation completed successfully')
                logging.getLogger('queue_exec').\
                    info('with result ' + self.result)
                
                edna_result = XSDataResultMXCuBE.parseString(self.result)
                
        return edna_result


    def is_running(self):
        return not self.job_success_event.isSet()
