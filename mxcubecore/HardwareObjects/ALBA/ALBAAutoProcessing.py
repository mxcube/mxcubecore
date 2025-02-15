import logging
import math
import os
import sys
from datetime import datetime

from ALBAClusterJob import ALBAEdnaProcJob
from PyTango import DeviceProxy
from xaloc import XalocJob
from XSDataAutoprocv1_0 import XSDataAutoprocInput
from XSDataCommon import (
    XSDataFile,
    XSDataInteger,
    XSDataString,
)

from mxcubecore.BaseHardwareObjects import HardwareObject

sys.path.append("/beamlines/bl13/controls/devel/pycharm/ALBAClusterClient")


root = os.environ["POST_PROCESSING_SCRIPTS_ROOT"]
sls_script = os.path.join(root, "gphl/autoproc/autoproc.process.sl")


class ALBAAutoProcessing(HardwareObject):
    def init(self):
        HardwareObject.init(self)

        self.template_dir = self.get_property("template_dir")
        var_dsname = self.get_property("variables_ds")
        logging.getLogger("HWR").debug(
            "ALBAAutoProcessing INIT: var_ds=%s, template_dir=%s"
            % (var_dsname, self.template_dir)
        )
        self.var_ds = DeviceProxy(var_dsname)

    # input files for standard collection auto processing
    def create_input_files(self, xds_dir, mosflm_dir, dc_pars):
        fileinfo = dc_pars["fileinfo"]
        osc_seq = dc_pars["oscillation_sequence"][0]

        prefix = fileinfo["prefix"]
        runno = fileinfo["run_number"]

        exp_time = osc_seq["exposure_time"]

        start_angle = osc_seq["start"]
        nb_images = osc_seq["number_of_images"]
        start_img_num = osc_seq["start_image_number"]
        angle_increment = osc_seq["range"]

        wavelength = osc_seq.get("wavelength", 0)

        xds_template_name = "XDS_TEMPLATE.INP"
        mosflm_template_name = "mosflm_template.dat"

        xds_template_path = os.path.join(self.template_dir, xds_template_name)
        mosflm_template_path = os.path.join(self.template_dir, mosflm_template_name)

        xds_file = os.path.join(xds_dir, "XDS.INP")
        mosflm_file = os.path.join(mosflm_dir, "mosflm.dat")

        t = datetime.now()

        # PREPARE VARIABLES
        detsamdis = self.var_ds.detsamdis
        beamx, beamy = self.var_ds.beamx, self.var_ds.beamy

        mbeamx, mbeamy = beamy * 0.172, beamx * 0.172

        datarangestartnum = start_img_num
        datarangefinishnum = start_img_num + nb_images - 1
        backgroundrangestartnum = start_img_num
        spotrangestartnum = start_img_num
        if angle_increment != 0:
            minimumrange = int(round(20 / angle_increment))
        elif angle_increment == 0:
            minimumrange = 1
        if nb_images >= minimumrange:
            backgroundrangefinishnum = start_img_num + minimumrange - 1
        if nb_images >= minimumrange:
            spotrangefinishnum = start_img_num + minimumrange - 1
        if nb_images < minimumrange:
            backgroundrangefinishnum = start_img_num + nb_images - 1
        if nb_images < minimumrange:
            spotrangefinishnum = start_img_num + nb_images - 1

        testlowres = 8.0
        largestvector = (
            0.172
            * ((max(beamx, 2463 - beamx)) ** 2 + (max(beamy, 2527 - beamy)) ** 2) ** 0.5
        )
        testhighres = round(
            wavelength / (2 * math.sin(0.5 * math.atan(largestvector / detsamdis))), 2
        )
        lowres = 50.0
        highres = testhighres
        datafilename = prefix + "_" + str(runno) + "_????"
        mdatafilename = prefix + "_" + str(runno) + "_####.cbf"
        seconds = 5 * exp_time

        if angle_increment < 1 and not angle_increment == 0:
            seconds = 5 * exp_time / angle_increment

        # DEFINE SG/UNIT CELL
        spacegroupnumber = ""
        unitcellconstants = ""

        datapath_dir = os.path.abspath(xds_file).replace("PROCESS_DATA", "RAW_DATA")
        datapath_dir = os.path.dirname(os.path.dirname(datapath_dir)) + os.path.sep

        # CREATE XDS.INP FILE
        xds_templ = open(xds_template_path, "r").read()

        xds_templ = xds_templ.replace("###BEAMX###", str(round(beamx, 2)))
        xds_templ = xds_templ.replace("###BEAMY###", str(round(beamy, 2)))
        xds_templ = xds_templ.replace("###DETSAMDIS###", str(round(detsamdis, 2)))
        xds_templ = xds_templ.replace("###ANGLEINCREMENT###", str(angle_increment))
        xds_templ = xds_templ.replace("###WAVELENGTH###", str(wavelength))
        xds_templ = xds_templ.replace("###DATARANGESTARTNUM###", str(datarangestartnum))
        xds_templ = xds_templ.replace(
            "###DATARANGEFINISHNUM###", str(datarangefinishnum)
        )
        xds_templ = xds_templ.replace(
            "###BACKGROUNDRANGESTART###", str(backgroundrangestartnum)
        )
        xds_templ = xds_templ.replace(
            "###BACKGROUNDRANGEFINISHNUM###", str(backgroundrangefinishnum)
        )
        xds_templ = xds_templ.replace("###SPOTRANGESTARTNUM###", str(spotrangestartnum))
        xds_templ = xds_templ.replace(
            "###SPOTRANGEFINISHNUM###", str(spotrangefinishnum)
        )
        xds_templ = xds_templ.replace("###TESTLOWRES###", str(testlowres))
        xds_templ = xds_templ.replace("###TESTHIGHRES###", str(testhighres))
        xds_templ = xds_templ.replace("###LOWRES###", str(lowres))
        xds_templ = xds_templ.replace("###HIGHRES###", str(highres))
        xds_templ = xds_templ.replace("###DIRECTORY###", str(datapath_dir))
        xds_templ = xds_templ.replace("###FILENAME###", str(datafilename))
        xds_templ = xds_templ.replace("###SECONDS###", str(int(seconds)))
        xds_templ = xds_templ.replace(
            "###LYSOZYME_SPACE_GROUP_NUMBER###", str(spacegroupnumber)
        )
        xds_templ = xds_templ.replace(
            "###LYSOZYME_UNIT_CELL_CONSTANTS###", str(unitcellconstants)
        )

        open(xds_file, "w").write(xds_templ)

        # CREATE MOSFLM.DAT FILE

        mosflm_templ = open(mosflm_template_path, "r").read()

        mosflm_templ = mosflm_templ.replace("###DETSAMDIS###", str(round(detsamdis, 2)))
        mosflm_templ = mosflm_templ.replace("###BEAMX###", str(round(mbeamx, 2)))
        mosflm_templ = mosflm_templ.replace("###BEAMY###", str(round(mbeamy, 2)))
        mosflm_templ = mosflm_templ.replace("###DIRECTORY###", str(datapath_dir))
        mosflm_templ = mosflm_templ.replace("###FILENAME###", str(mdatafilename))
        mosflm_templ = mosflm_templ.replace("###WAVELENGTH###", str(wavelength))
        mosflm_templ = mosflm_templ.replace(
            "###DATARANGESTARTNUM###", str(datarangestartnum)
        )

        open(mosflm_file, "w").write(mosflm_templ)

        # CREATE EDNAPROC XML FILE
        collection_id = dc_pars["collection_id"]
        output_dir = dc_pars["ednaproc_dir"]

        ednaproc_input_file = os.path.join(
            output_dir, "EDNAprocInput_%d.xml" % collection_id
        )

        ednaproc_input = XSDataAutoprocInput()

        input_file = XSDataFile()
        path = XSDataString()
        path.set_value(xds_file)
        input_file.setPath(path)

        ednaproc_input.setInput_file(input_file)
        ednaproc_input.setData_collection_id(XSDataInteger(collection_id))

        # output_dir = XSDataFile()
        # outpath = XSDataString()
        # outpath.set_value(output_dir)
        # output_dir.setPath(path)

        # ednaproc_input.setOutput_directory( output_dir )

        ednaproc_input.exportToFile(ednaproc_input_file)

        self.input_file = ednaproc_input_file

    # trigger auto processing for standard collection
    def trigger_auto_processing(self, dc_pars):
        logging.getLogger("HWR").debug(
            " ALBAAutoProcessing. triggering auto processing."
        )

        dc_id = dc_pars["collection_id"]
        output_dir = dc_pars["ednaproc_dir"]

        logging.getLogger("HWR").debug("    - collection_id = %s " % dc_id)
        logging.getLogger("HWR").debug("    - output_dir    = %s " % output_dir)

        job = ALBAEdnaProcJob()
        input_file = self.input_file  # TODO

        job.run(dc_id, input_file, output_dir)


def test_hwo(hwo):
    ofile = "/tmp/edna/edna_result"
    odir = "/tmp/edna"
    test_input_file = "/beamlines/bl13/projects/cycle2018-I/2018012551-bcalisto/mx2018012551/DATA/20180131/PROCESS_DATA/characterisation_ref-Thrombin-TB-TTI1_A_run1_1/EDNAInput_2004391.xml"
    result = hwo.run_edna(test_input_file, ofile, odir)
    print(result)
