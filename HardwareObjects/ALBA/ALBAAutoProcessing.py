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

import os
import math
import logging

from ALBAClusterJob import ALBAEdnaProcJob
from HardwareRepository.BaseHardwareObjects import HardwareObject
from XSDataCommon import XSDataFile, XSDataString, XSDataInteger
from XSDataAutoprocv1_0 import XSDataAutoprocInput

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"


class ALBAAutoProcessing(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.template_dir = None
        self.detsamdis_hwobj = None
        self.chan_beamx = None
        self.chan_beamy = None
        self.input_file = None

    def init(self):
        self.template_dir = self.getProperty("template_dir")
        logging.getLogger("HWR").debug("Autoprocessing template_dir = %s" %
                                       self.template_dir)
        self.detsamdis_hwobj = self.getObjectByRole("detector_distance")
        self.chan_beamx = self.getChannelObject('beamx')
        self.chan_beamy = self.getChannelObject('beamy')

    def create_input_files(self, dc_pars):

        xds_dir = dc_pars['xds_dir']
        mosflm_dir = dc_pars['auto_dir']

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
        detsamdis = self.detsamdis_hwobj.get_position()
        beamx, beamy = self.chan_beamx.getValue(), self.chan_beamy.getValue()

        mbeamx, mbeamy = beamy * 0.172, beamx * 0.172

        data_range_start_num = start_img_num
        data_range_finish_num = start_img_num + nb_images - 1
        background_range_start_num = start_img_num
        spot_range_start_num = start_img_num

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
        test_high_res = round(wavelength / (2 * math.sin(0.5 * math.atan(largest_vector /
                                                                         detsamdis))), 2)
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
        output_dir = dc_pars['ednaproc_dir']

        ednaproc_input_file = os.path.join(output_dir, "EDNAprocInput_%d.xml" %
                                           collection_id)
        ednaproc_input = XSDataAutoprocInput()

        input_file = XSDataFile()
        path = XSDataString()
        path.setValue(xds_file)
        input_file.setPath(path)

        ednaproc_input.setInput_file(input_file)
        ednaproc_input.setData_collection_id(XSDataInteger(collection_id))

        ednaproc_input.exportToFile(ednaproc_input_file)
        self.input_file = ednaproc_input_file

    def trigger_auto_processing(self, dc_pars):
        logging.getLogger("HWR").debug("Triggering auto processing.")

        dc_id = dc_pars['collection_id']
        output_dir = dc_pars['ednaproc_dir']

        logging.getLogger("HWR").debug("    - collection_id = %s " % dc_id)
        logging.getLogger("HWR").debug("    - output_dir    = %s " % output_dir)

        job = ALBAEdnaProcJob()

        input_file = self.input_file  # TODO
        logging.getLogger("HWR").debug("    - input file    = %s " % input_file)

        job.run(dc_id, input_file, output_dir)


def test_hwo(hwo):
    pass
