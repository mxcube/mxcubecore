import os
import glob
import time
import logging
import gevent
import numpy
import subprocess

import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

import SimpleHTML as simpleHtml
import queue_model_enumerables_v1 as qme

from HardwareRepository.BaseHardwareObjects import HardwareObject

from XSDataControlDozorv1_1 import XSDataInputControlDozor
from XSDataControlDozorv1_1 import XSDataResultControlDozor

from XSDataCommon import XSDataBoolean
from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataString


class ParallelProcessing(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
 
        # Hardware objects ----------------------------------------------------
        self.collect_hwobj = None
        self.detector_hwobj = None
        self.beamstop_hwobj = None
        self.lims_hwobj = None 

        # Internal variables --------------------------------------------------
        self.processing_start_command = None
        self.processing_results = None
        self.processing_done_event = None

    def init(self):
        self.processing_done_event = gevent.event.Event()

        self.collect_hwobj = self.getObjectByRole("collect")

        try:
           self.detector_hwobj = self.collect_hwobj.detector_hwobj
           self.lims_hwobj = self.collect_hwobj.lims_client_hwobj
        except:
           try:
              self.detector_hwobj = self.collect_hwobj.bl_config.detector_hwobj
              self.lims_hwobj = self.collect_hwobj.cl_config.lims_client_hwobj
           except:
              pass

        if self.detector_hwobj is None:
            logging.info("ParallelProcessing: No detector hwobj defined")

        self.beamstop_hwobj = self.getObjectByRole("beamstop")
        if self.beamstop_hwobj is None:
            logging.info("ParallelProcessing: No beamstop hwobj defined")

        self.processing_start_command = str(self.getProperty("processing_command"))        

    def create_processing_input(self, data_collection, processing_params, grid_object):
        """
        Descript. : Creates dozor input file base on data collection parameters
        Args.     : data_collection (object)
        Return.   : processing_input_file (object)
        """
        acquisition = data_collection.acquisitions[0]
        acq_params = acquisition.acquisition_parameters

        processing_input_file = XSDataInputControlDozor()
        _run = "_%d_" % acquisition.path_template.run_number
        image_file_template = "%s_%%d_%%05d.cbf" % (
                   acquisition.path_template.get_prefix())

        template = os.path.join(acquisition.path_template.directory,
                                image_file_template)

        first_image_num = acq_params.first_image
        images_num = acq_params.num_images
        last_image_num = first_image_num + images_num - 1 
        run_number = acquisition.path_template.run_number
        lines_num = acq_params.num_lines
        
        pixel_min = 0
        pixel_max = 0
        beamstop_size = 0
        beamstop_distance = 0
        beamstop_direction = 0

        try: 
           pixel_min = self.detector_hwobj.get_pixel_min()
           pixel_max = self.detector_hwobj.get_pixel_max()
        except:
           pass
      
        try:
           beamstop_size = self.beamstop_hwobj.get_beamstop_size()
           beamstop_distance = self.beamstop_hwobj.get_beamstop_distance()
           beamstop_direction = self.beamstop_hwobj.get_beamstop_direction()
        except:
           pass

        grid_params = grid_object.get_properties()
        reversing_rotation = grid_params["reversing_rotation"]

        processing_params["template"] = template
        processing_params["first_image_num"] = first_image_num
        processing_params["images_num"] = images_num
        processing_params["lines_num"] = lines_num
        processing_params["images_per_line"] = images_num / lines_num
        processing_params["run_number"] = run_number
        processing_params["pixel_min"] = pixel_min
        processing_params["pixel_max"] = pixel_max
        processing_params["beamstop_size"] = beamstop_size
        processing_params["beamstop_distance"] = beamstop_distance
        processing_params["beamstop_direction"] = beamstop_direction
        processing_params["status"] = "Started"
        processing_params["title"] = "%s_%d_xxxxx.cbf (%d - %d)" % \
             (acquisition.path_template.get_prefix(),
              acquisition.path_template.run_number,
              first_image_num,
              last_image_num)
        processing_params["comments"] = "Scan lines: %d, frames per line: %d" % \
             (lines_num, images_num / lines_num )

        if lines_num > 1:
            processing_params["dx_mm"] = grid_params["dx_mm"]
            processing_params["dy_mm"] = grid_params["dy_mm"]
            processing_params["steps_x"] = grid_params["steps_x"]
            processing_params["steps_y"] = grid_params["steps_y"]
            processing_params["xOffset"] = grid_params["xOffset"]
            processing_params["yOffset"] = grid_params["yOffset"]

        processing_input_file.setTemplate(XSDataString(template))
        processing_input_file.setFirst_image_number(XSDataInteger(first_image_num))
        processing_input_file.setLast_image_number(XSDataInteger(last_image_num))
        processing_input_file.setFirst_run_number(XSDataInteger(run_number))
        processing_input_file.setLast_run_number(XSDataInteger(run_number))
        processing_input_file.setLine_number_of(XSDataInteger(lines_num))
        processing_input_file.setReversing_rotation(XSDataBoolean(reversing_rotation))
        processing_input_file.setPixelMin(XSDataInteger(pixel_min)) # should be -1 for real data
        processing_input_file.setPixelMax(XSDataInteger(pixel_max))
        processing_input_file.setBeamstopSize(XSDataDouble(beamstop_size))
        processing_input_file.setBeamstopDistance(XSDataDouble(beamstop_distance))
        processing_input_file.setBeamstopDirection(XSDataString(beamstop_direction))

        return processing_input_file, processing_params

    def run_processing(self, data_collection, grid_object):
        """
        Descript. : Main parallel processing method.
                    At first EDNA input file is generated based on acq parameters.
                    If actual execution script is executable then processing
                    is launched via subprocess. Method do_processing_result_polling
                    is called after processing is launched.
        Args.     : data_collection object
        Return    : None
        """
        acquisition = data_collection.acquisitions[0] 
        acq_params = acquisition.acquisition_parameters
        self.processing_results = {}

        prefix = acquisition.path_template.get_prefix()
        run_number = acquisition.path_template.run_number
        process_directory = acquisition.path_template.process_directory
        archive_directory = acquisition.path_template.get_archive_directory()
        file_wait_timeout = (0.003 + acq_params.exp_time) * \
                            acq_params.num_images / acq_params.num_lines + 30

        # Estimates dozor directory. If run number found then creates
        # processing and archive directory         
        i = 1
        while True:
            processing_input_file_dirname = "dozor_%s_run%s_%d" % (prefix, run_number, i)
            processing_directory = os.path.join(process_directory, processing_input_file_dirname)
            processing_archive_directory = os.path.join(archive_directory, processing_input_file_dirname)
            if not os.path.exists(processing_directory):
                break
            i += 1
        if not os.path.isdir(processing_directory):
            os.makedirs(processing_directory)
        if not os.path.isdir(processing_archive_directory):
            os.makedirs(processing_archive_directory) 

        try:
            grid_snapshot_filename = None
            if grid_object is not None:
                grid_snapshot_filename = os.path.join(processing_archive_directory, "grid_snapshot.png")
                logging.getLogger("HWR").info("Saving grid snapshot: %s" % grid_snapshot_filename)
                grid_snapshot = grid_object.get_snapshot()
                grid_snapshot.save(grid_snapshot_filename, 'PNG')
        except:
            logging.getLogger("HWR").exception("Could not save grid snapshot: %s" \
                % grid_snapshot_filename)

        processing_params = {}
        processing_params["directory"] = processing_directory
        processing_params["processing_archive_directory"] = processing_archive_directory
        processing_params["grid_snapshot_filename"] = grid_snapshot_filename
        processing_params["images_num"] = acq_params.num_lines
        processing_params["result_file_path"] = processing_params["processing_archive_directory"]
        processing_params["plot_path"] = os.path.join(\
             processing_params["directory"], "parallel_processing_result.png")
        processing_params["cartography_path"] = os.path.join(\
             processing_params["processing_archive_directory"], "parallel_processing_result.png")  
        processing_params["log_file_path"] = os.path.join(\
             processing_params["processing_archive_directory"], "dozor_log.log")        
        processing_params["group_id"] = data_collection.lims_group_id
        #processing_params["associated_grid"] = associated_grid
        #processing_params["associated_data_collection"] = data_collection
        processing_params["processing_start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")


        processing_input, processing_params = self.create_processing_input(\
             data_collection, processing_params, grid_object) 
        processing_input_file = os.path.join(processing_directory, "dozor_input.xml")
        processing_input.exportToFile(processing_input_file)

        if not os.path.isfile(self.processing_start_command):
            self.processing_done_event.set()
            msg = "ParallelProcessing: Start command %s is not executable" % self.processing_start_command
            logging.getLogger("queue_exec").error(msg)
            self.emit("processingFailed")
            return       
        else:
            msg = "ParallelProcessing: Starting processing using xml file %s" % processing_input_file
            logging.getLogger("queue_exec").info(msg)
            line_to_execute = self.processing_start_command + ' ' + \
                              processing_input_file + ' ' + \
                              processing_directory
        subprocess.Popen(str(line_to_execute), shell = True,
                         stdin = None, stdout = None, stderr = None,
                         close_fds = True)

        self.do_processing_result_polling(processing_params, file_wait_timeout, grid_object)
        
    def do_processing_result_polling(self, processing_params, wait_timeout, grid_object):
        """Method polls processing results. Based on the polling of edna 
           result files. After each result file results are aligned to match 
           the diffractometer configuration.
           If processing succed (files appear before timeout) then a heat map 
           is created and results are stored in ispyb.
           If processing was executed for helical line then heat map as a 
           line plot is generated and best positions are estimated.
           If processing was executed for a grid then 2d plot is generated,
           best positions are estimated and stored in ispyb. Also mesh
           parameters and processing results as a workflow are stored in ispyb.
        Args.     : wait_timeout (file waiting timeout is sec.)
        Return.   : list of 10 best positions. If processing fails returns None 
        """
        processing_result = {"image_num" : numpy.zeros(processing_params["images_num"]),
                        "spots_num" : numpy.zeros(processing_params["images_num"]),
                        "spots_int_aver" : numpy.zeros(processing_params["images_num"]),
                        "spots_resolution" : numpy.zeros(processing_params["images_num"]),
                        "score" : numpy.zeros(processing_params["images_num"])}

        processing_params["status"] = "Success"
        failed = False

        do_polling = True
        result_file_index = 0
        _result_place = []
        _first_frame_timout = 5 * 60 / 10
        _time_out = _first_frame_timout
        _start_time = time.time()
       
        while _result_place == [] and time.time() - _start_time < _time_out :
           _result_place = glob.glob(os.path.join(processing_params["directory"],"EDApplication*/"))
           gevent.sleep(0.2)
        if _result_place == [] : 
           msg = "ParallelProcessing: Failed to read dozor result directory %s" % processing_params["directory"]
           logging.error(msg)
           processing_params["status"] = "Failed"
           processing_params["comments"] += "Failed: " + msg
           self.emit("processingFailed")
           self.processing_done_event.set()
           failed = True

        while do_polling and not failed:
            file_appeared = False
            result_file_name = os.path.join(_result_place[0],"ResultControlDozor_Chunk_%06d.xml" % result_file_index)
            wait_file_start = time.time()
            logging.debug('ParallelProcessing: Waiting for Dozor result file: %s' % result_file_name)
            while not file_appeared and time.time() - wait_file_start < wait_timeout:
                if os.path.exists(result_file_name) and os.stat(result_file_name).st_size > 0:
                    file_appeared = True
                    _time_out = wait_timeout
                    logging.debug('ParallelProcessing: Dozor file is there, size={0}'.format(os.stat(result_file_name).st_size))
                else:
                    os.system("ls %s > /dev/null" %_result_place[0])
                    gevent.sleep(0.2)
            if not file_appeared:
                failed = True
                msg = 'ParallelProcessing: Dozor result file ({0}) failed to appear after {1} seconds'.\
                      format(result_file_name, wait_timeout)
                logging.error(msg)
                processing_params["status"] = "Failed"
                processing_params["comments"] += "Failed: " + msg
                self.emit("processingFailed")
                
            # poll while the size increasing:
            _oldsize = -1 
            _newsize =  0
            while _oldsize < _newsize :
                _oldsize = _newsize
                _newsize = os.stat(result_file_name).st_size
                gevent.sleep(0.1)
                                
            dozor_output_file = XSDataResultControlDozor.parseFile(result_file_name)
            #this method could be improved with xml parsing
            for dozor_image in dozor_output_file.getImageDozor():
                image_index = dozor_image.getNumber().getValue() - 1
                processing_result["image_num"][image_index] = image_index
                processing_result["spots_num"][image_index] = dozor_image.getSpots_num_of().getValue()
                processing_result["spots_int_aver"][image_index] = dozor_image.getSpots_int_aver().getValue()   
                processing_result["spots_resolution"][image_index] = dozor_image.getSpots_resolution().getValue()
                processing_result["score"][image_index] = dozor_image.getScore().getValue()
                image_index += 1
                do_polling = (dozor_image.getNumber().getValue() != processing_params["images_num"])

            aligned_result = self.align_processing_results(\
                processing_result, processing_params, grid_object)
            self.emit("processingSetResult", (aligned_result, processing_params, False))
            result_file_index += 1
        """

        gevent.sleep(10)
        #This is for test...

        for key in processing_result.keys():
            processing_result[key] = numpy.linspace(0, 
                 processing_params["images_num"], 
                 processing_params["images_num"]).astype('uint8')
        """

        self.processing_results = self.align_processing_results(\
             processing_result, processing_params, grid_object)

        self.emit("paralleProcessingResults", (self.processing_results, processing_params, True)) 

        #Processing finished. Results are aligned and 10 best positions estimated
        processing_params["processing_programs"] = "EDNAdozor"
        processing_params["processing_end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        best_positions = self.processing_results.get("best_positions", []) 
 
        #If lims used then and mesh then save results in ispyb
        #Autoprocessin program

        if processing_params["lines_num"] > 1:
            logging.getLogger("HWR").info("ParallelProcessing: Saving autoprocessing program in ISPyB")
            autoproc_program_id = self.lims_hwobj.store_autoproc_program(processing_params)             

            logging.getLogger("HWR").info("ParallelProcessing: Saving processing results in ISPyB")
            workflow_id, workflow_mesh_id, grid_info_id = \
                 self.lims_hwobj.store_workflow(processing_params)
            processing_params["workflow_id"] = workflow_id
            processing_params["workflow_mesh_id"] = workflow_mesh_id
            processing_params["grid_info_id"] = grid_info_id

            self.collect_hwobj.update_lims_with_workflow(workflow_id, 
                 processing_params["grid_snapshot_filename"])

            #If best positions detected then save them in ispyb 
            if len(best_positions) > 0:
                logging.getLogger("HWR").info("ParallelProcessing: Saving %d best positions in ISPyB" % \
                       len(best_positions))

                motor_pos_id_list = []
                image_id_list = []
                for image in best_positions:
                    # Motor position is stored
                    motor_pos_id = self.lims_hwobj.store_centred_position(\
                           image["cpos"], image['col'], image['row'])     
                    # Corresponding image is stored
                    image_id = self.collect_hwobj.store_image_in_lims_by_frame_num(\
                         image['index'], motor_pos_id)
                    # Image quality indicators are stored 
                    image["image_id"] = image_id  
                    image["auto_proc_program"] = autoproc_program_id 
                    
                    self.lims_hwobj.store_image_quality_indicators(image)  
                    
                    motor_pos_id_list.append(motor_pos_id)
                    image_id_list.append(image_id)
               
                processing_params["best_position_id"] = motor_pos_id_list[0]
                processing_params["best_image_id"] = image_id_list[0] 

                logging.getLogger("HWR").info("ParallelProcessing: Updating best position in ISPyB")
                self.lims_hwobj.store_workflow(processing_params)
            else:
                logging.getLogger("HWR").info("ParallelProcessing: No best positions found during the scan")

            try:
                html_filename = os.path.join(processing_params["result_file_path"], "index.html")
                logging.getLogger("HWR").info("ParallelProcessing: Generating results html %s" % html_filename)
                simpleHtml.generate_mesh_scan_report(self.processing_results, processing_params, html_filename)
            except:
                logging.getLogger("HWR").exception("ParallelProcessing: Could not create result html %s" % html_filename)

        # Heat map generation
        fig, ax = plt.subplots(nrows=1, ncols=1 )
        if processing_params["lines_num"] > 1: 
            #If mesh scan then a 2D plot
            im = ax.imshow(self.processing_results["score"], 
                           interpolation = 'none', aspect='auto',
                           extent = [0, self.processing_results["score"].shape[1], 0, 
                                     self.processing_results["score"].shape[0]])
            if len(best_positions) > 0:
                plt.axvline(x = best_positions[0]["col"] - 0.5, linewidth=0.5)
                plt.axhline(y = best_positions[0]["row"] - 0.5, linewidth=0.5)

            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size=0.1, pad=0.05)
            cax.tick_params(axis='x', labelsize=8)
            cax.tick_params(axis='y', labelsize=8)
            plt.colorbar(im, cax=cax)
            im.set_cmap('hot')
        else:
            #if helical line then a line plot
            plt.plot(self.processing_results["score"])
            ylim = ax.get_ylim()
            ax.set_ylim((-1, ylim[1]))

        ax.tick_params(axis='x', labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        ax.set_title(processing_params["title"], fontsize=8)

        ax.grid(True)
        ax.spines['left'].set_position(('outward', 10))
        ax.spines['bottom'].set_position(('outward', 10))

        processing_plot_file = os.path.join(processing_params\
             ["directory"], "parallel_processing_result.png")
        processing_plot_archive_file = os.path.join(processing_params\
             ["processing_archive_directory"], "parallel_processing_result.png")

        try:
            logging.getLogger("HWR").info("ParallelProcessing: Saving heat map figure %s" % processing_plot_file)
            if not os.path.exists(os.path.dirname(processing_plot_file)):
                os.makedirs(os.path.dirname(processing_plot_file))
            fig.savefig(processing_plot_file, dpi = 150, bbox_inches = 'tight')
        except:
            logging.getLogger("HWR").exception("ParallelProcessing: Could not save figure %s" % processing_plot_file)
        try:
            logging.getLogger("HWR").info("ParallelProcessing: Saving heat map figure for ISPyB %s" % processing_plot_archive_file)
            if not os.path.exists(os.path.dirname(processing_plot_archive_file)):
                os.makedirs(os.path.dirname(processing_plot_archive_file))
            fig.savefig(processing_plot_archive_file, dpi = 150, bbox_inches = 'tight')
        except:
            logging.getLogger("HWR").exception("ParallelProcessing: Could not save figure for ISPyB %s" % processing_plot_archive_file) 
        plt.close(fig)
        self.processing_done_event.set()

    def is_running(self):
        return not self.processing_done_event.is_set()

    def align_processing_results(self, results_dict, processing_params, grid_object):
        """
        Descript. : Realigns all results. Each results (one dimensional numpy array)
                    is converted to 2d numpy array according to diffractometer
                    geometry.
                    Function also extracts 10 (if they exist) best positions  
        Args.     : resuld_dict contains 5 one dimensional numpy arrays
        Return    : Dictionary with realigned results and best positions         
        """
        #Each result array is realigned
        aligned_results = {}
        for result_array_key in results_dict.iterkeys():
            aligned_results[result_array_key] = self.align_result_array(\
              results_dict[result_array_key], processing_params, grid_object)
        if processing_params['lines_num'] > 1:
            grid_object.set_score(results_dict['score'])       

        #Best positions are extracted
        best_positions_list = []
        index_arr = (-results_dict["score"]).argsort()[:10]
        if len(index_arr) > 0:
           for index in index_arr:
               if results_dict["score"][index] > 0:
                   best_position = {}
                   best_position["index"] = index
                   best_position["index_serial"] = processing_params["first_image_num"] + index
                   best_position["score"] = float(results_dict["score"][index])
                   best_position["spots_num"] = int(results_dict["spots_num"][index])
                   best_position["spots_int_aver"] = float(results_dict["spots_int_aver"][index])
                   best_position["spots_resolution"] = float(results_dict["spots_resolution"][index])
                   best_position["filename"] = os.path.basename(processing_params["template"] % \
                        (processing_params["run_number"], processing_params["first_image_num"] + index))

                   cpos = None
                   if processing_params["lines_num"] > 1: 
                       col, row = grid_object.get_col_row_from_image_serial(\
                            index + processing_params["first_image_num"])  
                       cpos = grid_object.get_motor_pos_from_col_row(\
                            col, row, as_cpos = True)
                       #entred_position = processing_params["associated_grid"].get_motor_pos_from_col_row(col, row)
                   else:
                       col = index
                       row = 0
                       #cpos = processing_params["associated_data_collection"].get_motor_pos(index, as_cpos=True)
                       cpos = None
                       #TODO Add best position for helical line
                   best_position["col"] = col + 1
                   best_position["row"] = processing_params["steps_y"] - row
                   best_position['cpos'] = cpos
                   best_positions_list.append(best_position) 
        aligned_results["best_positions"] = best_positions_list
        return aligned_results

    def align_result_array(self, result_array, processing_params, grid_object):
        """
        Descript. : realigns result array based on the grid
                    Result array is numpy 2d array
        """
        num_lines = processing_params["lines_num"]
        if num_lines == 1:
            return result_array

        num_images_per_line = processing_params["images_per_line"]
        num_colls = processing_params["steps_x"]
        num_rows = processing_params["steps_y"]
        first_image_number = processing_params["first_image_num"]

        aligned_result_array = numpy.zeros(num_lines * num_images_per_line).\
                        reshape(num_colls, num_rows)        

        for cell_index in range(aligned_result_array.size):
           
            col, row = grid_object.get_col_row_from_image_serial(\
                cell_index + first_image_number)
            if (col < aligned_result_array.shape[0] and 
                row < aligned_result_array.shape[1]):
                aligned_result_array[col][row] = result_array[cell_index]
        return numpy.transpose(aligned_result_array)

    def get_last_processing_results(self):
        return self.processing_results 
