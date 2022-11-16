#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name] XalocEDNACharacterisation

[Description]
Prepare files and launch strategy pipeline (online) to the ALBA cluster

[Signals]
- None
"""

from __future__ import print_function

import os
import time
import subprocess

import logging

from EDNACharacterisation import EDNACharacterisation
from XSDataMXCuBEv1_3 import XSDataResultMXCuBE
from XSDataCommon import XSDataFile, XSDataString

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocEDNACharacterisation(EDNACharacterisation):

    def __init__(self, name):
        EDNACharacterisation.__init__(self, name)
        self.logger = logging.getLogger("HWR.XalocEDNACharacterisation")
        self.job = None
        self.output_dir = None
        self.input_file = None
        self.results_file = None
        self.cluster = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        EDNACharacterisation.init(self)
        self.cluster = self.get_object_by_role("cluster")

    def prepare_edna_input(self, input_file, output_dir):
        # used for strategy calculation (characterization) using data analysis cluster
        # Xaloc specific
        input_file.process_directory = output_dir
        output_dir = XSDataFile(XSDataString(output_dir))
        input_file.setOutputFileDirectory(output_dir)

    #def _run_edna(self, dc_id, input_file, results_file, output_dir):
        #return self.run(dc_id, input_file, results_file, output_dir)

    #def run(self, *args):

        #log = logging.getLogger('user_level_log')
        #dc_id, input_file, results_file, output_dir = args
        #jobname = os.path.basename(os.path.dirname(output_dir))

        #self.logger.debug("Submitting Job")
        #self.logger.debug(" job_name: %s" % jobname)
        #self.logger.debug(" input file: %s" % input_file)
        #self.logger.debug(" results file: %s" % results_file)
        #self.logger.debug(" output directory: %s" % output_dir)

        #self.job = self.cluster.create_strategy_job(dc_id, input_file, output_dir)
        #self.cluster.run(self.job)

        #log.info("Characterization Job ID: %s" % self.job.id)

        #self.output_dir = os.path.dirname(input_file)
        #self.input_file = os.path.basename(input_file)
        ## self.results_file = self.fix_path(results_file)
        #self.results_file = results_file
        #self.logger.debug("Results file: %s" % self.results_file)

        #state = self.cluster.wait_done(self.job)

        #if state == "COMPLETED":
            #log.info("Job completed")
            #time.sleep(0.5)
            #result = self.get_result()
        #else:
            #log.info("Job finished without success / state was %s" %
                              #state)
            #result = ""

        #return result

    # TODO: Deprecated
    #def fix_path(self, path):
        #out_path = path.replace('PROCESS_DATA', 'PROCESS_DATA/RESULTS')
        ## dirname = os.path.dirname(path)
        ## basename = os.path.basename(path)
        ## outpath = os.path.join(dirname,'RESULTS',basename)
        #return out_path

    # TODO: Unused??
    def wait_done(self):

        state = None
        time.sleep(0.5)
        self.logger.debug("Polling for Job state")

        try:
            state = self.job.state
            self.logger.debug("Job / is %s" % str(state))
        except Exception as e:
            self.logger.debug(
                "Polling for Job state, exception happened\n%s" % str(e))

        while state in ["RUNNING", "PENDING"]:
            self.logger.debug("Job / is %s" % state)
            time.sleep(0.5)
            state = self.job.state

        self.logger.debug("Returning %s" % str(state))
        return state

    def get_result(self):

        jobstatus = self.job.status

        self.logger.debug("Characterization Job COMPLETED")
        self.logger.debug("Status: %s" % jobstatus)
        self.logger.debug("Results file: %s" % self.results_file)
        if os.path.exists(self.results_file):
            result = XSDataResultMXCuBE.parseFile(self.results_file)
            self.logger.debug("EDNA Result loaded from file (type is %s" %
                              str(type(result)))
        else:
            self.logger.debug(
                "Cannot find output file, returning empty string.")
            result = ""

        return result

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

        firstImage = None
        #for dataSet in edna_input.dataSet:
        for dataSet in edna_input.getDataSet():
            for imageFile in dataSet.imageFile:
                if imageFile.getPath() is None:
                    continue
                firstImage = imageFile.path.value
                break

        listImageName = os.path.basename(firstImage).split("_")
        prefix = "_".join(listImageName[:-2])
        run_number = listImageName[-2]

        if hasattr(edna_input, "process_directory"):
            edna_directory = os.path.join(
                edna_input.process_directory, 
                "characterisation_%s_run%s_%s" % (prefix, run_number, dc_id )
            )
            os.makedirs(edna_directory)
        else:
            raise RuntimeError("No process directory specified in edna_input")

        edna_input_file = os.path.join(edna_directory, "EDNAInput_%s.xml" % dc_id)
        
        self.prepare_edna_input(edna_input, edna_directory)

        try:
            edna_input.exportToFile(edna_input_file)
        except:
            import traceback
            logging.getLogger("HWR").debug(" problem generating input file")
            logging.getLogger("HWR").debug(" %s " % traceback.format_exc())

        edna_results_file = os.path.join(edna_directory, "EDNAOutput_%s.xml" % dc_id)

        msg = "Starting EDNA using xml file %r", edna_input_file
        logging.getLogger("queue_exec").info(msg)
        #TODO: ALBA used local version of _run_edna to pass dc_id. 
        # Not sure why the implemented method is not used, 
        # self.result = self._run_edna(edna_input_file, edna_results_file, path)
        self.result = self._run_edna_xaloc(dc_id, edna_input_file, edna_results_file, edna_directory)

        self.processing_done_event.clear()
        return self.result

    def _run_edna_xaloc(self, dc_id, input_file, results_file, output_dir):
        """Starts EDNA"""
        log = logging.getLogger('user_level_log')
        if self.collect_obj.current_dc_parameters["status"] == "Failed":
            log.error("Collection failed, no characterisation done") 
            return

        msg = "Starting EDNA characterisation using xml file %s" % input_file
        logging.getLogger("queue_exec").info(msg)

        jobname = os.path.basename( os.path.dirname(output_dir) )

        self.logger.debug("Submitting Job")
        self.logger.debug(" job_name: %s" % jobname)
        self.logger.debug(" input file: %s" % input_file)
        self.logger.debug(" results file: %s" % results_file)
        self.logger.debug(" output directory: %s" % output_dir)

        self.job = self.cluster.create_strategy_job(dc_id, input_file, output_dir)
        self.cluster.run(self.job)

        log.info("Characterization Job ID: %s" % self.job.id)

        self.output_dir = os.path.dirname(input_file)
        self.input_file = os.path.basename(input_file)
        self.results_file = results_file
        self.logger.debug("Results file: %s" % self.results_file)

        state = self.cluster.wait_done(self.job)

        if state == "COMPLETED":
            log.info("Job completed")
            time.sleep(0.5)
            result = self.get_result()
        else:
            log.info("Job finished without success / state was %s" %
                              state)
            result = ""

        return result

def test_hwo(hwo):
    ofile = "/tmp/edna/edna_result"
    odir = "/tmp/edna"
    test_input_file = "/beamlines/bl13/projects/cycle2018-I/2018012551-bcalisto/" \
                      "mx2018012551/DATA/20180131/PROCESS_DATA/" \
                      "characterisation_ref-Thrombin-TB-TTI1_A_run1_1/" \
                      "EDNAInput_2004391.xml"
    result = hwo.run_edna(test_input_file, ofile, odir)
    print(result)
