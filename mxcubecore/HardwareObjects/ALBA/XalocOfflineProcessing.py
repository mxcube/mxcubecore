#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name]
XalocOfflineProcessing

[Description]
Hardware Object used to prepare and start the autoprocessing
pipelines for ALBA beamlines.

[Emitted signals]
- None

TODO: the same xml input files can be used for different processing
TODO: implement small mol processing
"""

from __future__ import print_function

import os
import math
import logging

from mxcubecore.BaseHardwareObjects import HardwareObject
from XSDataCommon import XSDataBoolean, XSDataFile, XSDataString, XSDataInteger, XSDataDouble
from XalocXSDataAutoprocv1_0 import XalocXSDataAutoprocInput  
from XalocXSDataControlAutoPROCv1_0 import XalocXSDataInputControlAutoPROC  
from XalocXSDataControlXia2DIALSv1_0 import XalocXSDataInputXia2DIALS  

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"


class XalocOfflineProcessing(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.logger = logging.getLogger("HWR.XalocOfflineProcessing")
        self.template_dir = None
        self.detsamdis_hwobj = None
        self.chan_beamx = None
        self.chan_beamy = None
        self.ednaproc_input_file = None
        self.autoproc_input_file = None
        self.cluster = None
        self.sample_is_small_molecule = False

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        self.template_dir = self.get_property("template_dir")
        self.logger.debug("Autoprocessing template_dir = %s" %
                                       self.template_dir)
        # TODO: include these values in dc_pars or osc_seq dictionaries
        self.detsamdis_hwobj = self.get_object_by_role("detector_distance")
        self.chan_beamx = self.get_channel_object('beamx')
        self.chan_beamy = self.get_channel_object('beamy')

        self.cluster = self.get_object_by_role("cluster")

    def create_input_files(self, dc_pars):

        self.logger.debug("XalocOfflineProcessing create_input_files dc_pars = %s " % dc_pars )
        xds_dir = dc_pars['xds_dir']
        mosflm_dir = dc_pars['mosflm_dir']
        ednaproc_dir = dc_pars['ednaproc_dir']
        autoproc_dir = dc_pars['autoproc_dir']

        fileinfo = dc_pars['fileinfo']
        osc_seq = dc_pars['oscillation_sequence'][0]

        prefix = fileinfo['prefix']
        runno = fileinfo['run_number']

        exp_time = osc_seq['exposure_time']

        # start_angle = osc_seq['start']
        nb_images = osc_seq['number_of_images']
        start_img_num = osc_seq['start_image_number']
        angle_increment = osc_seq['range']

        wavelength = osc_seq.get('wavelength', 0)

        xds_template_name = 'XDS_TEMPLATE.INP'
        mosflm_template_name = 'mosflm_template.dat'

        xds_template_path = os.path.join(self.template_dir, xds_template_name)
        mosflm_template_path = os.path.join(self.template_dir, mosflm_template_name)

        xds_file = os.path.join(xds_dir, "XDS.INP")
        mosflm_file = os.path.join(mosflm_dir, "mosflm.dat")

        # PREPARE VARIABLES
        detsamdis = self.detsamdis_hwobj.get_value()
        beamx, beamy = self.chan_beamx.get_value(), self.chan_beamy.get_value()

        mbeamx, mbeamy = beamy * 0.172, beamx * 0.172

        data_range_start_num = start_img_num
        data_range_finish_num = start_img_num + nb_images - 1
        background_range_start_num = start_img_num
        spot_range_start_num = start_img_num
        minimum_range = 0
        background_range_finish_num = 0
        spot_range_finish_num = 0

        if angle_increment != 0:
            minimum_range = int(round(20 / angle_increment))
        elif angle_increment == 0:
            minimum_range = 1
        if nb_images >= minimum_range:
            background_range_finish_num = start_img_num + minimum_range - 1
        if nb_images >= minimum_range:
            spot_range_finish_num = start_img_num + minimum_range - 1
        if nb_images < minimum_range:
            background_range_finish_num = start_img_num + nb_images - 1
        if nb_images < minimum_range:
            spot_range_finish_num = start_img_num + nb_images - 1

        test_low_res = 8.
        largest_vector = 0.172 * ((max(beamx, 2463 - beamx))**2 +
                                  (max(beamy, 2527 - beamy))**2)**0.5
        test_high_res = round(wavelength / (2 * math.sin(0.5 * math.atan(
            largest_vector / detsamdis))), 2)
        low_res = 50.
        high_res = test_high_res
        data_filename = prefix + '_' + str(runno) + '_????'
        mdata_filename = prefix + '_' + str(runno) + '_####.cbf'
        seconds = 5 * exp_time

        if angle_increment < 1 and not angle_increment == 0:
            seconds = 5 * exp_time / angle_increment

        # DEFINE SG/UNIT CELL
        spacegroup_number = ''
        unit_cell_constants = ''

        datapath_dir = os.path.abspath(xds_file).replace('PROCESS_DATA', 'RAW_DATA')
        datapath_dir = os.path.dirname(os.path.dirname(datapath_dir)) + os.path.sep

        # CREATE XDS.INP FILE
        xds_templ = open(xds_template_path, "r").read()

        xds_templ = xds_templ.replace('###BEAMX###', str(round(beamx, 2)))
        xds_templ = xds_templ.replace("###BEAMY###", str(round(beamy, 2)))
        xds_templ = xds_templ.replace("###DETSAMDIS###", str(round(detsamdis, 2)))
        xds_templ = xds_templ.replace("###ANGLEINCREMENT###", str(angle_increment))
        xds_templ = xds_templ.replace("###WAVELENGTH###", str(wavelength))
        xds_templ = xds_templ.replace("###DATARANGESTARTNUM###",
                                      str(data_range_start_num))
        xds_templ = xds_templ.replace("###DATARANGEFINISHNUM###",
                                      str(data_range_finish_num))
        xds_templ = xds_templ.replace("###BACKGROUNDRANGESTART###",
                                      str(background_range_start_num))
        xds_templ = xds_templ.replace("###BACKGROUNDRANGEFINISHNUM###",
                                      str(background_range_finish_num))
        xds_templ = xds_templ.replace("###SPOTRANGESTARTNUM###",
                                      str(spot_range_start_num))
        xds_templ = xds_templ.replace("###SPOTRANGEFINISHNUM###",
                                      str(spot_range_finish_num))
        xds_templ = xds_templ.replace("###TESTLOWRES###", str(test_low_res))
        xds_templ = xds_templ.replace("###TESTHIGHRES###", str(test_high_res))
        xds_templ = xds_templ.replace("###LOWRES###", str(low_res))
        xds_templ = xds_templ.replace("###HIGHRES###", str(high_res))
        xds_templ = xds_templ.replace("###DIRECTORY###", str(datapath_dir))
        xds_templ = xds_templ.replace("###FILENAME###", str(data_filename))
        xds_templ = xds_templ.replace("###SECONDS###", str(int(seconds)))
        xds_templ = xds_templ.replace("###LYSOZYME_SPACE_GROUP_NUMBER###",
                                      str(spacegroup_number))
        xds_templ = xds_templ.replace("###LYSOZYME_UNIT_CELL_CONSTANTS###",
                                      str(unit_cell_constants))

        open(xds_file, "w").write(xds_templ)

        # CREATE MOSFLM.DAT FILE
        mosflm_templ = open(mosflm_template_path, "r").read()

        mosflm_templ = mosflm_templ.replace("###DETSAMDIS###", str(round(detsamdis, 2)))
        mosflm_templ = mosflm_templ.replace('###BEAMX###', str(round(mbeamx, 2)))
        mosflm_templ = mosflm_templ.replace("###BEAMY###", str(round(mbeamy, 2)))
        mosflm_templ = mosflm_templ.replace("###DIRECTORY###", str(datapath_dir))
        mosflm_templ = mosflm_templ.replace("###FILENAME###", str(mdata_filename))
        mosflm_templ = mosflm_templ.replace("###WAVELENGTH###", str(wavelength))
        mosflm_templ = mosflm_templ.replace("###DATARANGESTARTNUM###",
                                            str(data_range_start_num))

        open(mosflm_file, "w").write(mosflm_templ)

        # CREATE EDNAPROC XML FILE
        collection_id = dc_pars['collection_id']
        ednaproc_dir = dc_pars['ednaproc_dir']

        ednaproc_input_file = os.path.join(ednaproc_dir, "EDNAprocInput_%d.xml" %
                                           collection_id)
        ednaproc_input = XalocXSDataAutoprocInput()

        input_file = XSDataFile()
        path = XSDataString()
        path.setValue(xds_file)
        input_file.setPath(path)

        ednaproc_input.setInput_file(input_file)
        ednaproc_input.setData_collection_id(XSDataInteger(collection_id))

        ednaproc_input = self.add_user_input_to_xml(ednaproc_input, dc_pars)
        
        ednaproc_input.exportToFile(ednaproc_input_file)
        self.ednaproc_input_file = ednaproc_input_file

        # CREATE AUTOPROC XML FILE
        self.create_autoproc_edna_input_file(dc_pars, data_range_start_num, data_range_finish_num, mdata_filename)
        self.create_xia2_edna_input_file(dc_pars, data_range_start_num, data_range_finish_num, mdata_filename)
        self.create_xia2chem_edna_input_file(dc_pars, data_range_start_num, data_range_finish_num, mdata_filename)

    def create_autoproc_edna_input_file(self, dc_pars, fromN, toN, template, ispyb=True):

        # Get data from data collection parameters
        collection_id = dc_pars['collection_id']
        images_dir = dc_pars['fileinfo']['directory']
        template = template
        first_image_nb = fromN
        last_image_nb = toN
        output_dir = dc_pars['autoproc_dir']

        #autoproc_input = XSDataInputControlAutoPROC()
        autoproc_input = XalocXSDataInputControlAutoPROC()
        # Add specific configuration file by the slurm script
        try: autoproc_input.setConfigDef(XSDataFile(XSDataString("__configDef")))
        except: pass

        if ispyb:
            autoproc_input.setDataCollectionId(XSDataInteger(collection_id))
        else:
            autoproc_input.setDirN(XSDataFile(XSDataString(images_dir)))
            autoproc_input.setFromN(XSDataInteger(first_image_nb))
            autoproc_input.setToN(XSDataInteger(last_image_nb))
            autoproc_input.setTemplateN(XSDataString(template))

        # When the user does not give a cell, the cell parameters are set to 0, 
        #  the EDNA autoproc plugin does not accept this
        # TODO: dont add cell parameters unless specified by the user
        #autoproc_input = self.add_user_input_to_xml(autoproc_input, dc_pars)            
            
        # Export file
        autoproc_input_filename = os.path.join(output_dir,
                                               "AutoPROCInput_%d.xml" % collection_id)
        autoproc_input.exportToFile(autoproc_input_filename)
        self.autoproc_input_file = autoproc_input_filename

    def create_xia2_edna_input_file(self, dc_pars, fromN, toN, template, ispyb=True):
        collection_id = dc_pars['collection_id']
        images_dir = dc_pars['fileinfo']['directory']
        template = template
        first_image_nb = fromN
        last_image_nb = toN
        output_dir = dc_pars['xia2_dir']
        first_image_string = os.path.join(images_dir,template.replace('####',"%04d" % first_image_nb))
        
        # Create EDNA data model input file
        xia2_input = XalocXSDataInputXia2DIALS()

        if ispyb:
            xia2_input.setDiffractionImage(XSDataString(first_image_string))
            xia2_input.setDataCollectionId(XSDataInteger(collection_id))
        else:
            raise NotImplementedError("Cannot process with XIA2 without using ISPyB")
        
        #xia2_input = self.add_user_input_to_xml(xia2_input, dc_pars)            

        # Export file
        xia2_input_filename = os.path.join(output_dir, "XIA2Input_%d.xml" % collection_id) 
        xia2_input.exportToFile(xia2_input_filename)
        self.xia2_input_file = xia2_input_filename
        
    def create_xia2chem_edna_input_file(self, dc_pars, fromN, toN, template, ispyb=True):
        collection_id = dc_pars['collection_id']
        images_dir = dc_pars['fileinfo']['directory']
        template = template
        first_image_nb = fromN
        last_image_nb = toN
        output_dir = dc_pars['xia2chem_dir']
        first_image_string = os.path.join(images_dir,template.replace('####',"%04d" % first_image_nb))
        
        # Create EDNA data model input file
        xia2_input = XalocXSDataInputXia2DIALS()

        if ispyb:
            xia2_input.setDiffractionImage(XSDataString(first_image_string))
            xia2_input.setDataCollectionId(XSDataInteger(collection_id))
        else:
            raise NotImplementedError("Cannot process with XIA2 chem without using ISPyB")
        #xia2_input = self.add_user_input_to_xml(xia2_input, dc_pars)            

        detsamdis = self.detsamdis_hwobj.get_value()
        osc_seq = dc_pars['oscillation_sequence'][0]
        wavelength = osc_seq.get('wavelength', 0)
        beamx, beamy = self.chan_beamx.get_value(), self.chan_beamy.get_value()
        largest_vector = 0.172 * ((max(beamx, 2463 - beamx))**2 +
                                  (max(beamy, 2527 - beamy))**2)**0.5

        max_det_res = round(wavelength / (2 * math.sin(0.5 * math.atan(
            largest_vector / detsamdis))), 2)
        max_det_res =  dc_pars['resolution']['upper']

        xia2_input.setDetector_max_res( XSDataDouble(max_det_res) )
        xia2_input.set_small_molecule_3dii( XSDataBoolean(True) )
        
        # Export file
        xia2_input_filename = os.path.join(output_dir, "XIA2Input_%d.xml" % collection_id) 
        xia2_input.exportToFile(xia2_input_filename)
        self.xia2chem_input_file = xia2_input_filename

    def add_user_input_to_xml(self, xsd_autoproc_input, params):
        residues_num = float(params.get("residues", 0))
        # These lines are not compatible with the GP AutoPROC module
        #if residues_num != 0:
            #xsd_autoproc_input.setNres(XSDataDouble(residues_num))
        space_group = params.get("sample_reference").get("spacegroup", "")
        if not isinstance(space_group, int) and len(space_group) > 0:
            xsd_autoproc_input.setSpacegroup(XSDataString(space_group))
        unit_cell = params.get("sample_reference").get("cell", "")
        if len(unit_cell) > 0:
            xsd_autoproc_input.setUnit_cell(XSDataString(unit_cell))
        return xsd_autoproc_input
        
    def trigger_auto_processing(self, dc_pars):

        dc_id = dc_pars['collection_id']
        self.logger.debug("Collection_id = %s " % dc_id)

        # EDNAProc
        ednaproc_dir = dc_pars['ednaproc_dir']
        logging.getLogger('user_level_log').info("Trigger EDNAProc processing")
        job = self.cluster.create_ednaproc_job(dc_id, self.ednaproc_input_file, ednaproc_dir)
        ##job.run()
        self.cluster.run(job)
        self.logger.debug("EDNAProc input file = %s " % self.ednaproc_input_file)
        self.logger.debug("Output dir = %s " % ednaproc_dir)
        logging.getLogger('user_level_log').info("EDNAProc job ID: %s" % job.id)

        # AutoPROC
        autoproc_dir = dc_pars['autoproc_dir']
        logging.getLogger('user_level_log').info("Trigger AutoPROC processing")
        job = self.cluster.create_autoproc_job(dc_id, self.autoproc_input_file, autoproc_dir)
        self.logger.debug("AutoPROC input file = %s " % self.autoproc_input_file)
        ##job.run()
        self.cluster.run(job)
        self.logger.debug("Output dir = %s " % autoproc_dir)
        logging.getLogger('user_level_log').info("AutoPROC job ID: %s" % job.id)

        # XIA2
        xia2_dir = dc_pars['xia2_dir']
        logging.getLogger('user_level_log').info("Trigger XIA2 processing")
        job = self.cluster.create_xia2_job(dc_id, self.xia2_input_file, xia2_dir)
        self.cluster.run(job)
        self.logger.debug("XIA2 input file = %s " % self.xia2_input_file)
        self.logger.debug("Output dir = %s " % xia2_dir)
        logging.getLogger('user_level_log').info("XIA2 job ID: %s" % job.id)

        # XIA2 small molecule
        xia2chem_dir = dc_pars['xia2chem_dir']
        logging.getLogger('user_level_log').info("Trigger XIA2 small molecule processing")
        job = self.cluster.create_xia2_job(dc_id, self.xia2chem_input_file, xia2chem_dir)
        self.cluster.run(job)
        self.logger.debug("XIA2 input file = %s " % self.xia2chem_input_file)
        self.logger.debug("Output dir = %s " % xia2chem_dir)
        logging.getLogger('user_level_log').info("XIA2 job ID: %s" % job.id)

    def set_sample_type(self, is_small_molecule):
        is_small_bool = True
        if is_small_molecule == 0: is_small_bool = False

        logging.getLogger('user_level_log').info("Setting sample is small molecule to %s" % is_small_bool)
        self.sample_is_small_molecule = is_small_bool

def test_hwo(hwo):
    pass
