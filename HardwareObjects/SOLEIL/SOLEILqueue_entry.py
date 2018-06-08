from queue_entry import *


class PX2DataCollectionQueueEntry(DataCollectionQueueEntry):
    """
    Defines the behaviour of a data collection.
    """
    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        DataCollectionQueueEntry.__init__(self, view, data_model, view_set_queue_entry)
        
        self.collect_hwobj = None
        self.diffractometer_hwobj = None
        self.collect_task = None
        self.centring_task = None
        self.shape_history = None
        self.session = None
        self.lims_client_hwobj = None
        
    def collect_dc(self, dc, list_item):
        log = logging.getLogger("user_level_log")
        
        log.info("queue_entry. Start data collection on object %s" % str(self.collect_hwobj))
        
        if self.collect_hwobj:
            acq_1 = dc.acquisitions[0]
            cpos = acq_1.acquisition_parameters.centred_position
            # sample = self.get_data_model().get_parent().get_parent()
            sample = self.get_data_model().get_sample_node()

            try:
                if dc.experiment_type is EXPERIMENT_TYPE.HELICAL:
                    acq_1, acq_2 = (dc.acquisitions[0], dc.acquisitions[1])
                    #self.collect_hwobj.getChannelObject("helical").setValue(1)

                    start_cpos = acq_1.acquisition_parameters.centred_position
                    end_cpos = acq_2.acquisition_parameters.centred_position

                    helical_oscil_pos = {'1': start_cpos.as_dict(), '2': end_cpos.as_dict()}
                    #self.collect_hwobj.getChannelObject('helical_pos').setValue(helical_oscil_pos)
                    self.collect_hwobj.set_helical(True, helical_oscil_pos)
                    
                    msg = "Helical data collection, moving to start position"
                    log.info(msg)
                    log.info("Moving sample to given position ...")
                    list_item.setText(1, "Moving sample")
                else:
                    #self.collect_hwobj.getChannelObject("helical").setValue(0)
                    self.collect_hwobj.set_helical(False)
                    
                empty_cpos = queue_model_objects.CentredPosition()

                if cpos != empty_cpos:
                    log.info("Moving sample to given position ...")
                    list_item.setText(1, "Moving sample")
                    self.shape_history.select_shape_with_cpos(cpos)
                    self.centring_task = self.diffractometer_hwobj.\
                                         moveToCentredPosition(cpos, wait=False)
                    self.centring_task.get()
                else:
                    pos_dict = self.diffractometer_hwobj.getPositions()
                    cpos = queue_model_objects.CentredPosition(pos_dict)
                    snapshot = self.shape_history.get_snapshot([])
                    acq_1.acquisition_parameters.centred_position = cpos
                    acq_1.acquisition_parameters.centred_position.snapshot_image = snapshot

                param_list = queue_model_objects.to_collect_dict(dc, self.session, sample)
                self.collect_task = self.collect_hwobj.\
                    collect(COLLECTION_ORIGIN_STR.MXCUBE, param_list)                
                self.collect_task.get()

                if 'collection_id' in param_list[0]:
                    dc.id = param_list[0]['collection_id']

                dc.acquisitions[0].path_template.xds_dir = param_list[0]['xds_dir']

            except gevent.GreenletExit:
                #log.warning("Collection stopped by user.")
                list_item.setText(1, 'Stopped')
                raise QueueAbortedException('queue stopped by user', self)
            except Exception as ex:
                print traceback.print_exc()
                raise QueueExecutionException(ex.message, self)
        else:
            log.error("Could not call the data collection routine," +\
                      " check the beamline configuration")
            list_item.setText(1, 'Failed')
            msg = "Could not call the data collection" +\
                  " routine, check the beamline configuration"
            raise QueueExecutionException(msg, self)
        
class PX2EnergyScanQueueEntry(EnergyScanQueueEntry):
    def __init__(self, view=None, data_model=None):
        EnergyScanQueueEntry.__init__(self, view, data_model)
        self.energy_scan_hwobj = None
        self.session_hwobj = None
        self.energy_scan_task = None
        self._failed = False
    
    def energy_scan_finished(self, scan_info):
        energy_scan = self.get_data_model()
        scan_file_path = os.path.join(energy_scan.path_template.directory,
                                      energy_scan.path_template.get_prefix())
        logging.info('self.energy_scan_hwobj %s type %s' % (self.energy_scan_hwobj, type(self.energy_scan_hwobj)))
        logging.info('energy_scan %s type %s' % (energy_scan, type(energy_scan))) 
        scan_file_archive_path = os.path.join(energy_scan.path_template.\
                                              get_archive_directory(),
                                              energy_scan.path_template.get_prefix())
        logging.info('energy_scan.element_symbol %s, energy_scan.edge %s, scan_file_archive_path %s, scan_file_path %s' %(energy_scan.element_symbol, energy_scan.edge, scan_file_archive_path, scan_file_path))
        egy_result = self.energy_scan_hwobj.doChooch(energy_scan.element_symbol, energy_scan.edge, scan_file_archive_path, scan_file_path)


        if egy_result is None:
             logging.info('energy_scan. failed. ')
             return None

        (pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, rm, chooch_graph_x, chooch_graph_y1, chooch_graph_y2, title) = egy_result

        #scan_info = self.energy_scan_hwobj.scanInfo

        # This does not always apply, update model so
        # that its possible to access the sample directly from
        # the EnergyScan object.
        sample = self.get_view().parent().parent().get_model()
        sample.crystals[0].energy_scan_result.peak = pk
        sample.crystals[0].energy_scan_result.inflection = ip
        sample.crystals[0].energy_scan_result.first_remote = rm
        sample.crystals[0].second_remote = None

        energy_scan.result = sample.crystals[0].energy_scan_result

        logging.getLogger("user_level_log").\
            info("Energy scan, result: peak: %.4f, inflection: %.4f" %
                 (sample.crystals[0].energy_scan_result.peak,
                  sample.crystals[0].energy_scan_result.inflection))

        self.get_view().setText(1, "Done")
