#  Project: MXCuBE
#  https://github.com/mxcube
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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
All queue entries inherits the baseclass BaseQueueEntry which in turn
inherits QueueEntryContainer. This makes it possible to arrange and
execute queue entries in a hierarchical manner.
"""

import sys
import traceback
import time
import gevent
import copy

from collections import namedtuple

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model import queue_model_objects
from mxcubecore.model.queue_model_enumerables import CENTRING_METHOD, EXPERIMENT_TYPE

from mxcubecore.HardwareObjects import autoprocessing

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


status_list = ["SUCCESS", "WARNING", "FAILED", "SKIPPED", "RUNNING", "NOT_EXECUTED"]
QueueEntryStatusType = namedtuple("QueueEntryStatusType", status_list)
QUEUE_ENTRY_STATUS = QueueEntryStatusType(0, 1, 2, 3, 4, 5)


class QueueExecutionException(Exception):
    def __init__(self, message, origin):
        Exception.__init__(self, message, origin)
        self.message = message
        self.origin = origin
        if sys.exc_info()[0] is None:
            self.stack_trace = None
        else:
            self.stack_trace = traceback.format_exc()


class QueueAbortedException(QueueExecutionException):
    pass


class QueueSkipEntryException(QueueExecutionException):
    pass


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

    def enqueue(self, queue_entry):
        # A queue entry container has a QueueController object
        # which controls the execution of the tasks in the
        # container. QueueManagers are their own controller.
        # These are set in subclasses
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

        log = logging.getLogger("queue_exec")
        msg = "dequeue called with: " + str(queue_entry)
        log.info(msg)

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
            self._queue_entry_list[index_a] = self._queue_entry_list[index_b]
            self._queue_entry_list[index_b] = temp

        log = logging.getLogger("queue_exec")
        msg = "swap called with: " + str(queue_entry_a) + ", " + str(queue_entry_b)
        log.info(msg)

        msg = "Queue is :" + str(self.get_queue_controller())
        log.info(msg)

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

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        QueueEntryContainer.__init__(self)
        self._data_model = None
        self._view = None
        self.set_data_model(data_model)
        self.set_view(view, view_set_queue_entry)
        self._checked_for_exec = False
        self.status = QUEUE_ENTRY_STATUS.NOT_EXECUTED
        self.type_str = ""

    def is_failed(self):
        """Returns True if failed"""
        return self.status == QUEUE_ENTRY_STATUS.FAILED

    def enqueue(self, queue_entry):
        """
        Method inherited from QueueEntryContainer, a derived class
        should newer need to override this method.
        """
        queue_entry.set_queue_controller(self.get_queue_controller())
        super(BaseQueueEntry, self).enqueue(queue_entry)

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
        msg = "Calling execute on: " + str(self)
        logging.getLogger("queue_exec").info(msg)

    def pre_execute(self):
        """
        Procedure to be done before execute.
        """
        msg = "Calling pre_execute on: " + str(self)
        logging.getLogger("queue_exec").info(msg)
        self.get_data_model().set_running(True)

    def post_execute(self):
        """
        Procedure to be done after execute, and execute of all
        children of this entry.
        """
        msg = "Calling post_execute on: " + str(self)
        logging.getLogger("queue_exec").info(msg)

        # view = self.get_view()
        # view.setHighlighted(True)
        # view.setOn(False)

        self.get_data_model().set_executed(True)
        self.get_data_model().set_running(False)
        self.get_data_model().set_enabled(False)
        self.set_enabled(False)

        # self._set_background_color()

    def _set_background_color(self):
        view = self.get_view()

        if self.get_data_model().is_executed():
            view.set_background_color(self.status + 1)
        else:
            view.set_background_color(0)
            # view.setBackgroundColor(widget_colors.WHITE)

    def stop(self):
        """
        Stops the execution of this entry, should free
        external resources, cancel all pending processes and so on.
        """
        self.get_view().setText(1, "Stopped")
        msg = "Calling stop on: " + str(self)
        logging.getLogger("queue_exec").info(msg)

    def handle_exception(self, ex):
        view = self.get_view()

        if view and isinstance(ex, QueueExecutionException):
            if ex.origin is self:
                # view.setBackgroundColor(widget_colors.LIGHT_RED)
                view.set_background_color(3)

    def __str__(self):
        info_str = "<%s object at %s> [" % (self.__class__.__name__, hex(id(self)))

        for entry in self._queue_entry_list:
            info_str += str(entry)

        return info_str + "]"

    def get_type_str(self):
        return self.type_str


class TaskGroupQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)

        self.interleave_task = None
        self.interleave_items = None
        self.interleave_sw_list = None
        self.interleave_stopped = None

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
            from mxcubecore.queue_entry.generic_workflow import (
                GenericWorkflowQueueEntry,
            )

            if isinstance(self._queue_entry_list[0], GenericWorkflowQueueEntry):
                do_new_dc_group = False

        init_ref_images = False
        if do_new_dc_group:
            # Creating a collection group with the current session id
            # and a dummy exepriment type OSC. The experiment type
            # will be updated when the collections are stored.
            if task_model.interleave_num_images:
                init_ref_images = task_model.interleave_num_images
                group_data = {
                    "sessionId": HWR.beamline.session.session_id,
                    "experimentType": "Collect - Multiwedge",
                }
            elif task_model.inverse_beam_num_images:
                init_ref_images = task_model.inverse_beam_num_images
                group_data = {
                    "sessionId": HWR.beamline.session.session_id,
                    "experimentType": "Collect - Multiwedge",
                }
            else:
                group_data = {
                    "sessionId": HWR.beamline.session.session_id,
                    "experimentType": "OSC",
                }

            sample_model = task_model.get_sample_node()
            task_model.get_parent()
            if sample_model.lims_container_location != -1:
                loc = sample_model.lims_container_location

                if isinstance(loc, str):
                    cell, puck = list(map(int, "2:2".split(":")))
                    loc = (cell - 1) * 3 + puck

                group_data["actualContainerSlotInSC"] = loc
            if sample_model.lims_sample_location != -1:
                group_data["actualSampleSlotInContainer"] = int(
                    sample_model.lims_sample_location
                )

            try:
                gid = HWR.beamline.lims._store_data_collection_group(group_data)
                self.get_data_model().lims_group_id = gid
            except Exception as ex:
                msg = (
                    "Could not create the data collection group"
                    + " in LIMS. Reason: "
                    + str(ex)
                )
                raise QueueExecutionException(msg, self)

        self.interleave_items = []
        if init_ref_images:
            # At first all children are gathered together and
            # checked if interleave is set. For this implementation
            # interleave is just possible for discreet data collections
            ref_num_images = 0
            children_data_model_list = self._data_model.get_children()

            for child_data_model in children_data_model_list:
                if isinstance(child_data_model, queue_model_objects.DataCollection):
                    if task_model.inverse_beam_num_images is not None:
                        child_data_model.acquisitions[
                            0
                        ].acquisition_parameters.num_images /= 2
                    num_images = child_data_model.acquisitions[
                        0
                    ].acquisition_parameters.num_images

                    if num_images > init_ref_images:
                        if num_images > ref_num_images:
                            ref_num_images = num_images
                        interleave_item = {}
                        child_data_model.set_experiment_type(
                            EXPERIMENT_TYPE.COLLECT_MULTIWEDGE
                        )
                        interleave_item["data_model"] = child_data_model
                        for queue_entry in self._queue_entry_list:
                            if queue_entry.get_data_model() == child_data_model:
                                interleave_item["queue_entry"] = queue_entry
                                interleave_item["tree_item"] = queue_entry.get_view()
                        self.interleave_items.append(interleave_item)

                        if task_model.inverse_beam_num_images is not None:
                            inverse_beam_item = copy.deepcopy(interleave_item)
                            inverse_beam_item["data_model"] = interleave_item[
                                "data_model"
                            ].copy()
                            inverse_beam_item["data_model"].acquisitions[
                                0
                            ].acquisition_parameters.osc_start += 180
                            inverse_beam_item["data_model"].acquisitions[
                                0
                            ].acquisition_parameters.first_image = (
                                interleave_item["data_model"]
                                .acquisitions[0]
                                .acquisition_parameters.first_image
                                + interleave_item["data_model"]
                                .acquisitions[0]
                                .acquisition_parameters.num_images
                            )
                            self.interleave_items.append(inverse_beam_item)
        if len(self.interleave_items) > 1:
            interleave_num_images = task_model.interleave_num_images
            self.interleave_task = gevent.spawn(
                self.execute_interleaved, ref_num_images, init_ref_images
            )
            self.interleave_task.join()

    def execute_interleaved(self, ref_num_images, interleave_num_images):
        task_model = self.get_data_model()

        if task_model.interleave_num_images:
            method_type = "interleave"
        elif task_model.inverse_beam_num_images:
            method_type = "inverse beam"

        logging.getLogger("queue_exec").info(
            "Preparing %s data collection" % method_type
        )

        for interleave_item in self.interleave_items:
            interleave_item["queue_entry"].set_enabled(False)
            interleave_item["tree_item"].set_checkable(False)
            interleave_item["data_model"].lims_group_id = (
                interleave_item["data_model"].get_parent().lims_group_id
            )
            cpos = (
                interleave_item["data_model"]
                .acquisitions[0]
                .acquisition_parameters.centred_position
            )
            # sample = interleave_item["data_model"].get_parent().get_parent()
            sample = interleave_item["data_model"].get_sample_node()
            empty_cpos = queue_model_objects.CentredPosition()
            param_list = queue_model_objects.to_collect_dict(
                interleave_item["data_model"],
                HWR.beamline.session,
                sample,
                cpos if cpos != empty_cpos else None,
            )
            # HWR.beamline.collect.prepare_interleave(
            #    interleave_item["data_model"], param_list
            # )

        self.interleave_sw_list = queue_model_objects.create_interleave_sw(
            self.interleave_items, ref_num_images, interleave_num_images
        )

        self._queue_controller.emit("queue_interleaved_started")
        for item_index, item in enumerate(self.interleave_sw_list):
            if not self.interleave_stopped:
                self.get_view().setText(
                    1,
                    "Subwedge %d:%d)"
                    % ((item_index + 1), len(self.interleave_sw_list)),
                )

                acq_par = (
                    self.interleave_items[item["collect_index"]]["data_model"]
                    .acquisitions[0]
                    .acquisition_parameters
                )

                acq_path_template = (
                    self.interleave_items[item["collect_index"]]["data_model"]
                    .acquisitions[0]
                    .path_template
                )

                acq_first_image = acq_par.first_image

                acq_par.first_image = item["sw_first_image"]
                acq_par.num_images = item["sw_actual_size"]
                acq_par.osc_start = item["sw_osc_start"]
                acq_par.in_interleave = (
                    acq_first_image,
                    acq_first_image + item["collect_num_images"] - 1,
                )
                self.interleave_items[item["collect_index"]][
                    "queue_entry"
                ].in_queue = item_index < (len(self.interleave_sw_list) - 1)

                msg = "Executing %s collection (subwedge %d:%d, " % (
                    method_type,
                    (item_index + 1),
                    len(self.interleave_sw_list),
                )
                msg += "from %d to %d, " % (
                    acq_par.first_image,
                    acq_par.first_image + acq_par.num_images - 1,
                )
                msg += "osc start: %.2f, osc total range: %.2f)" % (
                    item["sw_osc_start"],
                    item["sw_osc_range"],
                )
                logging.getLogger("user_level_log").info(msg)

                try:
                    self.interleave_items[item["collect_index"]][
                        "queue_entry"
                    ].pre_execute()
                    self.interleave_items[item["collect_index"]][
                        "queue_entry"
                    ].execute()
                except Exception:
                    pass
                self.interleave_items[item["collect_index"]][
                    "queue_entry"
                ].post_execute()
                self.interleave_items[item["collect_index"]]["tree_item"].setText(
                    1,
                    "Subwedge %d:%d done"
                    % (item["collect_index"] + 1, item["sw_index"] + 1),
                )

                sig_data = {
                    "current_idx": item_index,
                    "item": item,
                    "nitems": len(self.interleave_sw_list),
                    "sw_size": interleave_num_images,
                }

                self._queue_controller.emit("queue_interleaved_sw_done", (sig_data,))

        if not self.interleave_stopped:
            logging.getLogger("queue_exec").info(
                "%s collection finished" % method_type.title()
            )
            self._queue_controller.emit("queue_interleaved_finished")

        self.interleave_task = None

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        self.get_view().setText(1, "")

    def stop(self):
        BaseQueueEntry.stop(self)
        if self.interleave_task:
            self.interleave_stopped = True
            self.interleave_task.kill()
        self.get_view().setText(1, "Interleave stoped")


class SampleQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of sample queue entries. Mounting, launching centring
    and so on.
    """

    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.sample_centring_result = None

    def __getstate__(self):
        d = dict(self.__dict__)
        d["sample_centring_result"] = None
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)

    def execute(self):
        BaseQueueEntry.execute(self)
        log = logging.getLogger("queue_exec")
        sc_used = not self._data_model.free_pin_mode

        # Only execute samples with collections and when sample changer is used
        if len(self.get_data_model().get_children()) != 0 and sc_used:
            if HWR.beamline.diffractometer.in_plate_mode():
                return
            else:
                mount_device = HWR.beamline.sample_changer

            if mount_device is not None:
                log.info("Loading sample " + str(self._data_model.location))
                sample_mounted = mount_device.is_mounted_sample(
                    tuple(self._data_model.location)
                )
                if not sample_mounted:
                    self.sample_centring_result = gevent.event.AsyncResult()
                    try:
                        mount_sample(
                            self._view,
                            self._data_model,
                            self.centring_done,
                            self.sample_centring_result,
                        )
                    except Exception as e:
                        self._view.setText(1, "Error loading")
                        msg = (
                            "Error loading sample, please check"
                            + " sample changer: "
                            + str(e)
                        )
                        log.error(msg)
                        self.status = QUEUE_ENTRY_STATUS.FAILED
                        if isinstance(e, QueueSkipEntryException):
                            raise
                        else:
                            raise QueueExecutionException(str(e), self)
                else:
                    log.info("Sample already mounted")
            else:
                msg = (
                    "SampleQueueItemPolicy does not have any "
                    + "sample changer hardware object, cannot "
                    + "mount sample"
                )
                log.info(msg)
            self.get_view().setText(1, "")

    def centring_done(self, success, centring_info):
        if not success:
            msg = (
                "Loop centring failed or was cancelled, " + "please continue manually."
            )
            logging.getLogger("user_level_log").warning(msg)
        self.sample_centring_result.set(centring_info)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)

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
                    inverse_beam = grand_child.acquisitions[
                        0
                    ].acquisition_parameters.inverse_beam

                    params.append(
                        {
                            "collect_id": grand_child.id,
                            "xds_dir": xds_dir,
                            "residues": residues,
                            "anomalous": anomalous,
                            "spacegroup": space_group,
                            "cell": cell,
                            "inverse_beam": inverse_beam,
                        }
                    )

        try:
            programs = HWR.beamline.collect["auto_processing"]
            autoprocessing.start(programs, "end_multicollect", params)
        except KeyError:
            pass

        self._set_background_color()
        self._view.setText(1, "")

    def _set_background_color(self):
        BaseQueueEntry._set_background_color(self)

    def get_type_str(self):
        return "Sample"


class BasketQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)


def mount_sample(view, data_model, centring_done_cb, async_result):
    view.setText(1, "Loading sample")
    HWR.beamline.sample_view.clear_all()
    log = logging.getLogger("queue_exec")

    loc = data_model.location
    holder_length = data_model.holder_length

    snapshot_before_filename = "/tmp/test_before.png"
    snapshot_after_filename = "/tmp/test_after.png"

    robot_action_dict = {
        "actionType": "LOAD",
        "containerLocation": loc[1],
        "dewarLocation": loc[0],
        "sampleBarcode": data_model.code,
        "sampleId": data_model.lims_id,
        "sessionId": HWR.beamline.session.session_id,
        "startTime": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    # "xtalSnapshotBefore": data_model.get_snapshot_filename(prefix="before"),
    # "xtalSnapshotAfter": data_model.get_snapshot_filename(prefix="after")}

    sample_mount_device = HWR.beamline.sample_changer

    if hasattr(sample_mount_device, "__TYPE__"):
        if sample_mount_device.__TYPE__ in ["Marvin", "CATS"]:
            element = "%d:%02d" % tuple(loc)
            sample_mount_device.load(sample=element, wait=True)
        elif sample_mount_device.__TYPE__ == "PlateManipulator":
            sample_mount_device.load_sample(sample_location=loc)
        else:
            if (
                sample_mount_device.load_sample(
                    holder_length, sample_location=loc, wait=True
                )
                is False
            ):
                # WARNING: explicit test of False return value.
                # This is to preserve backward compatibility (load_sample was supposed to return None);
                # if sample could not be loaded, but no exception is raised, let's skip
                # the sample
                raise QueueSkipEntryException(
                    "Sample changer could not load sample", ""
                )

    robot_action_dict["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if sample_mount_device.has_loaded_sample():
        robot_action_dict["status"] = "SUCCESS"
    else:
        robot_action_dict["message"] = "Sample was not loaded"
        robot_action_dict["status"] = "ERROR"

    HWR.beamline.lims.store_robot_action(robot_action_dict)

    if not sample_mount_device.has_loaded_sample():
        # Disables all related collections
        view.setOn(False)
        view.setText(1, "Sample not loaded")
        raise QueueSkipEntryException("Sample not loaded", "")
    else:
        view.setText(1, "Sample loaded")
        dm = HWR.beamline.diffractometer
        if dm is not None:
            if hasattr(sample_mount_device, "__TYPE__"):
                if sample_mount_device.__TYPE__ in (
                    "Marvin",
                    "PlateManipulator",
                    "Mockup",
                ):
                    return
            try:
                dm.connect("centringAccepted", centring_done_cb)
                centring_method = view.listView().parent().parent().centring_method
                if centring_method == CENTRING_METHOD.MANUAL:
                    log.warning(
                        "Manual centring used, waiting for" + " user to center sample"
                    )
                    dm.start_centring_method(dm.MANUAL3CLICK_MODE)
                elif centring_method == CENTRING_METHOD.LOOP:
                    dm.start_centring_method(dm.C3D_MODE)
                    log.warning(
                        "Centring in progress. Please save"
                        + " the suggested centring or re-center"
                    )
                elif centring_method == CENTRING_METHOD.FULLY_AUTOMATIC:
                    log.info("Centring sample, please wait.")
                    dm.start_centring_method(dm.C3D_MODE)
                else:
                    dm.start_centring_method(dm.MANUAL3CLICK_MODE)

                view.setText(1, "Centring !")
                centring_result = async_result.get()
                if centring_result["valid"]:
                    view.setText(1, "Centring done !")
                    log.info("Centring saved")
                else:
                    view.setText(1, "Centring failed !")
                    if centring_method == CENTRING_METHOD.FULLY_AUTOMATIC:
                        raise QueueSkipEntryException(
                            "Could not center sample, skipping", ""
                        )
                    else:
                        raise RuntimeError("Could not center sample")
            except Exception as ex:
                log.exception("Could not center sample: " + str(ex))
            finally:
                dm.disconnect("centringAccepted", centring_done_cb)


class DelayQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)

    def execute(self):
        BaseQueueEntry.execute(self)
        delay = self.get_data_model().delay
        logging.getLogger("HWR").debug("Execute Delay entry, delay =  %s" % delay)
        time.sleep(delay)


def center_before_collect(view, dm, queue, sample_view):
    view.setText(1, "Waiting for input")
    log = logging.getLogger("user_level_log")

    log.info("Please select, or center on a new position and press continue.")

    queue.pause(True)
    pos, shape = None, None

    if len(sample_view.get_selected_shapes()):
        shape = sample_view.get_selected_shapes()[0]
        pos = shape.mpos()
    else:
        msg = "No centred position selected, using current position."
        log.info(msg)

        # Create a centred postions of the current postion
        pos = dm.get_positions()
        shape = sample_view.add_shape_from_mpos([pos], (0, 0), "P")

    view(1, "Centring completed")
    log.info("Centring completed")

    return queue_model_objects.CentredPosition(pos), shape
