#!/usr/bin/env python

"""A simple client for MetadataManager and MetaExperiment
"""
from __future__ import print_function
import os
import sys
import math
import time
import logging
import PyTango.client
import traceback
from email.mime.text import MIMEText
import smtplib

from mx3core.ConvertUtils import string_types
from mx3core import HardwareRepository as HWR


class MetadataManagerClient(object):

    """
    A client for the MetadataManager and MetaExperiment tango Devices

    Attributes:
        name: name of the tango device. Example: 'id21/metadata/ingest'
    """

    def __init__(self, metadataManagerName, metaExperimentName):
        """
        Return a MetadataManagerClient object whose metadataManagerName is *metadataManagerName*
        and metaExperimentName is *metaExperimentName*
        """
        self.dataRoot = None
        self.proposal = None
        self.sample = None
        self.datasetName = None

        if metadataManagerName:
            self.metadataManagerName = metadataManagerName
        if metaExperimentName:
            self.metaExperimentName = metaExperimentName

        print("MetadataManager: %s" % metadataManagerName)
        print("MetaExperiment: %s" % metaExperimentName)

        # Tango Devices instances
        try:
            MetadataManagerClient.metadataManager = PyTango.client.Device(
                self.metadataManagerName
            )
            MetadataManagerClient.metaExperiment = PyTango.client.Device(
                self.metaExperimentName
            )
        except Exception:
            print("Unexpexted error: ", sys.exc_info()[0])
            raise

    def printStatus(self):
        print("DataRoot: %s" % MetadataManagerClient.metaExperiment.dataRoot)
        print("Proposal: %s" % MetadataManagerClient.metaExperiment.proposal)
        print("Sample: %s" % MetadataManagerClient.metaExperiment.sample)
        print("Dataset: %s" % MetadataManagerClient.metadataManager.scanName)

    def __setAttribute(self, proxy, attributeName, newValue):
        """
        This method sets an attribute on either the MetadataManager or MetaExperiment server.
        The method checks that the attribute has been set, and repeats up to five times
        setting the attribute if not. If the attribute is not set after five trials the method
        raises an 'RuntimeError' exception.
        """
        currentValue = "unknown"
        if newValue == currentValue:
            currentValue = "Current value not known"
        counter = 0
        while counter < 5:
            counter += 1
            try:
                setattr(proxy, attributeName, newValue)
                time.sleep(0.1)
                currentValue = getattr(proxy, attributeName)
                if currentValue == newValue:
                    break
            except Exception as e:
                print("Unexpected error in MetadataManagerClient._setAttribute: {0}".format(e))
                print("proxy = '{0}', attributeName = '{1}', newValue = '{2}'".format(
                    proxy, attributeName, newValue))
                print("Trying again, trial #{0}".format(counter))
                time.sleep(1)
        if currentValue == newValue:
            setattr(self, attributeName, newValue)
        else:
            raise RuntimeError("Cannot set '{0}' attribute '{1}' to '{2}'!".format(proxy, attributeName, newValue))

    def __setDataRoot(self, dataRoot):
        try:
            MetadataManagerClient.metaExperiment.dataRoot = dataRoot
            self.dataRoot = dataRoot
        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    def __setProposal(self, proposal):
        """ Set proposal should be done before stting the data root """
        try:
            MetadataManagerClient.metaExperiment.proposal = proposal
            self.proposal = proposal
        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    def appendFile(self, filePath):
        try:
            MetadataManagerClient.metadataManager.lastDataFile = filePath
        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    def __setSample(self, sample):
        try:
            MetadataManagerClient.metaExperiment.sample = sample
            self.sample = sample
        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    def __setDataset(self, datasetName):
        try:
            MetadataManagerClient.metadataManager.scanName = datasetName
            self.datasetName = datasetName
        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    def start(self, dataRoot, proposal, sampleName, datasetName):
        """ Starts a new dataset """
        if MetadataManagerClient.metaExperiment:
            try:
                # setting proposal
                # self.__setProposal(proposal)
                self.__setAttribute(MetadataManagerClient.metaExperiment, "proposal", proposal)

                # setting dataRoot
                # self.__setDataRoot(dataRoot)
                self.__setAttribute(MetadataManagerClient.metaExperiment, "dataRoot", dataRoot)

                # setting sample
                # self.__setSample(sampleName)
                self.__setAttribute(MetadataManagerClient.metaExperiment, "sample", sampleName)

                # setting dataset
                # self.__setDataset(datasetName)
                self.__setAttribute(MetadataManagerClient.metadataManager, "scanName", datasetName)
                self.datasetName = datasetName

                # setting datasetName
                if str(MetadataManagerClient.metaExperiment.state()) == "ON":
                    if str(MetadataManagerClient.metadataManager.state()) == "ON":
                        MetadataManagerClient.metadataManager.StartScan()

            except Exception:
                print("Unexpected error:", sys.exc_info()[0])
                raise

    def end(self):
        try:
            MetadataManagerClient.metadataManager.endScan()
        except Exception:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    def get_state(self):
        return str(MetadataManagerClient.metadataManager.state())


class MXCuBEMetadataClient(object):
    def __init__(self, esrf_multi_collect):
        self.esrf_multi_collect = esrf_multi_collect
        if hasattr(self.esrf_multi_collect["metadata"], "manager"):
            self._metadataManagerName = self.esrf_multi_collect["metadata"].manager
        else:
            self._metadataManagerName = None
        if hasattr(self.esrf_multi_collect["metadata"], "experiment"):
            self._metaExperimentName = self.esrf_multi_collect["metadata"].experiment
        else:
            self._metaExperimentName = None
        if hasattr(self.esrf_multi_collect["metadata"], "error_email"):
            self._listEmailReceivers = self.esrf_multi_collect[
                "metadata"
            ].error_email.split(" ")
        else:
            self._listEmailReceivers = []
        if hasattr(self.esrf_multi_collect["metadata"], "replyto_email"):
            self._emailReplyTo = self.esrf_multi_collect["metadata"].replyto_email
        else:
            self._emailReplyTo = None

        self._beamline = HWR.beamline.session.endstation_name

    def reportStackTrace(self):
        (exc_type, exc_value, exc_traceback) = sys.exc_info()
        errorMessage = "{0} {1}".format(exc_type, exc_value)
        errorMessage += "\n\n"
        listTrace = traceback.extract_tb(exc_traceback)
        errorMessage += "Traceback (most recent call last): \n"
        for listLine in listTrace:
            errorMessage += '  File "%s", line %d, in %s%s\n' % (
                listLine[0],
                listLine[1],
                listLine[2],
                os.linesep,
            )
        if len(self._listEmailReceivers) > 0 and self._emailReplyTo is not None:
            COMMASPACE = ", "
            mime_text_message = MIMEText(errorMessage)
            replyTo = self._emailReplyTo
            listTo = self._listEmailReceivers
            listCC = []
            listBCC = []
            mime_text_message[
                "Subject"
            ] = "Metadata upload error on {0} for proposal {1}".format(
                self._beamline, self._proposal
            )
            mime_text_message["From"] = replyTo
            mime_text_message["To"] = COMMASPACE.join(listTo)
            if len(listCC) > 0:
                mime_text_message["CC"] = COMMASPACE.join(listCC)
            if len(listBCC) > 0:
                mime_text_message["BCC"] = COMMASPACE.join(listBCC)
            try:
                smtp = smtplib.SMTP("localhost")
                smtp.sendmail(
                    replyTo, listTo + listCC + listBCC, mime_text_message.as_string()
                )
                smtp.quit()
            except Exception:
                pass
        return errorMessage

    def start(self, data_collect_parameters):
        # Metadata
        if (
            self._metadataManagerName is not None
            and self._metaExperimentName is not None
        ):
            try:
                self._proposal = HWR.beamline.session.get_proposal()
                # Create proxy object
                self._metadataManagerClient = MetadataManagerClient(
                    self._metadataManagerName, self._metaExperimentName
                )

                # First check the state of the device server
                serverState = self._metadataManagerClient.get_state()
                if serverState == "RUNNING":
                    # Force end of scan
                    self._metadataManagerClient.end()

                fileinfo = data_collect_parameters["fileinfo"]
                directory = fileinfo["directory"]
                prefix = fileinfo["prefix"]
                run_number = int(fileinfo["run_number"])
                # Connect to ICAT metadata database
                # Strip the prefix from any workflow expTypePrefix
                # TODO: use the ISPyB sample name instead
                sampleName = prefix
                for expTypePrefix in ["line-", "mesh-", "ref-", "burn-", "ref-kappa-"]:
                    if sampleName.startswith(expTypePrefix):
                        sampleName = sampleName.replace(expTypePrefix, "")
                        break
                # The data set name must be unique so we use the ISPyB data collection
                # id
                datasetName = "{0}_{1}_{2}".format(
                    prefix, run_number, self.esrf_multi_collect.collection_id
                )
                self._metadataManagerClient.start(
                    directory, self._proposal, sampleName, datasetName
                )
                self._metadataManagerClient.printStatus()
            except Exception:
                logging.getLogger("user_level_log").warning(
                    "Cannot connect to metadata server"
                )
                errorMessage = self.reportStackTrace()
                logging.getLogger("user_level_log").warning(errorMessage)
                self._metadataManagerClient = None

    def upload_images_to_icat(
        self,
        template,
        prefix,
        run_number,
        directory,
        number_of_images,
        start_image_number,
        overlap,
    ):
        logging.getLogger("user_level_log").info("Uploading to images to ICAT")
        if template.endswith(".h5"):
            if math.fabs(overlap) > 1:
                for image_number in range(1, number_of_images + 1):
                    h5_master_file_name = "{prefix}_{run_number}_{image_number}_master.h5".format(
                        prefix=prefix, run_number=run_number, image_number=image_number
                    )
                    h5_master_file_path = os.path.join(directory, h5_master_file_name)
                    self._metadataManagerClient.appendFile(h5_master_file_path)
                    h5_data_file_name = "{prefix}_{run_number}_{image_number}_data_000001.h5".format(
                        prefix=prefix, run_number=run_number, image_number=image_number
                    )
                    h5_data_file_path = os.path.join(directory, h5_data_file_name)
                    self._metadataManagerClient.appendFile(h5_data_file_path)
            else:
                h5_master_file_name = "{prefix}_{run_number}_{start_image_number}_master.h5".format(
                    prefix=prefix,
                    run_number=run_number,
                    start_image_number=start_image_number,
                )
                h5_master_file_path = os.path.join(directory, h5_master_file_name)
                self._metadataManagerClient.appendFile(h5_master_file_path)
                for index in range(int((number_of_images - 1) / 100) + 1):
                    h5_data_file_name = "{prefix}_{run_number}_{start_image_number}_data_{data_index:06d}.h5".format(
                        prefix=prefix,
                        run_number=run_number,
                        start_image_number=start_image_number,
                        data_index=(index + 1),
                    )
                    h5_data_file_path = os.path.join(directory, h5_data_file_name)
                    self._metadataManagerClient.appendFile(h5_data_file_name)
        else:
            for index in range(number_of_images):
                image_no = index + start_image_number
                image_path = os.path.join(directory, template % image_no)
                self._metadataManagerClient.appendFile(image_path)

    def end(self, data_collect_parameters):
        try:
            dictMetadata = self.getMetadata(data_collect_parameters)
            if self._metadataManagerClient is not None:
                # Upload all images
                fileinfo = data_collect_parameters["fileinfo"]
                prefix = fileinfo["prefix"]
                template = fileinfo["template"]
                directory = fileinfo["directory"]
                run_number = int(fileinfo["run_number"])
                for oscillation_parameters in data_collect_parameters[
                    "oscillation_sequence"
                ]:
                    number_of_images = oscillation_parameters["number_of_images"]
                    start_image_number = oscillation_parameters["start_image_number"]
                    overlap = oscillation_parameters["overlap"]
                    self.upload_images_to_icat(
                        template,
                        prefix,
                        run_number,
                        directory,
                        number_of_images,
                        start_image_number,
                        overlap,
                    )
                # Upload the two paths to the meta data HDF5 files
                pathToHdf5File1 = os.path.join(
                    directory,
                    "{proposal}-{beamline}-{prefix}_{run_number}_{dataCollectionId}.h5".format(
                        beamline=self._beamline,
                        proposal=self._proposal,
                        prefix=prefix,
                        run_number=run_number,
                        dataCollectionId=self.esrf_multi_collect.collection_id,
                    ),
                )
                self._metadataManagerClient.appendFile(pathToHdf5File1)
                pathToHdf5File2 = os.path.join(
                    directory,
                    "{proposal}-{prefix}-{prefix}_{run_number}_{dataCollectionId}.h5".format(
                        proposal=self._proposal,
                        prefix=prefix,
                        run_number=run_number,
                        dataCollectionId=self.esrf_multi_collect.collection_id,
                    ),
                )
                self._metadataManagerClient.appendFile(pathToHdf5File2)
                # Upload meta data as attributes
                # These attributes are common for all ESRF MX beamlines
                dictMetadata = self.getMetadata(data_collect_parameters)
                # import pprint
                # pprint.pprint(dictMetadata)
                for attributeName, value in dictMetadata.items():
                    logging.getLogger("HWR").info(
                        "Setting metadata client attribute '{0}' to '{1}'".format(
                            attributeName, value
                        )
                    )
                    setattr(
                        self._metadataManagerClient.metadataManager,
                        attributeName,
                        str(value),
                    )
                self._metadataManagerClient.printStatus()
                self._metadataManagerClient.end()
        except Exception:
            logging.getLogger("user_level_log").warning("Cannot upload metadata")
            errorMessage = self.reportStackTrace()
            logging.getLogger("user_level_log").warning(errorMessage)
            self._metadataManagerClient = None

    def getMetadata(self, data_collect_parameters):
        """
        Common metadata parameters for ESRF MX beamlines.
        """
        listAttributes = [
            ["MX_beamShape", "beamShape"],
            ["MX_beamSizeAtSampleX", "beamSizeAtSampleX"],
            ["MX_beamSizeAtSampleY", "beamSizeAtSampleY"],
            ["MX_dataCollectionId", "collection_id"],
            ["MX_directory", "fileinfo.directory"],
            ["MX_exposureTime", "oscillation_sequence.exposure_time"],
            ["MX_flux", "flux"],
            ["MX_fluxEnd", "flux_end"],
            ["MX_numberOfImages", "oscillation_sequence.number_of_images"],
            ["MX_oscillationRange", "oscillation_sequence.range"],
            ["MX_oscillationStart", "oscillation_sequence.start"],
            ["MX_oscillationOverlap", "oscillation_sequence.overlap"],
            ["MX_resolution", "resolution"],
            ["MX_startImageNumber", "oscillation_sequence.start_image_number"],
            ["MX_scanType", "experiment_type"],
            ["MX_template", "fileinfo.template"],
            ["MX_transmission", "transmission"],
            ["MX_xBeam", "xBeam"],
            ["MX_yBeam", "yBeam"],
            ["InstrumentMonochromator_wavelength", "wavelength"],
        ]
        dictMetadata = {}
        for attribute in listAttributes:
            if isinstance(attribute, list):
                attributeName = attribute[0]
                keyName = attribute[1]
            else:
                attributeName = attribute
                keyName = attribute
            value = None
            if "." in keyName:
                parent, child = str(keyName).split(".")
                parentObject = data_collect_parameters[parent]
                if isinstance(parentObject, type([])):
                    parentObject = parentObject[0]
                if child in parentObject:
                    value = str(parentObject[child])
            elif keyName in data_collect_parameters:
                value = str(data_collect_parameters[keyName])
            if value is not None:
                dictMetadata[attributeName] = value
        # Template - replace python formatting with hashes
        dictMetadata["MX_template"] = dictMetadata["MX_template"].replace(
            "%04d", "####"
        )
        # Motor positions
        motorNames = ""
        motorPositions = ""
        for motor, position in data_collect_parameters["motors"].items():
            if isinstance(motor, string_types):
                motorName = motor
            else:
                nameAttribute = getattr(motor, "name")
                if isinstance(nameAttribute, string_types):
                    motorName = nameAttribute
                else:
                    motorName = nameAttribute()
            if motorNames == "":
                motorNames = motorName
                motorPositions = str(round(position, 3))
            else:
                motorNames += " " + motorName
                if position is not None:
                    motorPositions += " " + str(round(position, 3))
                else:
                    motorPositions += " None"
        dictMetadata["MX_motors_name"] = motorNames
        dictMetadata["MX_motors_value"] = motorPositions
        # Detector distance
        distance = HWR.beamline.detector.distance.get_value()
        if distance is not None:
            dictMetadata["MX_detectorDistance"] = distance
        # Aperture
        if HWR.beamline.beam is not None and HWR.beamline.beam.aperture is not None:
            dictMetadata["MX_aperture"] = HWR.beamline.beam.aperture.get_value()
        return dictMetadata


if __name__ == "__main__":
    metadataManagerName = "id30a1/metadata/ingest"
    metaExperimentName = "id30a1/metadata/experiment"
    client = MetadataManagerClient(metadataManagerName, metaExperimentName)

    client.start(
        "/data/visitor/mx415/id30a1/20161014/RAW_DATA",
        "mx415",
        "sample1",
        "dataset_20161014_1",
    )
    client.appendFile("/data/visitor/mx415/id30a1/20161014/RAW_DATA/t1/test1.txt")
    client.appendFile("/data/visitor/mx415/id30a1/20161014/RAW_DATA/t1/test2.txt")
    client.printStatus()
    client.end()
