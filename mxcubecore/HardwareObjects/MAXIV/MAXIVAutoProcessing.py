#
#  Project: MXCuBE
#  https://github.com/mxcube
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
MAXIVAutoProcessing
"""

import os
import time
import logging
import gevent
import errno
import subprocess
import json
from textwrap import dedent

from XSDataAutoprocv1_0 import XSDataAutoprocInput
from mxcubecore.BaseHardwareObjects import HardwareObject


class MAXIVAutoProcessing(HardwareObject):
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
        self.generate_xds_inp_user_path = None # generate XDS.INP for user
        self.generate_xds_inp_proc_path = None # generate XDS.INP for processing pipelines
        self.gen_autoproc_path = None

    def init(self):
        """
        Descript. :
        """
        self.autoproc_programs = self["programs"]
        self.generate_xds_inp_user_path = self.get_property("generate_xds_inp_user_path", self.generate_xds_inp_user_path)
        self.generate_xds_inp_proc_path = self.get_property("generate_xds_inp_proc_path", self.generate_xds_inp_proc_path)
        self.gen_autoproc_path = self.get_property("generate_autoproc_path", self.gen_autoproc_path)
        self.log = logging.getLogger("HWR")
        self.host = "clu0-fe-0"
        self.gen_thumbnail_script = self.get_property(
            "gen_thumbnail_script",
            "/mxn/groups/sw/mxsw/mxcube_scripts/generate_thumbnail"
            )

    def execute_autoprocessing(self, process_event, params_dict, frame_number):
        """
        Descript. :
        """
        auto_dir = params_dict["auto_dir"]
        xds_dir = params_dict["xds_dir"]
        data_path  = params_dict['fileinfo']['filename']
        sample_info = params_dict.get("sample_reference")

        cmd = "cd %s\n" % xds_dir
        if self.generate_xds_inp_user_path is None:
            logging.getLogger("HWR").warning("[AutoProcessing] the script generate_xds_inp for user is missing!!")
        else:
            cmd += "%s %s\n" % (self.generate_xds_inp_user_path, data_path)
            cmd += "chmod 660 XDS.INP\n"
        if self.generate_xds_inp_proc_path is None:
            logging.getLogger("HWR").error("[AutoProcessing] the script generate_xds_inp for autoprocessing is missing!!")
            raise Exception("[AutoProcessing] the script generate_xds_inp for autoprocessing is missing!!")
        cmd += "cd %s\n" % auto_dir
        cmd += "%s %s\n" % (self.generate_xds_inp_proc_path, data_path)

        if process_event == "after":

            path = params_dict["auto_dir"]
            mode = 'after'
            dataCollectionId =  str(params_dict['collection_id'])
            numImages = params_dict['oscillation_sequence'][0]['number_of_images']
            startImageNum = params_dict['oscillation_sequence'][0]['start_image_number']
            residues = 200
            anomalous = False
            cell = sample_info.get('cell', "0,0,0,0,0,0")
            #some processing software don't work if only the angles are provided
            if cell == ",,,,," or cell[0:5]=="0,0,0":
                 cell = "0,0,0,0,0,0"
            space_group = sample_info.get('spacegroup', 0)

            #Undefined and None can be from ISPyB
            if space_group is None or space_group =="" or space_group=="None" or space_group=="Undefined" or space_group=="Notset":
                space_group = 0
            else:
                # remove spaces from user input if there's any
                space_group = str(space_group).replace(" ","")

            edna2Setup = "/mxn/groups/sw/mxsw/env_setup/edna2_proc_micromax.sh"

            pyDozorJson = {
                "dataCollectionId": int(dataCollectionId),
                "workingDirectory":auto_dir,
                "masterFile": data_path,
                "startNo": startImageNum,
                "batchSize": numImages,
                "doISPyBUpload": True,
                "doSubmit": True,
                "returnSpotList": False,
            }
            inDataPyDozorFilePath = os.path.join(auto_dir,"inDataPyDozor.json")
            with open(inDataPyDozorFilePath,"w+") as fp:
                json.dump(pyDozorJson,fp,indent=4)

            slurmStrDozor = """\
            sbatch <<-EOF
            \t#!/bin/bash
            \t#SBATCH --exclusive
            \t#SBATCH --partition=bio-sf
            \t#SBATCH --mem=0
            \t#SBATCH -t 00:10:00
            \t#SBATCH -J "EDNA2"
            \t#SBATCH --output EDNA2Dozor_%j.out
            \t#SBATCH --chdir {a}
            \tsource {b}
            \trun_edna2.py --inDataFile {a}/inDataPyDozor.json ControlPyDozor
            \tEOF
            """.format(a=auto_dir, b=edna2Setup)
            slurmStrDozor = dedent(slurmStrDozor)

            cmd += slurmStrDozor + '\n'


            autoPROCJson = {
                "dataCollectionId":int(dataCollectionId),
                "masterFilePath":data_path,
                "workingDirectory":auto_dir,
                "anomalous":anomalous,
                "spaceGroup":space_group,
                "unitCell":cell,
                "onlineAutoProcessing":True,
                "waitForFiles":True,
                "doUploadIspyb":True,
                "test":False
            }
            inDataJsonFilePath = os.path.join(auto_dir,"inDataMAXIVAutoProcessing.json")
            with open(inDataJsonFilePath,"w+") as fp:
                json.dump(autoPROCJson,fp,indent=4)
                        
            
            slurmStr = """\
            sbatch <<-EOF
            \t#!/bin/bash
            \t#SBATCH --exclusive
            \t#SBATCH --partition=all,fujitsu
            \t#SBATCH --mem=0
            \t#SBATCH -t 02:00:00
            \t#SBATCH -J "EDNA2"
            \t#SBATCH --output MAXIVAutoProcessing_%j.out
            \t#SBATCH --chdir {a}
            \tsource {b}
            \trun_edna2.py --inDataFile {a}/inDataMAXIVAutoProcessing.json MAXIVFastProcessingTask
            \tEOF
            """.format(a=auto_dir, b=edna2Setup)
            slurmStr = dedent(slurmStr)

            cmd += slurmStr
            
        script_dir = os.path.join(auto_dir, "autoproc_gen.sh")
        with open(script_dir,"w+") as script:
            script.write(cmd)
        os.system("ssh {} sh {}&".format(self.host, script_dir))

    def start_dataset_repacking(self, dc_params, bl_config):
        '''
        Trigger the dataset repacking script for interleaved
        '''
        script = "python /mxn/groups/biomax/wmxsoft/scripts_mxcube/Repack.py"
        dir = dc_params["fileinfo"]["directory"]
        self.log.info("Spawning interleaved dataset repacking in directory {}".format(dir))
        self.bl_config = bl_config
        cmd = "echo 'source /mxn/groups/sw/mxsw/env_setup/h5handler_env.sh; {} -d {}' | ssh {}".format(script, dir, self.host)
        self.log.info("The cmd going to run is {}".format(cmd))
        os.system(cmd)

        self.log.info("Spawning dataset repacking waiting ")
        gevent.spawn(self.wait_for_dataset_repacking, dc_params)

    def master_files_on_disk(self, dc_params):
        """
        Return the new expected master filenames after the repacking operation
        """
        dir = dc_params["fileinfo"]["directory"]
        prefix = dc_params["fileinfo"]["prefix"]
        # remove _wedge-x from the prefix
        prefix = prefix.split('_wedge')[0]
        self.master_files = []
        inc_nr = 1
        # removing duplicates
        self.interleaved_energies = list(dict.fromkeys(self.interleaved_energies))

        for energy in self.interleaved_energies:
            self.master_files.append(os.path.join(dir, "repack-{}-{}-{}_master.h5".format(prefix, inc_nr, int(energy*1000))))
            inc_nr += 1

        return self.master_files

    def prepare_xds_filenames(self, dc_params):
        """
        Create XDS adn AUTO directories
        """
        i = 1

        while True:
            xds_input_file_dirname = "xds_%s_%s_%d" % (\
                dc_params['fileinfo']['prefix'],
                dc_params['fileinfo']['run_number'],
                i)
            xds_directory = os.path.join(\
                dc_params['fileinfo']['directory'],
                "process", xds_input_file_dirname)
            if not os.path.exists(xds_directory):
                break
            i += 1

        auto_directory = os.path.join(
            dc_params['fileinfo']['process_directory'],
            xds_input_file_dirname)

        self.log.info("[COLLECT] Processing input file directories: XDS: %s, AUTO: %s" % (xds_directory, auto_directory))
        try:
            for directory in [xds_directory, auto_directory]:
                try:
                    os.makedirs(directory)
                except os.error as e:
                    if e.errno != errno.EEXIST:
                        raise
            # temporary, to improve
            os.system("chmod -R 770 %s %s" % (os.path.dirname(xds_directory), auto_directory))
        except Exception:
            logging.exception("Could not create processing file directory")
            return

        return xds_directory, auto_directory

    def repack_collection_dictionaries(self):
        """
        Recreate new datacollection parameters dir for the new repacked files
        Send info to ispyb which will create a new entry
        Triger autoprocessing
        """
        collections = {}
        for energy in self.interleaved_energies:
            collections[energy] = []

        for col in self.collection_dictionaries:
            collections[col.get('energy')].append(col)
        # so we now have the wedges split by their energy

        index = 0
        for energy in self.interleaved_energies:
            my_cols = collections[energy]
            num_images = 0
            for col in my_cols:
                num_images += col['oscillation_sequence'][0].get('number_of_images')
            # TODO: change and create xds directories
            _col = my_cols[0]
            _col['oscillation_sequence'][0]['number_of_images'] = num_images
            filename = self.master_files[index]
            _col['fileinfo']['filename'] = filename
            _col['fileinfo']['prefix'] = filename.split('/')[-1].split('_master.h5')[0]
            _col['fileinfo']['template'] = _col['fileinfo']['prefix'] + '_%06d.h5'

            index += 1
            _col.pop('group_id', None)
            _col.pop('collection_id', None)

            xds_directory, auto_directory = self.prepare_xds_filenames(_col)

            if xds_directory:
                _col["xds_dir"] = xds_directory
            if auto_directory:
                _col["auto_dir"] = auto_directory

            if self.lims_client_hwobj:
                try:
                    self.log.info("Sending to ISPYB repacked info: {}".format(_col))
                    group_id = self.lims_client_hwobj.store_data_collection_group(_col)
                    _col['group_id'] = group_id
                    (collection_id, detector_id) = self.lims_client_hwobj.store_data_collection(_col, self.bl_config)
                    _col['collection_id'] = collection_id
                    self.log.info("Sending to ISPYB repacked info, collection ID: {}".format(collection_id))
                    if detector_id:
                        _col['detector_id'] = detector_id
                except Exception:
                    self.log.exception("Could not store data collection in LIMS")

            gevent.spawn(self.post_collection_store_image, _col)

            # and now send to processing
            self.log.info("[COLLECT] triggering auto processing, dc_parameters: %s" % _col)
            self.execute_autoprocessing("after", _col, 0)
            self.current_dc_parameters = _col

    def wait_for_dataset_repacking(self, dc_params):
        """
        Wait for the repacking operation to finish and the new files are on disk
        """
        master_files = self.master_files_on_disk(dc_params)
        self.log.info("Waiting for repacked files: {}".format(master_files))

        with gevent.Timeout(60, Exception("Timeout waiting for repacked dataset")):
            while not all([os.path.exists(f) for f in master_files]):
                gevent.sleep(1)

        self.repack_collection_dictionaries()

        self.interleaved_energies = []
        self.collection_dictionaries = []

    def correct_omega_in_master_file(self, dc_params):
        """
        Correct omage value in the master file for characterisation
        """
        oscillation_parameters = dc_params["oscillation_sequence"][0]
        overlap = oscillation_parameters['overlap']
        master_filename = dc_params['fileinfo']['filename']
        script = "/mxn/groups/biomax/wmxsoft/scripts_mxcube/omega_correction/correct_omega.py"
        cmd = "echo 'source /mxn/groups/sw/mxsw/env_setup/h5handler_env.sh; python {} -f {} -o {} &' | ssh {} ".format(script, master_filename, - overlap, self.host)
        self.log.info( " the cmd going to run is %s " % cmd)
        os.system(cmd)


    def post_collection_store_image(self, collection=None):
        '''
        Generate and store ijn ispyb thumbnail images
        '''
        # only store the first image
        self.log.info("Storing images in lims, frame number: 1")
        if collection is None:
            collection = self.current_dc_parameters
        try:
            self.store_image_in_lims(1, collection=collection)
            self.generate_and_copy_thumbnails(collection['fileinfo']['filename'], 1)
        except Exception as ex:
            self.log.error("Could not store images in lims, error was {}".format(ex))

    def store_image_in_lims_by_frame_num(self, frame, motor_position_id=None):
        """
        Descript. :
        """
        # Dont save mesh first and last images
        # Mesh images (best positions) are stored after data analysis
        self.log.info("TODO: fix store_image_in_lims_by_frame_num method for nimages>1")
        return

    def generate_and_copy_thumbnails(self, data_path, frame_number):
        if self.gen_thumbnail_script is None:
            self.log.warning("[COLLECT] Generating thumbnail script is not defined, no thumbnails will be created!!")
            return
        #  generare diffraction thumbnails
        image_file_template = self.current_dc_parameters['fileinfo']['template']
        archive_directory = self.current_dc_parameters['fileinfo']['archive_directory']
        thumb_filename = "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
        jpeg_thumbnail_file_template = os.path.join(archive_directory, thumb_filename)
        jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame_number

        self.log.info("[COLLECT] Generating thumbnails, output filename: %s" % jpeg_thumbnail_full_path)
        self.log.info("[COLLECT] Generating thumbnails, data path: %s" % data_path)
        nimages = 1
        cmd = "ssh clu0-fe-0 %s  %s  %d  %s &" \
            % (self.gen_thumbnail_script, data_path, frame_number, jpeg_thumbnail_full_path)
        self.log.info(cmd)
        os.system(cmd)

    def store_image_in_lims(self, frame_number, motor_position_id=None, collection=None):
        """
        Descript. :
        """
        if collection is None:
            collection = self.current_dc_parameters
        if self.lims_client_hwobj:
            file_location = collection["fileinfo"]["directory"]
            image_file_template = collection['fileinfo']['template']
            filename = image_file_template % frame_number
            lims_image = {'dataCollectionId': collection["collection_id"],
                          'fileName': filename,
                          'fileLocation': file_location,
                          'imageNumber': frame_number,
                          'measuredIntensity': collection.get('flux_end', None), # self.get_measured_intensity(),
                          'synchrotronCurrent': '', # self.get_machine_current(),
                          'machineMessage': '', # self.get_machine_message(),
                          'temperature': 0} #self.get_cryo_temperature()}
            archive_directory = collection['fileinfo']['archive_directory']

            if archive_directory:
                jpeg_filename = "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
                thumb_filename = "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
                jpeg_file_template = os.path.join(archive_directory, jpeg_filename)
                jpeg_thumbnail_file_template = os.path.join(archive_directory, thumb_filename)
                jpeg_full_path = jpeg_file_template % frame_number
                jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame_number
                lims_image['jpegFileFullPath'] = jpeg_full_path
                lims_image['jpegThumbnailFileFullPath'] = jpeg_thumbnail_full_path
                lims_image['fileLocation'] = collection["fileinfo"]["directory"]
            if motor_position_id:
                lims_image['motorPositionId'] = motor_position_id
            self.log.info("LIMS IMAGE: %s, %s, %s, %s" %(jpeg_filename, thumb_filename, jpeg_full_path, jpeg_thumbnail_full_path))
            try:
                image_id = self.lims_client_hwobj.store_image(lims_image)
            except Exception as ex:
                self.log.error("Could not store images in lims, error was {}".format(ex))

        # temp fix for ispyb permission issues
            try:
                session_dir = os.path.join(archive_directory,  '../../../')
                os.system("chmod -R 777 %s" % (session_dir))
            except Exception as ex:
                self.log.warning("Could not change permissions on ispyb storage, error was {}".format(ex))

            return image_id


