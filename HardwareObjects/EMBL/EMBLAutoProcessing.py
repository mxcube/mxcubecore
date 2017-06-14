"""
Descript. :
"""
import os
import time
import logging
import gevent 
import subprocess

from XSDataAutoprocv1_0 import XSDataAutoprocInput

from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataString

from HardwareRepository.BaseHardwareObjects import HardwareObject


class EMBLAutoProcessing(HardwareObject):
    """
    Descript. :
    """
    def __init__(self, name):
        """
        Descript. :
        """
        HardwareObject.__init__(self, name)
        self.result = None
        self.autoproc_programs = None
        self.current_autoproc_procedure = None

    def init(self):
        """
        Descript. :
        """
        self.autoproc_programs = self["programs"]

    def execute_autoprocessing(self, process_event, params_dict, frame_number):
        """
        Descript. : 
        """
        if self.autoproc_programs is not None:
            self.current_autoproc_procedure = gevent.spawn(self.autoproc_procedure,
                                                           process_event, 
                                                           params_dict, 
                                                           frame_number)
            self.current_autoproc_procedure.link(self.autoproc_done)

    def autoproc_procedure(self, process_event, params_dict, frame_number):
        """
        Descript. : 

        Main autoprocessing procedure. At the beginning correct event (defined 
        in xml) is found. If the event is executable then accordingly to the 
        event type (image, after) then the sequence is executed:  
        Implemented tasks:
           - after : Main autoprocessing procedure
                     1. Input file is generated with create_autoproc_input 
                        Input file has name "edna-autoproc-input-%Y%m%d_%H%M%S.xml".
                     2. Then it waits for XDS.INP directory and if it exists then
                        creates input file
                     3. edna_autoprocessing.sh script is executed with parameters:
                        - arg1 : generated xml file
                        - arg2 : process dir 
                     4. script executes EDNA EDPluginControlAutoprocv1_0
           - image : Thumbnail generation for first and last image
                     1. No input file is generated
                     2. edna_thumbnails.sh script is executed with parameters:
                        - arg1 : image base dir (place where thumb will be generated)
                        - arg2 : file name
        """
        for program in self.autoproc_programs:
            if process_event == program.getProperty("event"):
                executable = program.getProperty("executable")
                if os.path.isfile(executable):	
                    will_execute = False
                    if process_event == "after": 
                        input_filename, will_execute = self.create_autoproc_input(process_event, params_dict)
                        if will_execute:
                            endOfLineToExecute = ' ' + input_filename + ' ' + \
                                params_dict["fileinfo"]["directory"]
                    if process_event == 'image':
                        if frame_number == 1 or frame_number == params_dict['oscillation_sequence'][0]['number_of_images']:
                            endOfLineToExecute = " %s %s/%s_%d_%05d.cbf" % (params_dict["fileinfo"]["directory"],
                               params_dict["fileinfo"]["directory"], 
                               params_dict["fileinfo"]["prefix"],
                               params_dict["fileinfo"]["run_number"], 
                               frame_number)
                            will_execute = True 	
                    if will_execute:	
                        lineToExecute = executable + endOfLineToExecute
                        #logging.info("Process event %s, executing %s" % (process_event, str(lineToExecute)))
                        subprocess.Popen(str(lineToExecute), shell = True, 
                                    stdin = None, stdout = None, stderr = None, 
                                    close_fds = True)	
                else:
                    logging.getLogger().error("EMBLAutoprocessing: No program to execute found (%s)", executable)

    def autoproc_done(self, current_autoproc):
        """
        Descript. :
        """
        self.current_autoproc_procedure = None

    def create_autoproc_input(self, event, params):
        """
        Descript. :
        """
        WAIT_XDS_TIMEOUT = 20
        WAIT_XDS_RESOLUTION = 1

        file_name_timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        autoproc_path = params.get("xds_dir")
        autoproc_xds_filename = os.path.join(autoproc_path, "XDS.INP")
        autoproc_input_filename = os.path.join(autoproc_path, 
                                                "edna-autoproc-input-%s" % \
                                                file_name_timestamp)
        autoproc_output_file_name = os.path.join(autoproc_path, 
                                                 "edna-autoproc-results-%s" % \
                                                 file_name_timestamp)

        autoproc_input = XSDataAutoprocInput() 
        autoproc_xds_file = XSDataFile()
        autoproc_xds_file.setPath(XSDataString(autoproc_xds_filename))
        autoproc_input.setInput_file(autoproc_xds_file)

        autoproc_output_file = XSDataFile()
        autoproc_output_file.setPath(XSDataString(autoproc_output_file_name))
        autoproc_input.setOutput_file(autoproc_output_file)

        autoproc_input.setData_collection_id(XSDataInteger(params.get("collection_id")))
        residues_num = float(params.get("residues", 0))
        if residues_num != 0:
            autoproc_input.setNres(XSDataDouble(residues_num)) 
        space_group = params.get("sample_reference").get("spacegroup", "")
        if len(space_group) > 0:
            autoproc_input.setSpacegroup(XSDataString(space_group)) 
        unit_cell = params.get("sample_reference").get("cell", "")
        if len(unit_cell) > 0:
            autoproc_input.setUnit_cell(XSDataString(unit_cell))
       
        #Maybe we have to check if directory is there. Maybe create dir with mxcube
        xds_appeared = False
        wait_xds_start = time.time()
        logging.debug('EMBLAutoprocessing: Waiting for XDS.INP file: %s' % autoproc_xds_filename)
        while not xds_appeared and time.time() - wait_xds_start < WAIT_XDS_TIMEOUT:
            if os.path.exists(autoproc_xds_filename) and os.stat(autoproc_xds_filename).st_size > 0:
                xds_appeared = True
                logging.debug('EMBLAutoprocessing: XDS.INP file is there, size={0}'.\
                        format(os.stat(autoproc_xds_filename).st_size))
            else:
                os.system("ls %s> /dev/null"%(os.path.dirname(autoproc_path)))
                gevent.sleep(WAIT_XDS_RESOLUTION)
        if not xds_appeared:
            logging.error('EMBLAutoprocessing: XDS.INP file ({0}) failed to appear after {1} seconds'.\
                    format(autoproc_xds_filename, WAIT_XDS_TIMEOUT))
            return None, False
 
        autoproc_input.exportToFile(autoproc_input_filename)

        return autoproc_input_filename, True
