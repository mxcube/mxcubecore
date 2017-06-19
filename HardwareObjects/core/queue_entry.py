"""
Contains following classes:
* QueueEntryContainer
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
import os
import autoprocessing

import edna_test_data
from XSDataMXCuBEv1_3 import XSDataInputMXCuBE

from collections import namedtuple
from queue_model_enumerables_v1 import *
from HardwareRepository.HardwareRepository import dispatcher

status_list = ['SUCCESS','WARNING', 'FAILED']
QueueEntryStatusType = namedtuple('QueueEntryStatusType', status_list)
QUEUE_ENTRY_STATUS = QueueEntryStatusType(0,1,2,)


class QueueExecutionException(Exception):
    def __init__(self, message, origin):
        Exception.__init__(self, message, origin)
        self.message = message
        self.origin = origin
        self.stack_trace = traceback.format_exc()

class QueueAbortedException(QueueExecutionException):
    def __init__(self, message, origin):
        Exception.__init__(self, message, origin)
        self.origin = origin
        self.message = message
        self.stack_trace = traceback.format_exc()

class QueueSkippEntryException(QueueExecutionException):
    def __init__(self, message, origin):
        Exception.__init__(self, message, origin)
        self.origin = origin
        self.message = message
        self.stack_trace = traceback.format_exc()


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

    def get_queue_entry_list(self):
        return self._queue_entry_list

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
        #log.info('Queue is :' + str(self.get_queue_controller()))

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
        self.type_str = ""

    # def __getstate__(self):
    #     return QueueEntryContainer.__getstate__(self)
    
    # def __setstate__(self, d):
    #     return QueueEntryContainer.__setstate__(self, d)

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
        self.get_data_model().set_running(True)

    def post_execute(self):
        """
        Procedure to be done after execute, and execute of all
        children of this entry.
        """
        logging.getLogger('queue_exec').\
            info('Calling post_execute on: ' + str(self))
        view = self.get_view()

        view.setHighlighted(True)
        view.setOn(False)
        self.get_data_model().set_executed(True)
        self.get_data_model().set_running(False)
        self.get_data_model().set_enabled(False)
        self.set_enabled(False)
        self._set_background_color()

    def _set_background_color(self):
        view = self.get_view()

        if self.get_data_model().is_executed():
            """
            if self.status == QUEUE_ENTRY_STATUS.SUCCESS:
                view.setBackgroundColor(widget_colors.LIGHT_GREEN)
            elif self.status == QUEUE_ENTRY_STATUS.WARNING:
                view.setBackgroundColor(widget_colors.LIGHT_YELLOW)
            elif self.status == QUEUE_ENTRY_STATUS.FAILED:
                view.setBackgroundColor(widget_colors.LIGHT_RED)
            """
            view.set_background_color(self.status + 1)
        else:
            view.set_background_color(0)
            #view.setBackgroundColor(widget_colors.WHITE)

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
                #view.setBackgroundColor(widget_colors.LIGHT_RED)
                view.set_background_color(3)

    def __str__(self):
        s = '<%s object at %s> [' % (self.__class__.__name__, hex(id(self)))

        for entry in self._queue_entry_list:
            s += str(entry)

        return s + ']'

    def get_type_str(self):
        return self.type_str


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
        self.session_hwobj = None
        self.interleave_task = None
        self.interleave_items = None
        self.interleave_sw_list = None
        self.interleave_stoped = None

    def execute(self):
        BaseQueueEntry.execute(self)
        task_model = self.get_data_model()
        gid = task_model.lims_group_id

        do_new_dc_group = True
        # Do not create a new data collection group if one already exists
        # or if the current task group contains a GenericWorkflowQueueEntry
        if gid:
            do_new_dc_group = False
        elif len(self._queue_entry_list) > 0:
            if type(self._queue_entry_list[0]) == GenericWorkflowQueueEntry:
                do_new_dc_group = False
                
        if do_new_dc_group:
            # Creating a collection group with the current session id
            # and a dummy exepriment type OSC. The experiment type
            # will be updated when the collections are stored.
            if task_model.interleave_num_images:
                group_data = {'sessionId': self.session_hwobj.session_id,
                              'experimentType': 'Collect - Multiwedge'}
            else:
                group_data = {'sessionId': self.session_hwobj.session_id,
                              'experimentType': 'OSC'}

            sample_model = task_model.get_parent()
            if sample_model.lims_container_location > -1:
                group_data['actualContainerSlotInSC'] = \
                   sample_model.lims_container_location
            if sample_model.lims_sample_location > -1:
                group_data['actualSampleSlotInContainer'] = \
                   sample_model.lims_sample_location 
               
            try:
                gid = self.lims_client_hwobj.\
                  _store_data_collection_group(group_data)
                self.get_data_model().lims_group_id = gid
            except Exception as ex:
                msg = 'Could not create the data collection group' + \
                      ' in LIMS. Reason: ' + str(ex)
                raise QueueExecutionException(msg, self)

        self.interleave_items = []
        if task_model.interleave_num_images:
            # At first all children are gathered together and
            # checked if interleave is set. For this implementation
            # interleave is just possible for discreet data collections
            ref_num_images = 0
            children_data_model_list =  self._data_model.get_children()

            for child_data_model in children_data_model_list: 
                if isinstance(child_data_model, queue_model_objects.DataCollection):
                    num_images = child_data_model.acquisitions[0].\
                        acquisition_parameters.num_images
                    if num_images > task_model.interleave_num_images:
                        if num_images > ref_num_images:
                            ref_num_images = num_images
                        interleave_item = {}
                        child_data_model.set_experiment_type(\
                            EXPERIMENT_TYPE.COLLECT_MULTIWEDGE)
                        interleave_item["data_model"] = child_data_model
                        for queue_entry in self._queue_entry_list:
                            if queue_entry.get_data_model() == child_data_model:
                                interleave_item["queue_entry"] = queue_entry
                                interleave_item["tree_item"] = queue_entry.get_view()
                        self.interleave_items.append(interleave_item)

        if len(self.interleave_items) > 1:
            interleave_num_images = task_model.interleave_num_images
            self.interleave_task = gevent.spawn(self.execute_iterleaved,
                                                ref_num_images, 
                                                interleave_num_images)
            self.interleave_task.get()

    def execute_iterleaved(self, ref_num_images, interleave_num_images):
        self.get_view().setText(1, "Interleaving...") 
        logging.getLogger("queue_exec").info("Preparing interleaved data collection")

        for interleave_item in self.interleave_items:
            interleave_item["queue_entry"].set_enabled(False)
            interleave_item["tree_item"].set_checkable(False)
            interleave_item["data_model"].lims_group_id = \
                interleave_item["data_model"].get_parent().lims_group_id
            cpos = interleave_item["data_model"].acquisitions[0].\
                acquisition_parameters.centred_position
            sample = interleave_item["data_model"].get_parent().get_parent()
            empty_cpos = queue_model_objects.CentredPosition()
            param_list = queue_model_objects.to_collect_dict(
                 interleave_item["data_model"], self.session_hwobj,
                 sample, cpos if cpos!=empty_cpos else None)
            self.collect_hwobj.prepare_interleave(interleave_item["data_model"],
                                                  param_list)
 
        self.interleave_sw_list = queue_model_objects.create_interleave_sw(\
              self.interleave_items, ref_num_images, interleave_num_images)
        for item_index, item in enumerate(self.interleave_sw_list):
            if not self.interleave_stoped:
                self.get_view().setText(1, "Interleaving subwedge %d (total: %d)" \
                     % (item["collect_index"] + 1, item["sw_index"] + 1))
                acq_par = self.interleave_items[item["collect_index"]]["data_model"].\
                   acquisitions[0].acquisition_parameters
                acq_first_image = acq_par.first_image

                acq_par.first_image = item["sw_first_image"]
                acq_par.num_images = item["sw_actual_size"]
                acq_par.osc_start = item["sw_osc_start"]
                acq_par.in_interleave = (acq_first_image, acq_first_image + item["collect_num_images"] - 1)
                self.interleave_items[item["collect_index"]]["queue_entry"].in_queue = \
                     item_index < (len(self.interleave_sw_list) - 1)

                msg = "Executing interleaved collection (subwedge %d:%d, " % \
                    (item["collect_index"] + 1, item["sw_index"] + 1)
                msg += "from %d to %d, " % (acq_par.first_image, 
                    acq_par.first_image + acq_par.num_images - 1) 
                msg += "osc start: %.2f, osc total range: %.2f)" % \
                    (item["sw_osc_start"], item["sw_osc_range"])
                logging.getLogger("user_level_log").info(msg)

                try:
                   self.interleave_items[item["collect_index"]]["queue_entry"].pre_execute()
                   self.interleave_items[item["collect_index"]]["queue_entry"].execute()
                except:
                   pass
                self.interleave_items[item["collect_index"]]["queue_entry"].post_execute()
                self.interleave_items[item["collect_index"]]["tree_item"].\
                      setText(1, "Subwedge %d:%d done" % (\
                              item["collect_index"] + 1, 
                              item["sw_index"] + 1))

        if not self.interleave_stoped:
            logging.getLogger("queue_exec").info("Interleaved task finished")

        """
        for interleave_item in self.interleave_items:
            sample = interleave_item["data_model"].get_parent().get_parent()
            param_list = queue_model_objects.to_collect_dict(
                 interleave_item["data_model"], self.session_hwobj,
                 sample)
            self.collect_hwobj.finalize_interleave(param_list)
        """

        self.interleave_task = None

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self.lims_client_hwobj = self.beamline_setup.lims_client_hwobj
        self.session_hwobj = self.beamline_setup.session_hwobj
        self.collect_hwobj = self.beamline_setup.collect_hwobj

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        self.get_view().setText(1, "")

    def stop(self):
        BaseQueueEntry.stop(self)
        if self.interleave_task:
            self.interleave_stoped = True
            self.interleave_task.kill()       
        self.get_view().setText(1, "Interleave stoped")

class SampleQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of sample queue entries. Mounting, launching centring
    and so on.
    """
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.sample_changer_hwobj = None
        self.diffractometer_hwobj = None
        self.plate_manipulator_hwobj = None
        self.sample_centring_result = None

    def __getstate__(self):
        d = dict(self.__dict__)
        d["sample_centring_result"] = None
        return d
 
    def __setstate__(self, d):
        self.__dict__.update(d)

    def execute(self):
        BaseQueueEntry.execute(self)
        log = logging.getLogger('queue_exec')
        sc_used = not self._data_model.free_pin_mode
 
        # Only execute samples with collections and when sample changer is used
        if len(self.get_data_model().get_children()) != 0 and sc_used:
            if self.diffractometer_hwobj.in_plate_mode():
                mount_device = self.plate_manipulator_hwobj
            else:
                mount_device = self.sample_changer_hwobj

            if mount_device is not None:
                log.info("Loading sample " + self._data_model.loc_str)
                sample_mounted = mount_device.is_mounted_sample(self._data_model.location)
                if not sample_mounted:
                    self.sample_centring_result = gevent.event.AsyncResult()
                    try:
                        mount_sample(self.beamline_setup, self._view, self._data_model,
                                     self.centring_done, self.sample_centring_result)
                    except Exception as e:
                        self._view.setText(1, "Error loading")
                        msg = "Error loading sample, please check" +\
                              " sample changer: " + str(e)
                        log.error(msg)
                        if isinstance(e, QueueSkippEntryException):
                            raise
                        else: 
                            raise QueueExecutionException(e.message, self)
                else:
                    log.info("Sample already mounted")
            else:
                msg = "SampleQueuItemPolicy does not have any " +\
                      "sample changer hardware object, cannot " +\
                      "mount sample"
                log.info(msg)

    def centring_done(self, success, centring_info):
        if not success:
            msg = "Loop centring failed or was cancelled, " +\
                  "please continue manually."
            logging.getLogger("queue_exec").warning(msg)
        self.sample_centring_result.set(centring_info)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        try:
            self.sample_changer_hwobj = self.beamline_setup.sample_changer_hwobj
        except AttributeError:
            self.sample_changer_hwobj = None
        self.diffractometer_hwobj = self.beamline_setup.diffractometer_hwobj
        try:
            self.plate_manipulator_hwobj = self.beamline_setup.plate_manipulator_hwobj
        except AttributeError:
            self.plate_manipulator_hwobj = None
        self.shape_history = self.beamline_setup.shape_history_hwobj

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        params = []

        # Start grouped processing, get information from each collection
        # and call autoproc with grouped processing option
        for child in self.get_data_model().get_children():
            for grand_child in child.get_children():
                if isinstance(grand_child, queue_model_objects.DataCollection):
                    xds_dir = grand_child.acquisitions[0].path_template.xds_dir
                    residues = grand_child.processing_parameters.num_residues
                    anomalous = grand_child.processing_parameters.anomalous
                    space_group = grand_child.processing_parameters.space_group
                    cell = grand_child.processing_parameters.get_cell_str()
                    inverse_beam = grand_child.acquisitions[0].acquisition_parameters.inverse_beam

                    params.append({'collect_id': grand_child.id, 
                                   'xds_dir': xds_dir,
                                   'residues': residues,
                                   'anomalous' : anomalous,
                                   'spacegroup': space_group,
                                   'cell': cell,
                                   'inverse_beam': inverse_beam})

        try:
            #TODO move this to AutoProcessing hwobj
            programs = self.beamline_setup.collect_hwobj["auto_processing"]
        except IndexError:
            # skip autoprocessing of the data
            pass
        else:
            autoprocessing.start(programs, "end_multicollect", params)

        self._set_background_color()
        self._view.setText(1, "")

    def _set_background_color(self):
        BaseQueueEntry._set_background_color(self)

    def get_type_str(self):
        return "Sample"

class BasketQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)

class SampleCentringQueueEntry(BaseQueueEntry):
    """
    Entry for centring a sample
    """
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.sample_changer_hwobj = None
        self.diffractometer_hwobj = None
        self.shape_history = None

    def __getstate__(self):
        d = dict(self.__dict__)
        return d
 
    def __setstate__(self, d):
        self.__dict__.update(d)

    def execute(self):
        BaseQueueEntry.execute(self)

        self.get_view().setText(1, 'Waiting for input')
        log = logging.getLogger("user_level_log")

        kappa = self._data_model.get_kappa()
        phi = self._data_model.get_kappa_phi()

        if hasattr(self.diffractometer_hwobj, "in_kappa_mode") and self.diffractometer_hwobj.in_kappa_mode():
            self.diffractometer_hwobj.moveMotors({"kappa": kappa, "kappa_phi":phi})

        #TODO agree on correct message
        log.warning("Please center a new point, and press continue.")
        #log.warning("Please select a centred position, and press continue.")

        self.get_queue_controller().pause(True)
        pos = None

        if len(self.shape_history.get_selected_shapes()):
            pos = self.shape_history.get_selected_shapes()[0]
        else:
            msg = "No centred position selected, using current position."
            log.info(msg)

            # Create a centred postions of the current postion
            pos_dict = self.diffractometer_hwobj.getPositions()
            cpos = queue_model_objects.CentredPosition(pos_dict)
            #pos = shape_history.Point(None, cpos, None) #, True)

        # Get tasks associated with this centring
        tasks = self.get_data_model().get_tasks()

        """for task in tasks:
            cpos = pos.get_centred_positions()[0]

            if pos.qub_point is not None:
                snapshot = self.shape_history.\
                           get_snapshot([pos.qub_point])
            else:
                snapshot = self.shape_history.get_snapshot([])

            cpos.snapshot_image = snapshot 
            task.set_centred_positions(cpos)"""

        self.get_view().setText(1, 'Input accepted')

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self.sample_changer_hwobj = self.beamline_setup.sample_changer_hwobj
        self.diffractometer_hwobj = self.beamline_setup.diffractometer_hwobj
        self.shape_history = self.beamline_setup.shape_history_hwobj

    def post_execute(self):
        #If centring is executed once then we dont have to execute it again
        self.get_view().set_checkable(False)
        BaseQueueEntry.post_execute(self)

    def get_type_str(self):
        return "Sample centering"


class DataCollectionQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """
    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)

        self.collect_hwobj = None
        self.diffractometer_hwobj = None
        self.collect_task = None
        self.centring_task = None
        self.shape_history = None
        self.session = None
        self.lims_client_hwobj = None
        self.enable_take_snapshots = True
        self.enable_store_in_lims = True
        self.in_queue = False 

        self.parallel_processing_hwobj = None

    def __getstate__(self):
        d = dict(self.__dict__)
        d["collect_task"] = None
        d["centring_task"] = None
        return d
 
    def __setstate__(self, d):
        self.__dict__.update(d)


    def __getstate__(self):
        d = dict(self.__dict__)
        d["collect_task"] = None
        d["centring_task"] = None
        return d
 
    def __setstate__(self, d):
        self.__dict__.update(d)


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
        self.parallel_processing_hwobj = self.beamline_setup.parallel_processing_hwobj

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

        if self.parallel_processing_hwobj is not None:
            qc.connect(self.parallel_processing_hwobj, 'paralleProcessingResults',
                       self.processing_set_result)
            qc.connect(self.parallel_processing_hwobj, 'processingFinished',
                       self.processing_finished)
            qc.connect(self.parallel_processing_hwobj, 'processingFailed',
                       self.processing_failed)

        data_model = self.get_data_model()

        if data_model.get_parent():
            gid = data_model.get_parent().lims_group_id
            data_model.lims_group_id = gid

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

        if self.parallel_processing_hwobj is not None:
            qc.disconnect(self.parallel_processing_hwobj, 'paralleProcessingResults',
                       self.processing_set_result)
            qc.disconnect(self.parallel_processing_hwobj, 'processingFinished',
                       self.processing_finished)
            qc.disconnect(self.parallel_processing_hwobj, 'processingFailed',
                       self.processing_failed)

        self.get_view().set_checkable(False)

    def collect_dc(self, dc, list_item):
        log = logging.getLogger("user_level_log")

        if self.collect_hwobj:
            acq_1 = dc.acquisitions[0]
            acq_1.acquisition_parameters.in_queue = self.in_queue
            cpos = acq_1.acquisition_parameters.centred_position
            sample = self.get_data_model().get_parent().get_parent()
            self.collect_hwobj.run_processing_after = dc.run_processing_after
            self.collect_hwobj.aborted_by_user = None
            self.processing_task = None

            try:
                if dc.experiment_type is EXPERIMENT_TYPE.HELICAL:
                    acq_1, acq_2 = (dc.acquisitions[0], dc.acquisitions[1])
                    self.collect_hwobj.set_helical(True)
                    self.collect_hwobj.set_mesh(False)

                    start_cpos = acq_1.acquisition_parameters.centred_position
                    end_cpos = acq_2.acquisition_parameters.centred_position

                    helical_oscil_pos = {'1': start_cpos.as_dict(), '2': end_cpos.as_dict() }
                    self.collect_hwobj.set_helical_pos(helical_oscil_pos)
                    #msg = "Helical data collection, moving to start position"
                    #log.info(msg)
                    #list_item.setText(1, "Moving sample")

                elif dc.experiment_type is EXPERIMENT_TYPE.MESH:
                    mesh_nb_lines = acq_1.acquisition_parameters.num_lines
                    mesh_total_nb_frames = acq_1.acquisition_parameters.num_images
                    mesh_range = acq_1.acquisition_parameters.mesh_range
                    mesh_center = acq_1.acquisition_parameters.centred_position
                    self.collect_hwobj.set_mesh_scan_parameters(mesh_nb_lines, mesh_total_nb_frames, mesh_center, mesh_range)
                    self.collect_hwobj.set_helical(False)
                    self.collect_hwobj.set_mesh(True)
                else:
                    self.collect_hwobj.set_helical(False)
                    self.collect_hwobj.set_mesh(False)

                if dc.run_processing_parallel and \
                   self.parallel_processing_hwobj is not None:
                      self.processing_task = gevent.spawn(\
                           self.parallel_processing_hwobj.run_processing,
                           dc)    

                empty_cpos = queue_model_objects.CentredPosition()

                if cpos != empty_cpos:
                    self.shape_history.select_shape_with_cpos(cpos)
                else:
                    pos_dict = self.diffractometer_hwobj.getPositions()
                    cpos = queue_model_objects.CentredPosition(pos_dict)
                    snapshot = self.shape_history.get_snapshot([])
                    acq_1.acquisition_parameters.centred_position = cpos
                    acq_1.acquisition_parameters.centred_position.snapshot_image = snapshot

                self.shape_history.inc_used_for_collection(cpos)

                param_list = queue_model_objects.to_collect_dict(dc, self.session, sample, cpos if cpos!=empty_cpos else None)
               
                self.collect_task = self.collect_hwobj.\
                    collect(COLLECTION_ORIGIN_STR.MXCUBE, param_list)                
                self.collect_task.get()
                #TODO as a gevent task?
                #self.collect_task = gevent.spawn(self.collect_hwobj.collect,
                #             COLLECTION_ORIGIN_STR.MXCUBE,
                #             param_list)
                #self.collect_task.get()
                #self.collect_hwobj.ready_event.wait()
                #self.collect_hwobj.ready_event.clear()


                if 'collection_id' in param_list[0]:
                    dc.id = param_list[0]['collection_id']

                dc.acquisitions[0].path_template.xds_dir = param_list[0]['xds_dir']

            except gevent.GreenletExit:
                #log.warning("Collection stopped by user.")
                list_item.setText(1, 'Stopped')
                raise QueueAbortedException('queue stopped by user', self)
            except Exception as ex:
                #print (traceback.print_exc())
                raise QueueExecutionException(ex.message, self)
        else:
            log.error("Could not call the data collection routine," +\
                      " check the beamline configuration")
            list_item.setText(1, 'Failed')
            msg = "Could not call the data collection" +\
                  " routine, check the beamline configuration"
            raise QueueExecutionException(msg, self)

    def collect_started(self, owner, num_oscillations):
        logging.getLogger("user_level_log").info('Collection started')
        self.get_view().setText(1, "Collecting")

    def collect_number_of_frames(self, number_of_images=0, exposure_time=0):
        pass

    def image_taken(self, image_number):
        if image_number > 0:
            num_images = self.get_data_model().acquisitions[0].\
                         acquisition_parameters.num_images
            num_images += self.get_data_model().acquisitions[0].\
                          acquisition_parameters.first_image - 1
            self.get_view().setText(1, str(image_number) + "/" + str(num_images))

    def preparing_collect(self, number_images=0, exposure_time=0):
        self.get_view().setText(1, "Collecting")

    def collect_failed(self, owner, state, message, *args):
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        self.get_view().setText(1, "Failed")
        self.status = QUEUE_ENTRY_STATUS.FAILED
        logging.getLogger("queue_exec").error(message.replace('\n', ' '))
        raise QueueExecutionException(message.replace('\n', ' '), self)

    def collect_osc_started(self, owner, blsampleid, barcode, location,
                            collect_dict, osc_id):
        self.get_view().setText(1, "Preparing")

    def collect_finished(self, owner, state, message, *args):
        # this is to work around the remote access problem

        if self.processing_task:
            self.get_view().setText(1, "Processing")
            self.parallel_processing_hwobj.processing_done_event.wait()
            self.parallel_processing_hwobj.processing_done_event.clear()

        dispatcher.send("collect_finished")
        self.get_view().setText(1, "Collection done")
        logging.getLogger("user_level_log").info('Collection finished')

    def stop(self):
        BaseQueueEntry.stop(self)

        try:
            self.collect_hwobj.stopCollect('mxCuBE')
            if self.processing_task:
                self.parallel_processing_hwobj.stop_processing()
            if self.centring_task:
                self.centring_task.kill(block=False)
        except gevent.GreenletExit:
            raise

        self.get_view().setText(1, 'Stopped')
        logging.getLogger('queue_exec').info('Calling stop on: ' + str(self))
        logging.getLogger('user_level_log').error('Collection: Stoppend')
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        raise QueueAbortedException('Queue stopped', self)

    def processing_set_result(self, result_dict, info_dict, last_result):
        data_model = self.get_data_model()
        data_model.parallel_processing_result = result_dict

    def processing_finished(self):
        dispatcher.send("collect_finished")
        self.processing_task = None
        self.get_view().setText(1, "Processing done")
        logging.getLogger("user_level_log").info('Processing done')

    def processing_failed(self):
        self.processing_task = None
        self.get_view().setText(1, "Processing failed")
        logging.getLogger("user_level_log").error('Processing failed')

    def get_type_str(self):
        data_model = self.get_data_model()
        if data_model.is_helical():
            return "Helical"
        elif data_model.is_mesh():
            return "Mesh"
        else:
            return "OSC"
            

class CharacterisationGroupQueueEntry(BaseQueueEntry):
    """
    Used to group (couple) a CollectionQueueEntry and a
    CharacterisationQueueEntry, creating a virtual entry for characterisation.
    """
    def __init__(self, view=None, data_model=None,
                 view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)
        self.dc_qe = None
        self.char_qe = None
        self.in_queue = False

    def execute(self):
        BaseQueueEntry.execute(self)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        char = self.get_data_model()
        reference_image_collection = char.reference_image_collection

        # Trick to make sure that the reference collection has a sample.
        reference_image_collection._parent = char.get_parent()

        gid = self.get_data_model().get_parent().lims_group_id
        reference_image_collection.lims_group_id = gid

        # Enqueue the reference collection and the characterisation routine.
        dc_qe = DataCollectionQueueEntry(self.get_view(),
                                         reference_image_collection,
                                         view_set_queue_entry=False)
        dc_qe.set_enabled(True)
        dc_qe.in_queue = self.in_queue
        self.enqueue(dc_qe)
        self.dc_qe = dc_qe

        if char.run_characterisation:
            char_qe = CharacterisationQueueEntry(self.get_view(), char,
                                                 view_set_queue_entry=False)
            char_qe.set_enabled(True)
            self.enqueue(char_qe)
            self.char_qe = char_qe

    def post_execute(self):
        if self.char_qe: 
            self.status = self.char_qe.status
        else:
            self.status = self.dc_qe.status
        BaseQueueEntry.post_execute(self)


class CharacterisationQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a characterisation
    """
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
        log = logging.getLogger("queue_exec")

        self.get_view().setText(1, "Characterising")
        log.info("Characterising, please wait ...")
        char = self.get_data_model()
        reference_image_collection = char.reference_image_collection
        characterisation_parameters = char.characterisation_parameters

        if self.data_analysis_hwobj is not None:
            edna_input = self.data_analysis_hwobj.\
                         from_params(reference_image_collection,
                                     characterisation_parameters)
            #Un-comment to use the test input files
            #edna_input = XSDataInputMXCuBE.parseString(edna_test_data.EDNA_TEST_DATA)
            #edna_input.process_directory = reference_image_collection.acquisitions[0].\
            #                                path_template.process_directory

            self.edna_result = self.data_analysis_hwobj.characterise(edna_input)

        if self.edna_result:
            log.info("Characterisation completed.")

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
                log.warning("Characterisation completed " +\
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
        #should be an other way how to get queue_model_hwobj:
        self.queue_model_hwobj = self.get_view().listView().\
             parent().queue_model_hwobj
        
        self.session_hwobj = self.beamline_setup.session_hwobj

    def post_execute(self):
        BaseQueueEntry.post_execute(self)

    def get_type_str(self):
        return "Characterisation"

class EnergyScanQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.energy_scan_hwobj = None
        self.session_hwobj = None
        self.energy_scan_task = None
        self._failed = False

    def __getstate__(self):
        d = dict(self.__dict__)
        d["energy_scan_task"] = None
        return d
 
    def __setstate__(self, d):
        self.__dict__.update(d)


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

        self.energy_scan_hwobj.ready_event.wait()
        self.energy_scan_hwobj.ready_event.clear()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self._failed = False
        self.energy_scan_hwobj = self.beamline_setup.energyscan_hwobj
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
        self.get_view().set_checkable(False)

    def energy_scan_status_changed(self, msg):
        logging.getLogger("user_level_log").info(msg)

    def energy_scan_started(self, *arg):
        logging.getLogger("user_level_log").info("Energy scan started.")
        self.get_view().setText(1, "In progress")

    def energy_scan_finished(self, scan_info):
        energy_scan = self.get_data_model()
        #fname = "_".join((energy_scan.path_template.get_prefix(),str(energy_scan.path_template.run_number)))
        #scan_file_path = os.path.join(energy_scan.path_template.directory,
        #                              fname)
        #scan_file_path = os.path.join(energy_scan.path_template.directory,
        #                              energy_scan.path_template.get_prefix())

        #scan_file_archive_path = os.path.join(energy_scan.path_template.\
        #                                      get_archive_directory(),
        #                                      energy_scan.path_template.get_prefix())

        (pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, rm,
         chooch_graph_x, chooch_graph_y1, chooch_graph_y2, title) = \
         self.energy_scan_hwobj.doChooch(energy_scan.element_symbol,
                                         energy_scan.edge,
                                         energy_scan.path_template.directory,
                                         energy_scan.path_template.get_archive_directory(),
                                         "%s_%d" %(energy_scan.path_template.get_prefix(),
                                         energy_scan.path_template.run_number))     
                                         #scan_file_archive_path,
                                         #scan_file_path)

        #scan_info = self.energy_scan_hwobj.scanInfo

        # This does not always apply, update model so
        # that its possible to access the sample directly from
        # the EnergyScan object.
        sample = self.get_view().parent().parent().get_model()
        sample.crystals[0].energy_scan_result.peak = pk
        sample.crystals[0].energy_scan_result.inflection = ip
        sample.crystals[0].energy_scan_result.first_remote = rm
        sample.crystals[0].energy_scan_result.second_remote = None

        energy_scan.result.pk = pk
        energy_scan.result.fppPeak = fppPeak
        energy_scan.result.fpPeak = fpPeak
        energy_scan.result.ip = ip
        energy_scan.result.fppInfl = fppInfl
        energy_scan.result.fpInfl = fpInfl
        energy_scan.result.rm = rm
        energy_scan.result.chooch_graph_x = chooch_graph_x
        energy_scan.result.chooch_graph_y1 = chooch_graph_y1
        energy_scan.result.chooch_graph_y2 = chooch_graph_y2
        energy_scan.result.title = title
        try:
            energy_scan.result.data = self.energy_scan_hwobj.get_scan_data()
        except:
            pass

        logging.getLogger("user_level_log").\
            info("Energy scan, result: peak: %.4f, inflection: %.4f" %
                 (sample.crystals[0].energy_scan_result.peak,
                  sample.crystals[0].energy_scan_result.inflection))

        self.get_view().setText(1, "Done")

    def energy_scan_failed(self):
        self._failed = True
        self.get_view().setText(1, "Failed")
        self.status = QUEUE_ENTRY_STATUS.FAILED
        logging.getLogger("user_level_log").error("Energy scan failed.")
        raise QueueExecutionException("Energy scan failed", self)

    def stop(self):
        BaseQueueEntry.stop(self)

        try:
            #self.get_view().setText(1, 'Stopping ...')
            self.energy_scan_hwobj.cancelEnergyScan()

            if self.centring_task:
                self.centring_task.kill(block=False)
        except gevent.GreenletExit:
            raise

        self.get_view().setText(1, 'Stopped')
        logging.getLogger('queue_exec').info('Calling stop on: ' + str(self))
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        raise QueueAbortedException('Queue stopped', self)

    def get_type_str(self):
        return "Energy scan"

class XRFSpectrumQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.xrf_spectrum_hwobj = None
        self.session_hwobj = None
        self._failed = False
  
    def __getstate__(self):
        d = dict(self.__dict__)
        d["xrf_spectrum_task"] = None
        return d
 
    def __setstate__(self, d):
        self.__dict__.update(d)

    def execute(self):
        BaseQueueEntry.execute(self)

        if self.xrf_spectrum_hwobj is not None:
            xrf_spectrum = self.get_data_model()
            self.get_view().setText(1, "Starting xrf spectrum")

            sample_model = self.get_data_model().\
                           get_parent().get_parent()

            sample_lims_id = sample_model.lims_id
            # No sample id, pass None to startEnergySpectrum
            if sample_lims_id == -1:
                sample_lims_id = None

            self.xrf_spectrum_hwobj.startXrfSpectrum(
                             xrf_spectrum.count_time,
                             xrf_spectrum.path_template.directory,
                             xrf_spectrum.path_template.get_archive_directory(),
                             "%s_%d" % (xrf_spectrum.path_template.get_prefix(),
                                        xrf_spectrum.path_template.run_number),
                             self.session_hwobj.session_id,
                             sample_lims_id,
                             xrf_spectrum.adjust_transmission)
            self.xrf_spectrum_hwobj.ready_event.wait()
            self.xrf_spectrum_hwobj.ready_event.clear()
        else:
            logging.getLogger("user_level_log").info("XRFSpectrum not defined in beamline setup")
            self.xrf_spectrum_failed()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self._failed = False
        self.xrf_spectrum_hwobj = self.beamline_setup.xrf_spectrum_hwobj
        self.session_hwobj = self.beamline_setup.session_hwobj
        qc = self.get_queue_controller()
        qc.connect(self.xrf_spectrum_hwobj, 'xrfSpectrumStatusChanged',
                   self.xrf_spectrum_status_changed)

        qc.connect(self.xrf_spectrum_hwobj, 'xrfSpectrumStarted',
                   self.xrf_spectrum_started)
        qc.connect(self.xrf_spectrum_hwobj, 'xrfSpectrumFinished',
                   self.xrf_spectrum_finished)
        qc.connect(self.xrf_spectrum_hwobj, 'xrfSpectrumFailed',
                   self.xrf_spectrum_failed)

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        qc = self.get_queue_controller()
        qc.disconnect(self.xrf_spectrum_hwobj, 'xrfSpectrumStatusChanged',
                      self.xrf_spectrum_status_changed)

        qc.disconnect(self.xrf_spectrum_hwobj, 'xrfSpectrumStarted',
                      self.xrf_spectrum_started)

        qc.disconnect(self.xrf_spectrum_hwobj, 'xrfSpectrumFinished',
                      self.xrf_spectrum_finished)

        qc.disconnect(self.xrf_spectrum_hwobj, 'xrfSpectrumFailed',
                      self.xrf_spectrum_failed)
        if self._failed:
            raise QueueAbortedException('Queue stopped', self)
        self.get_view().set_checkable(False)

    def xrf_spectrum_status_changed(self, msg):
        logging.getLogger("user_level_log").info(msg)

    def xrf_spectrum_started(self):
        logging.getLogger("user_level_log").info("XRF spectrum started.")
        self.get_view().setText(1, "In progress")

    def xrf_spectrum_finished(self, mcaData, mcaCalib, mcaConfig):
        xrf_spectrum = self.get_data_model()
        spectrum_file_path = os.path.join(xrf_spectrum.path_template.directory,
                                      xrf_spectrum.path_template.get_prefix())
        spectrum_file_archive_path = os.path.join(xrf_spectrum.path_template.\
                                              get_archive_directory(),
                                              xrf_spectrum.path_template.get_prefix())

        xrf_spectrum.result.mca_data = mcaData
        xrf_spectrum.result.mca_calib = mcaCalib
        xrf_spectrum.result.mca_config = mcaConfig

        logging.getLogger("user_level_log").info("XRF spectrum finished.")
        self.get_view().setText(1, "Done")

    def xrf_spectrum_failed(self):
        self._failed = True
        self.get_view().setText(1, "Failed")
        self.status = QUEUE_ENTRY_STATUS.FAILED
        logging.getLogger("user_level_log").error("XRF spectrum failed.")
        raise QueueExecutionException("XRF spectrum failed", self)

    def get_type_str(self):
        return "XRF spectrum"

class GenericWorkflowQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.rpc_server_hwobj = None
        self.workflow_hwobj = None
        self.workflow_running = False
        self.workflow_started = False

    def execute(self):
        BaseQueueEntry.execute(self)
        
        # Start execution of a new workflow
        if str(self.workflow_hwobj.state.value) != 'ON':
            # We are trying to start a new workflow and the Tango server is not idle,
            # therefore first abort any running workflow: 
            self.workflow_hwobj.abort()
            if self.workflow_hwobj.command_failure():
                msg = "Workflow abort command failed! Please check workflow Tango server."
                logging.getLogger("user_level_log").error(msg)
            else:
                # Then sleep three seconds for allowing the server to abort a running workflow:
                time.sleep(3)
                # If the Tango server has been restarted the state.value is None.
                # If not wait till the state.value is "ON":
                if self.workflow_hwobj.state.value is not None:
                    while str(self.workflow_hwobj.state.value) != 'ON':
                        time.sleep(0.5)

        msg = "Starting workflow (%s), please wait." % (self.get_data_model()._type)
        logging.getLogger("user_level_log").info(msg)
        workflow_params = self.get_data_model().params_list
        # Add the current node id to workflow parameters
        #group_node_id = self._parent_container._data_model._node_id
        #workflow_params.append("group_node_id")
        #workflow_params.append("%d" % group_node_id)
        self.workflow_hwobj.start(workflow_params)
        if self.workflow_hwobj.command_failure():
            msg = "Workflow start command failed! Please check workflow Tango server."
            logging.getLogger("user_level_log").error(msg)
            self.workflow_running = False
        else:
            self.workflow_running = True
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
            msg = "Workflow waiting for input, verify parameters and press continue."
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

class XrayCenteringQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of an Advanced scan
    """
    def __init__(self, view=None, data_model=None,
                 view_set_queue_entry=True):

        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)
        self.mesh_qe = None
        self.helical_qe = None
        self.in_queue = False

    def execute(self):
        BaseQueueEntry.execute(self)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        mesh = self.get_data_model()
        reference_image_collection = mesh.reference_image_collection

        # Trick to make sure that the reference collection has a sample.
        reference_image_collection._parent = mesh.get_parent()

        gid = self.get_data_model().get_parent().lims_group_id
        reference_image_collection.lims_group_id = gid

        # Enqueue the reference collection and the characterisation routine.
        mesh_qe = DataCollectionQueueEntry(self.get_view(),
                                         reference_image_collection,
                                         view_set_queue_entry=False)
        mesh_qe.set_enabled(True)
        mesh_qe.in_queue = self.in_queue
        self.enqueue(mesh_qe)
        self.mesh_qe = mesh_qe

        #if char.run_characterisation:
        #    char_qe = CharacterisationQueueEntry(self.get_view(), char,
        #                                         view_set_queue_entry=False)
        #    char_qe.set_enabled(True)
        #    self.enqueue(char_qe)
        #    self.char_qe = char_qe

    def post_execute(self):
        if self.helical_qe:
            self.status = self.helical_qe.status
        else:
            self.status = self.mesh_qe
        BaseQueueEntry.post_execute(self)

class OpticalCentringQueueEntry(BaseQueueEntry):
    """
    Entry for automatic sample centring with lucid
    """
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.diffractometer_hwobj = None

    def execute(self):
        BaseQueueEntry.execute(self)
        self.diffractometer_hwobj.automatic_centring_try_count = \
             self.get_data_model().try_count
 
        self.diffractometer_hwobj.start_automatic_centring(wait_result=True)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self.diffractometer_hwobj = self.beamline_setup.diffractometer_hwobj

    def post_execute(self):
        self.get_view().set_checkable(False)
        BaseQueueEntry.post_execute(self)

    def get_type_str(self):
        return "Optical automatic centering"

def mount_sample(beamline_setup_hwobj,
                 view, data_model,
                 centring_done_cb, async_result):
    view.setText(1, "Loading sample")
    beamline_setup_hwobj.shape_history_hwobj.clear_all()
    log = logging.getLogger("queue_exec")

    loc = data_model.location
    holder_length = data_model.holder_length

    # This is a possible solution how to deal with two devices that
    # can move sample on beam (sample changer, plate holder, in future 
    # also harvester)
    # TODO make sample_Changer_one, sample_changer_two
    if beamline_setup_hwobj.diffractometer_hwobj.in_plate_mode():
        sample_mount_device = beamline_setup_hwobj.plate_manipulator_hwobj
    else:
        sample_mount_device = beamline_setup_hwobj.sample_changer_hwobj

    if hasattr(sample_mount_device, '__TYPE__'):
        if sample_mount_device.__TYPE__ in ['Marvin','CATS']:
            element = '%d:%02d' % loc
            sample_mount_device.load(sample=element, wait=True)
        elif sample_mount_device.__TYPE__ == "PlateManipulator": 
            sample_mount_device.load_sample(sample_location=loc)
        else:
            if sample_mount_device.load_sample(holder_length, sample_location=loc, wait=True) == False:
                # WARNING: explicit test of False return value.
                # This is to preserve backward compatibility (load_sample was supposed to return None);
                # if sample could not be loaded, but no exception is raised, let's skip the sample
                raise QueueSkippEntryException("Sample changer could not load sample", "")

    if not sample_mount_device.hasLoadedSample():
        #Disables all related collections
        view.setOn(False)
        view.setText(1, "Sample not loaded")
        raise QueueSkippEntryException("Sample not loaded", "")
    else:
        view.setText(1, "Sample loaded")
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
                elif centring_method == CENTRING_METHOD.FULLY_AUTOMATIC:
                    log.info("Centring sample, please wait.")
                    dm.startCentringMethod(dm.C3D_MODE)
                else:
                    dm.startCentringMethod(dm.MANUAL3CLICK_MODE)

                view.setText(1, "Centring !")
                centring_result = async_result.get()
                if centring_result['valid']: 
                    view.setText(1, "Centring done !")
                    log.info("Centring saved")
                else:
                    if centring_method == CENTRING_METHOD.FULLY_AUTOMATIC:
                        raise QueueSkippEntryException("Could not center sample, skipping", "")
                    else:
                        raise RuntimeError("Could not center sample")
            except:
                pass
            finally:
                dm.disconnect("centringAccepted", centring_done_cb)

MODEL_QUEUE_ENTRY_MAPPINGS = \
    {queue_model_objects.DataCollection: DataCollectionQueueEntry,
     queue_model_objects.Characterisation: CharacterisationGroupQueueEntry,
     queue_model_objects.EnergyScan: EnergyScanQueueEntry,
     queue_model_objects.XRFSpectrum: XRFSpectrumQueueEntry,
     queue_model_objects.SampleCentring: SampleCentringQueueEntry,
     queue_model_objects.OpticalCentring: OpticalCentringQueueEntry,
     queue_model_objects.Sample: SampleQueueEntry,
     queue_model_objects.Basket: BasketQueueEntry,
     queue_model_objects.TaskGroup: TaskGroupQueueEntry,
     queue_model_objects.Workflow: GenericWorkflowQueueEntry,
     queue_model_objects.XrayCentering: XrayCenteringQueueEntry}
