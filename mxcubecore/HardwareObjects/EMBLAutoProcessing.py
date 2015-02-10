"""
Descript. :
"""
import os
import time
import logging
import tempfile
import gevent 
import subprocess
from HardwareRepository.BaseHardwareObjects import HardwareObject
from stat import S_IRGRP, S_IROTH, S_IRUSR, S_IWUSR

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
            self.current_autoproc_procedure = gevent.spawn(self.autoprocessing_procedure,
                                                           process_event, 
                                                           params_dict, 
                                                           frame_number)
            self.current_autoproc_procedure.link(self.autoproc_done)

    def autoprocessing_procedure(self, process_event, params_dict, frame_number):
        """
        Descript. : 
        """
        for program in self.autoproc_programs:
            if process_event == program.getProperty("event"):
                executable = program.getProperty("executable")
                if os.path.isfile(executable):	
                    will_execute = False
                    if process_event == "after": 
                        input_filename, will_execute = self.prepare_for_autoprocessing(process_event, params_dict)
                        if will_execute:
                            endOfLineToExecute = ' ' + input_filename + ' ' + \
                                params_dict["fileinfo"]["directory"]

                    if process_event == 'end_multicollect':
                        endOfLineToExecute = ""
                    if process_event == 'image':
                        if frame_number == 1 or frame_number == params_dict['oscillation_sequence'][0]['number_of_images']:
                            endOfLineToExecute = " %s %s/%s_%d_%0.4d.cbf" % (params_dict["fileinfo"]["directory"],
                               params_dict["fileinfo"]["directory"], 
                               params_dict["fileinfo"]["prefix"],
                               params_dict["fileinfo"]["run_number"], 
                               frame_number)
                            will_execute = True 	
                    if will_execute:	
                        lineToExecute = executable + endOfLineToExecute
                        logging.info("Process event %s, executing %s" % (process_event, str(lineToExecute)))
                        subprocess.Popen(str(lineToExecute), shell = True, 
                                    stdin = None, stdout = None, stderr = None, 
                                    close_fds = True)	
                else:
                    logging.getLogger().error("No program to execute found (%s)", executable)

    def autoproc_done(self, current_autoproc):
        """
        Descript. :
        """
        self.current_autoproc_procedure = None

    def prepare_for_autoprocessing(self, event, params):
        """
        Descript. :
        """
        WAIT_XDS_TIMEOUT = 20
        WAIT_XDS_RESOLUTION = 5
	
        path = params.get("xds_dir")
        input_file = os.path.join(path, 'XDS.INP')	

	#Probably try...
        nres = float(params.get("residues"))
        sg_opt = params.get("sample_reference").get("spacegroup")
        spacegroup = None
        if sg_opt:
            if len(sg_opt) > 0:	    
                spacegroup = sg_opt
        unit_cell_constants = params.get("cell")
        cell = None
        if unit_cell_constants:
            if len(unit_cell_constants) > 0:
                cell = unit_cell_constants
        xds_appeared = False
        wait_xds_start = time.time()
        logging.debug('Waiting for XDS.INP file: %s' %input_file)	
        while not xds_appeared and time.time() - wait_xds_start < WAIT_XDS_TIMEOUT:
            if os.path.exists(input_file) and os.stat(input_file).st_size > 0:
                xds_appeared = True
                logging.debug('XDS.INP file is there, size={0}'.format(os.stat(input_file).st_size))
            else:
                gevent.sleep(WAIT_XDS_RESOLUTION)
        if not xds_appeared:
            logging.error('XDS.INP file ({0}) failed to appear after {1} seconds'.format(input_file, WAIT_XDS_TIMEOUT))
            return None, False

        output_file = tempfile.NamedTemporaryFile(suffix='.xml',
                                                  prefix='edna-autoproc-results-',
                                                  dir=path,
                                                  delete=False)	
	
        output_path = output_file.name
        output_file.close()
        os.chmod(output_path, S_IRUSR|S_IWUSR|S_IRGRP|S_IROTH)

        input_template = '''<?xml version="1.0"?>
                            <XSDataAutoprocInput>
                             <input_file>
                              <path>
                               <value>{input_file}</value>
                              </path>
                             </input_file>
                             <data_collection_id>
                              <value>{dcid}</value>
                             </data_collection_id>
                             <output_file>
                              <path>
                               <value>{output_path}</value>
                              </path>
                             </output_file>
                             {nres_fragment}
                             {spacegroup_fragment}
                             {cell_fragment}
                            </XSDataAutoprocInput>'''

        if nres is not None and nres != 0:
            nres_fragment = """  <nres>
   	                          <value>{0}</value>
                                 </nres>""".format(nres)
        else:
            nres_fragment = ""
        if spacegroup is not None:
            spacegroup_fragment = """  <spacegroup>
                                        <value>{0}</value>
                                       </spacegroup>""".format(spacegroup)
        else:
            spacegroup_fragment = ""
        if cell is not None:
            cell_fragment = """  <unit_cell>
                                  <value>{0}</value>
                                 </unit_cell>""".format(cell)
        else:
            cell_fragment = ""
        input_dm = input_template.format(input_file=input_file,
                                   	 dcid=params.get("collection_id"),
                                 	 output_path=output_path,
                                 	 nres_fragment=nres_fragment,
                                 	 cell_fragment=cell_fragment,
                                 	 spacegroup_fragment=spacegroup_fragment)

        dm_file = tempfile.NamedTemporaryFile(suffix='.xml',
                                    	      prefix='edna-autoproc-input-',
                                     	      dir=path,
                                      	      delete=False)
        dm_path = dm_file.name
        dm_file.file.write(input_dm)
        dm_file.close()
        os.chmod(dm_path, S_IRUSR|S_IWUSR|S_IRGRP|S_IROTH)

        return dm_path, True
