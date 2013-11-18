"""
Containes the classes:
* QueueuEntryContainer
* BaseQueueEntry
* DummyQueueEntry
* TaskGroupQueueEntry
* SampleQueueEntry
* SampleCentringQueueEntry
* DataCollectionQueueEntry
* CharacterisationQueueEntry
* EnergyScanQueueEntry.

All queue entries inherits the baseclass BaseQueueEntry which inturn
inherits QueueEntryContainer. This makes it possible to arrange and
execute queue entries in a hierarchical maner.

The rest of the classes: DummyQueueEntry, TaskGroupQueueEntry,
SampleQueueEntry, SampleCentringQueueEntry, DataCollectionQueueEntry,
CharacterisationQueueEntry, EnergyScanQueueEntry are concrete
implementations of tasks.
"""

import gevent
import traceback
import logging
import time
import queue_model_objects_v1 as queue_model_objects
import pprint
import os
import ShapeHistory as shape_history

#import edna_test_data
#from XSDataMXCuBEv1_3 import XSDataInputMXCuBE

from collections import namedtuple
from queue_model_enumerables_v1 import COLLECTION_ORIGIN_STR
from queue_model_enumerables_v1 import CENTRING_METHOD
from queue_model_enumerables_v1 import EXPERIMENT_TYPE
from BlissFramework.Utils import widget_colors
from HardwareRepository.HardwareRepository import dispatcher

__author__ = "Marcus Oskarsson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["My great coleagues", "The MxCuBE colaboration"]

__version__ = "0.1"
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Beta"


status_list = ['SUCCESS','WARNING', 'FAILED']
QueueEntryStatusType = namedtuple('QueueEntryStatusType', status_list)
QUEUE_ENTRY_STATUS = QueueEntryStatusType(0,1,2,)


class QueueExecutionException(Exception):
    def __init__(self, message, origin):
        Exception.__init__(self, message, origin)
        self.origin = origin


class QueueAbortedException(QueueExecutionException):
    def __init__(self, message, origin):
        Exception.__init__(self, message, origin)
        self.origin = origin


class QueueSkippEntryException(QueueExecutionException):
    def __init__(self, message, origin):
        Exception.__init__(self, message, origin)
        self.origin = origin


class QueueEntryContainer(object):
    """
    A QueueEntryContainer has a list of queue entries, classes
    inheriting BaseQueueEntry, and a Queue object. The Queue object
    controls/handles the execution of the queue entries.
    """
    def __init__(self):
        object.__init__(self)
        self._queue_entry_list = []
        self._queue_controller = None
        self._parent_container = None

    def enqueue(self, queue_entry, queue_controller=None):
        # A queue entry container has a QueueController object
        # which controls the execution of the tasks in the
        # container. The container is set to be its own controller
        # if none is given.
        if queue_controller:
            queue_entry.set_queue_controller(queue_controller)
        else:
            queue_entry.set_queue_controller(self)

        queue_entry.set_container(self)
        self._queue_entry_list.append(queue_entry)

    def dequeue(self, queue_entry):
        """
        Dequeues the QueueEntry <queue_entry> and returns the
        dequeued entry.

        Throws ValueError if the queue_entry is not in the queue.

        :param queue_entry: The queue entry to dequeue/remove.
        :type queue_entry: QueueEntry

        :returns: The dequeued entry.
        :rtype: QueueEntry
        """
        result = None
        index = None
        queue_entry.set_queue_controller(None)
        queue_entry.set_container(None)

        try:
            index = self._queue_entry_list.index(queue_entry)
        except ValueError:
            raise

        if index is not None:
            result = self._queue_entry_list.pop(index)

        log = logging.getLogger('queue_exec')
        log.info('dequeue called with: ' + str(queue_entry))
        log.info('Queue is :' + str(self.get_queue_controller()))

        return result

    def swap(self, queue_entry_a, queue_entry_b):
        """
        Swaps places between the two queue entries <queue_entry_a> and
        <queue_entry_b>.

        Throws a ValueError if one of the entries does not exist in the
        queue.

        :param queue_entry: Queue entry to swap
        :type queue_entry: QueueEntry

        :param queue_entry: Queue entry to swap
        :type queue_entry: QueueEntry
        """
        index_a = None
        index_b = None

        try:
            index_a = self._queue_entry_list.index(queue_entry_a)
        except ValueError:
            raise

        try:
            index_b = self._queue_entry_list.index(queue_entry_b)
        except ValueError:
            raise

        if (index_a is not None) and (index_b is not None):
            temp = self._queue_entry_list[index_a]
            self._queue_entry_list[index_a] = \
                 self._queue_entry_list[index_b]
            self._queue_entry_list[index_b] = temp

        log = logging.getLogger('queue_exec')
        log.info('swap called with: ' + str(queue_entry_a) + ', ' + \
                 str(queue_entry_b))
        log.info('Queue is :' + str(self.get_queue_controller()))

    def set_queue_controller(self, queue_controller):
        """
        Sets the queue controller, the object that controls execution
        of this QueueEntryContainer.

        :param queue_controller: The queue controller object.
        :type queue_controller: QueueController
        """
        self._queue_controller = queue_controller

    def get_queue_controller(self):
        """
        :returns: The queue controller
        :type queue_controller: QueueController
        """
        return self._queue_controller

    def set_container(self, queue_entry_container):
        """
        Sets the parent queue entry to <queue_entry_container>

        :param queue_entry_container:
        :type queue_entry_container: QueueEntryContainer
        """
        self._parent_container = queue_entry_container

    def get_container(self):
        """
        :returns: The parent QueueEntryContainer.
        :rtype: QueueEntryContainer
        """
        return self._parent_container


class BaseQueueEntry(QueueEntryContainer):
    """
    Base class for queue entry objects. Defines the overall
    interface and behaviour for a queue entry.
    """

    def __init__(self, view=None, data_model=None,
                 view_set_queue_entry=True):
        QueueEntryContainer.__init__(self)
        self._data_model = None
        self._view = None
        self.set_data_model(data_model)
        self.set_view(view, view_set_queue_entry)
        self._checked_for_exec = False
        self.beamline_setup = None
        self._execution_failed = False
        self.status = QUEUE_ENTRY_STATUS.SUCCESS

    def enqueue(self, queue_entry):
        """
        Method inherited from QueueEntryContainer, a derived class
        should newer need to override this method.
        """
        QueueEntryContainer.enqueue(self, queue_entry,
                                    self.get_queue_controller())

    def set_data_model(self, data_model):
        """
        Sets the model node of this queue entry to <data_model>

        :param data_model: The data model node.
        :type data_model: TaskNode
        """
        self._data_model = data_model

    def get_data_model(self):
        """
        :returns: The data model of this queue entry.
        :rtype: TaskNode
        """
        return self._data_model

    def set_view(self, view, view_set_queue_entry=True):
        """
        Sets the view of this queue entry to <view>. Makes the
        correspodning bi-directional connection if view_set_queue_entry
        is set to True. Which is normaly case, it can be usefull with
        'uni-directional' connection in some rare cases.

        :param view: The view to associate with this entry
        :type view: ViewItem

        :param view_set_queue_entry: Bi- or uni-directional
                                     connection to view.
        :type view_set_queue_entry: bool
        """
        if view:
            self._view = view

            if view_set_queue_entry:
                view.set_queue_entry(self)

    def get_view(self):
        """
        :returns the view:
        :rtype: ViewItem
        """
        return self._view

    def is_enabled(self):
        """
        :returns: True if this item is enabled.
        :rtype: bool
        """
        return self._checked_for_exec

    def set_enabled(self, state):
        """
        Enables or disables this entry, controls wether this item
        should be executed (enabled) or not (disabled)

        :param state: Enabled if state is True otherwise disabled.
        :type state: bool
        """
        self._checked_for_exec = state

    def execute(self):
        """
        Execute method, should be overriden my subclasses, defines
        the main body of the procedure to be performed when the entry
        is executed.

        The default executer calls excute on all child entries after
        this method but before post_execute.
        """
        logging.getLogger('queue_exec').\
            info('Calling execute on: ' + str(self))

    def pre_execute(self):
        """
        Procedure to be done before execute.
        """
        logging.getLogger('queue_exec').\
            info('Calling pre_execute on: ' + str(self))
        self.beamline_setup = self.get_queue_controller().\
                              getObjectByRole("beamline_setup")

    def post_execute(self):
        """
        Procedure to be done after execute, and execute of all
        children of this entry.
        """
        logging.getLogger('queue_exec').\
            info('Calling post_execute on: ' + str(self))
        view = self.get_view()

        if self.status == QUEUE_ENTRY_STATUS.SUCCESS:
            view.setBackgroundColor(widget_colors.LIGHT_GREEN)
        elif self.status == QUEUE_ENTRY_STATUS.WARNING:
            view.setBackgroundColor(widget_colors.LIGHT_YELLOW)
        elif self.status == QUEUE_ENTRY_STATUS.FAILED:
            view.setBackgroundColor(widget_colors.LIGHT_RED)
            
        view.setHighlighted(True)
        view.setOn(False)
        self.get_data_model().set_executed(True)

    def stop(self):
        """
        Stops the execution of this entry, should free
        external resources, cancel all pending processes and so on.
        """
        self.get_view().setText(1, 'Stopped')
        logging.getLogger('queue_exec').\
            info('Calling stop on: ' + str(self))

    def handle_exception(self, ex):
        view = self.get_view()

        if view and isinstance(ex, QueueExecutionException):
            if ex.origin is self:
                view.setBackgroundColor(widget_colors.LIGHT_RED)

    def __str__(self):
        s = '<%s object at %s> [' % (self.__class__.__name__, hex(id(self)))

        for entry in self._queue_entry_list:
            s += str(entry)

        return s + ']'


class DummyQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)

    def execute(self):
        BaseQueueEntry.execute(self)
        self.get_view().setText(1, 'Sleeping 5 s')
        time.sleep(5)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)

    def post_execute(self):
        BaseQueueEntry.post_execute(self)


class TaskGroupQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.lims_client_hwobj = None
        self._lims_group_id = 0
        self.session_hwobj = None

    def execute(self):
        BaseQueueEntry.execute(self)
        group_data = {'sessionId': self.session_hwobj.session_id}

        try:
            gid = self.lims_client_hwobj.\
                  _store_data_collection_group(group_data)
            self.get_data_model().lims_group_id = gid
        except Exception as ex:
            msg = 'Could not create the data collection group' + \
                  ' in lims. Reason: ' + ex.message, self
            raise QueueExecutionException(msg, self)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self.lims_client_hwobj = self.beamline_setup.lims_client_hwobj
        self.session_hwobj = self.beamline_setup.session_hwobj

    def post_execute(self):
        BaseQueueEntry.post_execute(self)


class SampleQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.sample_changer_hwobj = None
        self.diffractometer_hwobj = None
        self.sample_centring_result = None

    def execute(self):
        BaseQueueEntry.execute(self)
        log = logging.getLogger('queue_exec')

        if not self._data_model.free_pin_mode:
            if self.sample_changer_hwobj is not None:
                log.info("Loading sample " + self._data_model.loc_str)
                sample_mounted = self.sample_changer_hwobj.\
                                 is_mounted_sample(self._data_model.location)
                if not sample_mounted:
                    self.sample_centring_result = gevent.event.AsyncResult()
                    try:
                        mount_sample(self.beamline_setup, self._view, self._data_model,
                                     self.centring_done, self.sample_centring_result)
                    except Exception as e:
                        self._view.setText(1, "Error loading")
                        msg = "Error loading sample, please check" +\
                              " sample changer: " + e.message
                        log.error(msg)
                        raise QueueExecutionException(e.message, self)
                else:
                    log.info("Sample already mounted")
            else:
                msg = "SampleQueuItemPolicy does not have any " +\
                      "sample changer hardware object, cannot " +\
                      "mount sample"
                log.info(msg)

    def centring_done(self, success, centring_info):
        if success:
            self.sample_centring_result.set(centring_info)
        else:
            msg = "Loop centring failed or was cancelled, " +\
                  "please continue manually."
            logging.getLogger("user_level_log").warning(msg)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self.sample_changer_hwobj = self.beamline_setup.sample_changer_hwobj
        self.diffractometer_hwobj = self.beamline_setup.diffractometer_hwobj
        self.shape_history = self.beamline_setup.shape_history_hwobj

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        self._view.setText(1, "")


class SampleCentringQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.sample_changer_hwobj = None
        self.diffractometer_hwobj = None
        self.shape_history = None

    def execute(self):
        BaseQueueEntry.execute(self)

        self.get_view().setText(1, 'Waiting for input')
        log = logging.getLogger("user_level_log")
        log.warning("Please select a centred position.")

        self.get_queue_controller().pause(True)
        pos = None

        if len(self.shape_history.selected_shapes):
            pos = self.shape_history.selected_shapes.values()[0]
        elif len(self.shape_history.shapes):
            pos = self.shape_history.shapes.values()[0]
        else:
            log.warning("No centred position selected, " +\
                        " using current position.")

            # Create a centred postions of the current postion
            pos_dict = self.diffractometer_hwobj.getPositions()
            cpos = queue_model_objects.CentredPosition(pos_dict)
            pos = shape_history.Point(None, cpos, None)

        tasks = self.get_data_model().get_tasks()

        for task in tasks:
            cpos = pos.get_centred_positions()[0]

            if pos.qub_point is not None:
                snapshot = self.shape_history.\
                           get_snapshot([pos.qub_point])
            else:
                snapshot = self.shape_history.get_snapshot([])

            cpos.snapshot_image = snapshot 
            task.set_centred_positions(cpos)

        self.get_view().setText(1, 'Input accepted')

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self.sample_changer_hwobj = self.beamline_setup.sample_changer_hwobj
        self.diffractometer_hwobj = self.beamline_setup.diffractometer_hwobj
        self.shape_history = self.beamline_setup.shape_history_hwobj

    def post_execute(self):
        BaseQueueEntry.post_execute(self)


class DataCollectionQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)

        self.collect_hwobj = None
        self.diffractometer_hwobj = None
        self.collect_task = None
        self.centring_task = None
        self.shape_history = None
        self.session = None
        self.lims_client_hwobj = None

    def execute(self):
        BaseQueueEntry.execute(self)
        data_collection = self.get_data_model()

        if data_collection:
            self.collect_dc(data_collection, self.get_view())

        if self.shape_history:
            self.shape_history.de_select_all()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)

        self.lims_client_hwobj = self.beamline_setup.lims_client_hwobj
        self.collect_hwobj = self.beamline_setup.collect_hwobj
        self.diffractometer_hwobj = self.beamline_setup.diffractometer_hwobj
        self.shape_history = self.beamline_setup.shape_history_hwobj
        self.session = self.beamline_setup.session_hwobj

        qc = self.get_queue_controller()

        qc.connect(self.collect_hwobj, 'collectStarted',
                   self.collect_started)
        qc.connect(self.collect_hwobj, 'collectNumberOfFrames',
                   self.preparing_collect)
        qc.connect(self.collect_hwobj, 'collectOscillationStarted',
                   self.collect_osc_started)
        qc.connect(self.collect_hwobj, 'collectOscillationFailed',
                   self.collect_failed)
        qc.connect(self.collect_hwobj, 'collectOscillationFinished',
                   self.collect_finished)
        qc.connect(self.collect_hwobj, 'collectImageTaken',
                   self.image_taken)
        qc.connect(self.collect_hwobj, 'collectNumberOfFrames',
                   self.collect_number_of_frames)

        if self.get_data_model().get_parent():
            gid = self.get_data_model().get_parent().lims_group_id
            self.get_data_model().lims_group_id = gid

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        qc = self.get_queue_controller()

        qc.disconnect(self.collect_hwobj, 'collectStarted',
                     self.collect_started)
        qc.disconnect(self.collect_hwobj, 'collectNumberOfFrames',
                     self.preparing_collect)
        qc.disconnect(self.collect_hwobj, 'collectOscillationStarted',
                     self.collect_osc_started)
        qc.disconnect(self.collect_hwobj, 'collectOscillationFailed',
                     self.collect_failed)
        qc.disconnect(self.collect_hwobj, 'collectOscillationFinished',
                     self.collect_finished)
        qc.disconnect(self.collect_hwobj, 'collectImageTaken',
                     self.image_taken)
        qc.disconnect(self.collect_hwobj, 'collectNumberOfFrames',
                     self.collect_number_of_frames)

    def collect_dc(self, dc, list_item):
        log = logging.getLogger("user_level_log")

        if self.collect_hwobj:
            acq_1 = dc.acquisitions[0]
            cpos = acq_1.acquisition_parameters.centred_position
            #acq_1.acquisition_parameters.take_snapshots = True
            param_list = queue_model_objects.\
                to_collect_dict(dc, self.session)

            try:
                if dc.experiment_type is EXPERIMENT_TYPE.HELICAL:
                    acq_1, acq_2 = (dc.acquisitions[0], dc.acquisitions[1])
                    self.collect_hwobj.getChannelObject("helical").setValue(1)

                    start_cpos = acq_1.acquisition_parameters.centred_position
                    end_cpos = acq_2.acquisition_parameters.centred_position

                    dc.lims_end_pos_id = self.lims_client_hwobj.\
                                         store_centred_position(end_cpos)

                    helical_oscil_pos = {'1': start_cpos.as_dict(), '2': end_cpos.as_dict()}
                    self.collect_hwobj.getChannelObject('helical_pos').setValue(helical_oscil_pos)

                    msg = "Helical data collection with start" +\
                          "position: " + str(pprint.pformat(start_cpos)) + \
                          " and end position: " + str(pprint.pformat(end_cpos))
                    log.info(msg)
                    list_item.setText(1, "Moving sample")
                else:
                    self.collect_hwobj.getChannelObject("helical").setValue(0)

                empty_cpos = queue_model_objects.CentredPosition()

                if cpos != empty_cpos:
                    log.info("Moving to: " + str(cpos))
                    list_item.setText(1, "Moving sample")
                    self.shape_history.select_shape_with_cpos(cpos)
                    self.centring_task = self.diffractometer_hwobj.\
                                         moveToCentredPosition(cpos)
                    self.centring_task.get()
                else:
                    pos_dict = self.diffractometer_hwobj.getPositions()
                    cpos = queue_model_objects.CentredPosition(pos_dict)
                    snapshot = self.shape_history.get_snapshot([])
                    acq_1.acquisition_parameters.centred_position = cpos
                    acq_1.acquisition_parameters.centred_position.snapshot_image = snapshot

                dc.lims_start_pos_id = self.lims_client_hwobj.store_centred_position(cpos)
                    
                #log.info("Calling collect hw-object with: " + str(dc.as_dict()))

                #log.info("Collecting: " + str(dc.as_dict()))
                self.collect_task = self.collect_hwobj.\
                                    collect(COLLECTION_ORIGIN_STR.MXCUBE,
                                            param_list)                
                self.collect_task.get()
                
                if 'collection_id' in param_list[0]:
                    dc.id = param_list[0]['collection_id']
                
            except gevent.GreenletExit:
                log.exception("Collection stopped by user.")
                log.warning("Collection stopped by user.")
                list_item.setText(1, 'Stopped')
                raise QueueAbortedException('Queue stopped', self)
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

    def collect_started(self, owner, num_oscillations):
        pass

    def collect_number_of_frames(self, number_of_images=0):
        pass

    def image_taken(self, image_number):
        # this is to work around the remote access problem
        dispatcher.send("collect_started")
        num_images = str(self.get_data_model().acquisitions[0].\
                     acquisition_parameters.num_images)

        first_image = self.get_data_model().acquisitions[0].\
                      acquisition_parameters.first_image

        if first_image != 0:
            image_number = image_number - first_image + 1

        self.get_view().setText(1, str(image_number) + "/" + num_images)

    def preparing_collect(self, number_images=0):
        self.get_view().setText(1, "Collecting")

    def collect_failed(self, owner, state, message, *args):
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        self.get_view().setText(1, "Failed")
        logging.getLogger("user_level_log").error(message.replace('\n', ' '))
        raise QueueExecutionException(message.replace('\n', ' '), self)

    def collect_osc_started(self, owner, blsampleid, barcode, location,
                            collect_dict, osc_id):
        self.get_view().setText(1, "Preparing")

    def collect_finished(self, owner, state, message, *args):
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        self.get_view().setText(1, "Collection done")
        logging.getLogger("user_level_log").info('Collection completed')

    def stop(self):
        BaseQueueEntry.stop(self)

        try:
            self.get_view().setText(1, 'Stopping ...')
            if self.collect_task:
                self.collect_task.kill(block=False)

            if self.centring_task:
                self.centring_task.kill(block=False)

        except gevent.GreenletExit:
            raise

        self.get_view().setText(1, 'Stopped')
        logging.getLogger('queue_exec').info('Calling stop on: ' + str(self))
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")

        raise QueueAbortedException('Queue stopped', self)


class CharacterisationGroupQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None,
                 view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)
        self.char_qe = None

    def execute(self):
        BaseQueueEntry.execute(self)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        char = self.get_data_model()
        reference_image_collection = char.reference_image_collection

        gid = self.get_data_model().get_parent().lims_group_id
        reference_image_collection.lims_group_id = gid

        # Enqueue the reference collection and the characterisation
        # routine.
        dc_qe = DataCollectionQueueEntry(self.get_view(),
                                         reference_image_collection,
                                         view_set_queue_entry=False)
        dc_qe.set_enabled(True)
        self.enqueue(dc_qe)

        char_qe = CharacterisationQueueEntry(self.get_view(), char,
                                             view_set_queue_entry=False)
        char_qe.set_enabled(True)
        self.enqueue(char_qe)
        self.char_qe = char_qe

    def post_execute(self):
        self.status = self.char_qe.status
        BaseQueueEntry.post_execute(self)


class CharacterisationQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None,
                 view_set_queue_entry=True):

        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)
        self.data_analysis_hwobj = None
        self.diffractometer_hwobj = None
        self.queue_model_hwobj = None
        self.session_hwobj = None
        self.edna_result = None

    def execute(self):
        BaseQueueEntry.execute(self)
        log = logging.getLogger("user_level_log")

        self.get_view().setText(1, "Characterising")
        log.info("Characterising, please wait ...")
        char = self.get_data_model()
        reference_image_collection = char.reference_image_collection
        characterisation_parameters = char.characterisation_parameters

        if self.data_analysis_hwobj is not None:
            edna_input = self.data_analysis_hwobj.\
                         from_params(reference_image_collection,
                                     characterisation_parameters)
            #edna_input = XSDataInputMXCuBE.parseString(edna_test_data.EDNA_TEST_DATA)
            #edna_input.process_directory = reference_image_collection.acquisitions[0].\
            #                                path_template.process_directory

            self.edna_result = self.data_analysis_hwobj.characterise(edna_input)

        if self.edna_result:
            logging.getLogger("user_level_log").\
                info("Characterisation successful.")

            char.html_report = self.data_analysis_hwobj.\
                               get_html_report(self.edna_result)

            try:
                strategy_result = self.edna_result.getCharacterisationResult().\
                                  getStrategyResult()
            except:
                strategy_result = None
                

            if strategy_result:
                collection_plan = strategy_result.getCollectionPlan()
            else:
                collection_plan = None

            if collection_plan:
                dcg_model = char.get_parent()
                sample_data_model = dcg_model.get_parent()

                new_dcg_name = 'Diffraction plan'
                new_dcg_num = dcg_model.get_parent().\
                              get_next_number_for_name(new_dcg_name)

                new_dcg_model = queue_model_objects.TaskGroup()
                new_dcg_model.set_enabled(False)
                new_dcg_model.set_name(new_dcg_name)
                new_dcg_model.set_number(new_dcg_num)
                self.queue_model_hwobj.add_child(sample_data_model,
                                                 new_dcg_model)

                edna_collections = queue_model_objects.\
                                   dc_from_edna_output(self.edna_result,
                                                       reference_image_collection,
                                                       new_dcg_model,
                                                       sample_data_model,
                                                       self.beamline_setup)

                for edna_dc in edna_collections:
                    path_template = edna_dc.acquisitions[0].path_template
                    run_number = self.queue_model_hwobj.get_next_run_number(path_template)
                    path_template.run_number = run_number

                    edna_dc.set_enabled(False)
                    edna_dc.set_name(path_template.get_prefix())
                    edna_dc.set_number(path_template.run_number)
                    self.queue_model_hwobj.add_child(new_dcg_model, edna_dc)

                self.get_view().setText(1, "Done")
            else:
                self.get_view().setText(1, "No result")
                self.status = QUEUE_ENTRY_STATUS.WARNING
                log.info("EDNA-Characterisation completed " +\
                         "successfully but without collection plan.")
                log.warning("Characterisation completed" +\
                            "successfully but without collection plan.")
        else:
            self.get_view().setText(1, "Charact. Failed")

            if self.data_analysis_hwobj.is_running():
                log.error('EDNA-Characterisation, software is not responding.')
                log.error("Characterisation completed with error: "\
                          + " data analysis server is not responding.")
            else:
                log.error('EDNA-Characterisation completed with a failure.')
                log.error("Characterisation completed with errors.")

        char.set_executed(True)
        self.get_view().setHighlighted(True)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self.get_view().setOn(True)
        self.get_view().setHighlighted(False)

        self.data_analysis_hwobj = self.beamline_setup.data_analysis_hwobj
        self.diffractometer_hwobj = self.beamline_setup.diffractometer_hwobj
        self.queue_model_hwobj = self.get_view().listView().parent().queue_model_hwobj
        self.session_hwobj = self.beamline_setup.session_hwobj

    def post_execute(self):
        BaseQueueEntry.post_execute(self)


class EnergyScanQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.energy_scan_hwobj = None
        self.session_hwobj = None
        self.energy_scan_task = None
        self._failed = False

    def execute(self):
        BaseQueueEntry.execute(self)

        if self.energy_scan_hwobj:
            energy_scan = self.get_data_model()
            self.get_view().setText(1, "Starting energy scan")

            sample_model = self.get_data_model().\
                           get_parent().get_parent()

            sample_lims_id = sample_model.lims_id

            # No sample id, pass None to startEnergyScan
            if sample_lims_id == -1:
                sample_lims_id = None

            self.energy_scan_task = \
                gevent.spawn(self.energy_scan_hwobj.startEnergyScan,
                             energy_scan.element_symbol,
                             energy_scan.edge,
                             energy_scan.path_template.directory,
                             energy_scan.path_template.get_prefix(),
                             self.session_hwobj.session_id,
                             sample_lims_id)

        self.energy_scan_task.get()
        self.energy_scan_hwobj.ready_event.wait()
        self.energy_scan_hwobj.ready_event.clear()

        # Test code
        # sample = self.get_view().parent().parent().get_model()
        # sample.crystals[0].energy_scan_result.peak = 12
        # sample.crystals[0].energy_scan_result.inflection = 13
        # sample.crystals[0].energy_scan_result.first_remote = 14
        # sample.crystals[0].second_remote = None

        # logging.getLogger("user_level_log").\
        #     info("Energy scan, result: peak: %.4f, inflection: %.4f" %
        #          (sample.crystals[0].energy_scan_result.peak,
        #           sample.crystals[0].energy_scan_result.inflection))

        # self.get_view().setText(1, "Done")

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self._failed = False
        self.energy_scan_hwobj = self.beamline_setup.energy_hwobj
        self.session_hwobj = self.beamline_setup.session_hwobj

        qc = self.get_queue_controller()

        qc.connect(self.energy_scan_hwobj, 'scanStatusChanged',
                   self.energy_scan_status_changed)

        qc.connect(self.energy_scan_hwobj, 'energyScanStarted',
                   self.energy_scan_started)

        qc.connect(self.energy_scan_hwobj, 'energyScanFinished',
                   self.energy_scan_finished)

        qc.connect(self.energy_scan_hwobj, 'energyScanFailed',
                   self.energy_scan_failed)

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        qc = self.get_queue_controller()

        qc.disconnect(self.energy_scan_hwobj, 'scanStatusChanged',
                      self.energy_scan_status_changed)

        qc.disconnect(self.energy_scan_hwobj, 'energyScanStarted',
                      self.energy_scan_started)

        qc.disconnect(self.energy_scan_hwobj, 'energyScanFinished',
                      self.energy_scan_finished)

        qc.disconnect(self.energy_scan_hwobj, 'energyScanFailed',
                      self.energy_scan_failed)

        if self._failed:
            raise QueueAbortedException('Queue stopped', self)

    def energy_scan_status_changed(self, msg):
        logging.getLogger("user_level_log").info(msg)

    def energy_scan_started(self):
        logging.getLogger("user_level_log").info("Energy scan started.")
        self.get_view().setText(1, "In progress")

    def energy_scan_finished(self, scan_info):
        energy_scan = self.get_data_model()
        scan_file_path = os.path.join(energy_scan.path_template.directory,
                                      energy_scan.path_template.get_prefix())

        scan_file_archive_path = os.path.join(energy_scan.path_template.\
                                              get_archive_directory(),
                                              energy_scan.path_template.get_prefix())

        (pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, rm,
         chooch_graph_x, chooch_graph_y1, chooch_graph_y2, title) = \
        self.energy_scan_hwobj.doChooch(None, energy_scan.element_symbol,
                                        energy_scan.edge,
                                        scan_file_archive_path,
                                        scan_file_path)

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

    def energy_scan_failed(self):
        self._failed = True


class GenericWorkflowQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.rpc_server_hwobj = None
        self.workflow_hwobj = None
        self.workflow_running = False
        self.workflow_started = False

    def execute(self):
        BaseQueueEntry.execute(self)

        if str(self.workflow_hwobj.state.value) != 'ON':
            self.workflow_hwobj.abort()
            time.sleep(3)

            while str(self.workflow_hwobj.state.value) != 'ON':
                time.sleep(0.5)

        msg = "Starting workflow (%s), please wait." % (self.get_data_model()._type)
        logging.getLogger("user_level_log").info(msg)
        workflow_params = self.get_data_model().params_list
        self.workflow_running = True
        self.workflow_hwobj.start(workflow_params)

        while self.workflow_running:
            time.sleep(1)

    def workflow_state_handler(self, state):
        if isinstance(state, tuple):
            state = str(state[0])
        else:
            state = str(state)

        if state == 'ON':
            self.workflow_running = False
        elif state == 'RUNNING':
            self.workflow_started = True
        elif state == 'OPEN':
            msg = "Workflow waiting for input"
            logging.getLogger("user_level_log").warning(msg)
            self.get_queue_controller().show_workflow_tab() 

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        
        qc = self.get_queue_controller()
        self.workflow_hwobj = self.beamline_setup.workflow_hwobj

        qc.connect(self.workflow_hwobj, 'stateChanged',
                  self.workflow_state_handler)

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        qc = self.get_queue_controller()
        qc.disconnect(self.workflow_hwobj, 'stateChanged',
                      self.workflow_state_handler)
        # reset state
        self.workflow_started = False
        self.workflow_running = False


    def stop(self):
        BaseQueueEntry.stop(self)
        self.workflow_hwobj.abort()
        self.get_view().setText(1, 'Stopped')
        raise QueueAbortedException('Queue stopped', self)

def mount_sample(beamline_setup_hwobj, view, data_model,
                 centring_done_cb, async_result):
    view.setText(1, "Loading sample")
    beamline_setup_hwobj.shape_history_hwobj.clear_all()
    log = logging.getLogger("user_level_log")

    loc = data_model.location
    holder_length = data_model.holder_length
    beamline_setup_hwobj.sample_changer_hwobj.load_sample(holder_length,
                                                          sample_location=loc,
                                                          wait=True)

    dm = beamline_setup_hwobj.diffractometer_hwobj

    if dm is not None:
        try:
            dm.connect("centringAccepted", centring_done_cb)
            centring_method = view.listView().parent().\
                              centring_method

            if centring_method == CENTRING_METHOD.MANUAL:
                log.warning("Manual centring used, waiting for" +\
                            " user to center sample")
                dm.startCentringMethod(dm.MANUAL3CLICK_MODE)
            elif centring_method == CENTRING_METHOD.LOOP:
                dm.startCentringMethod(dm.C3D_MODE)
                log.warning("Centring in progress. Please save" +\
                            " the suggested centring or re-center")
            elif centring_method == CENTRING_METHOD.CRYSTAL:
                log.info("Centring sample, please wait.")
                dm.startAutoCentring()
                log.warning("Please save or reject the centring")

            view.setText(1, "Centring !")
            async_result.get()
        finally:
            dm.disconnect("centringAccepted", centring_done_cb)


MODEL_QUEUE_ENTRY_MAPPINGS = \
    {queue_model_objects.DataCollection: DataCollectionQueueEntry,
     queue_model_objects.Characterisation: CharacterisationGroupQueueEntry,
     queue_model_objects.EnergyScan: EnergyScanQueueEntry,
     queue_model_objects.SampleCentring: SampleCentringQueueEntry,
     queue_model_objects.Sample: SampleQueueEntry,
     queue_model_objects.TaskGroup: TaskGroupQueueEntry,
     queue_model_objects.Workflow: GenericWorkflowQueueEntry}
