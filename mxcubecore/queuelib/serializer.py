# encoding: utf-8
#
#  Project name: MXCuBE
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
"""QueueSerializer: turns the queue tree into the client JSON format, and
turns client JSON back into calls on QueueBuilder.
"""

import json
import logging
import os

from pydantic import ValidationError

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model import queue_model_enumerables as qme
from mxcubecore.model import queue_model_objects as qmo
from mxcubecore.queue_entry.base_queue_entry import QUEUE_ENTRY_STATUS
from mxcubecore.queuelib.constants import (
    COLLECTED,
    FAILED,
    QUEUE_FORMAT_VERSION,
    RUNNING,
    UNCOLLECTED,
    WARNING,
)
from mxcubecore.queuelib.models import (
    CharacterisationNodeModel,
    DataCollectionNodeModel,
    EnergyScanNodeModel,
    QueueNodeModel,
    SampleNode,
    TaskNodeModel,
    WorkflowNodeModel,
    XRFNodeModel,
    build_task_node_model,
)


class QueueSerializer:
    """Serializes the queue. Depends only on mxcubecore (HWR.beamline.*)
    and its sibling QueueBuilder - no self.app reference."""

    def __init__(self, builder):
        self.builder = builder

    def queue_to_dict(self, node=None) -> list[dict]:
        if node is None:
            node = HWR.beamline.queue_model.get_model_root()
            queue_dict = {
                _n.sampleID: _n.model_dump() for _n in self._queue_to_dict_rec(node)
            }

            if queue_dict:
                queue_dict["sample_order"] = list(queue_dict.keys())

            # Always present, even for an empty queue - see JSON_FORMAT.md
            # and queuelib/json_schema.py.
            queue_dict["format_version"] = QUEUE_FORMAT_VERSION

        else:
            queue_dict = self._queue_to_dict_rec(node)[0].model_dump()

        return queue_dict

    def _build_sample_node(self, n) -> SampleNode:
        """Builds the SampleNode representation of the Sample model <n>."""
        return SampleNode(
            sampleID=n.loc_str,
            queueID=n._node_id,
            code=n.code,
            type="Sample",
            location="Manual" if n.free_pin_mode else n.loc_str,
            sampleName=n.get_name(),
            proteinAcronym=n.crystals[0].protein_acronym,
            defaultPrefix=self.builder.get_default_prefix(n),
            defaultSubDir=self.builder.get_default_subdir(n),
            cell_no=getattr(n, "cell_no", 0),
            puck_no=getattr(n, "puck_no", 1),
            checked=n.is_enabled(),
            state=self.get_node_state(n._node_id)[1],
            tasks=self._queue_to_dict_rec(n),
        )

    def _queue_to_dict_rec(self, node) -> list[QueueNodeModel]:
        result = []
        node_list = node if isinstance(node, list) else node.get_children()

        for n in node_list:
            sample_node = n.get_sample_node() if hasattr(n, "get_sample_node") else None

            if isinstance(n, qmo.Sample):
                result.append(self._build_sample_node(n))

            elif isinstance(n, qmo.Characterisation):
                result.append(self._handle_char_node(sample_node, n))

            elif isinstance(n, qmo.DataCollection):
                result.append(self._handle_dc_node(sample_node, n))

            elif isinstance(n, qmo.Workflow):
                result.append(self._handle_wf_node(sample_node, n))

            elif isinstance(n, qmo.GphlWorkflow):
                result.append(self._handle_gphl_node(sample_node, n))

            elif isinstance(n, qmo.XRFSpectrum):
                result.append(self._handle_xrf_node(sample_node, n))

            elif isinstance(n, qmo.EnergyScan):
                result.append(self._handle_energy_node(sample_node, n))

            elif isinstance(n, qmo.TaskGroup) and getattr(
                n, "interleave_num_images", 0
            ):
                result.append(self._handle_interleaved_node(sample_node, n))

            elif isinstance(n, qmo.TaskNode) and getattr(n, "task_data", None):
                result.append(self._handle_task_node(sample_node, n))

            else:
                result.extend(self._queue_to_dict_rec(n))

        return result

    def pretty_print_queue(self, msg: str | None = None) -> None:
        """Pretty print current queue state for debugging."""
        try:
            q = self.queue_to_dict()
            # Prefer devtools.debug for nice printing of pydantic models
            try:
                from devtools import debug

                header = msg or "Queue state after addition:"
                print(f"[QueueSerializer] {header}")
                debug(q)
                return
            except Exception:
                pretty = json.dumps(q, indent=2, sort_keys=True, ensure_ascii=False)
                header = msg or "Queue state after addition:"
                print(f"[QueueSerializer] {header}\n{pretty}")
        except Exception as e:
            try:
                logging.getLogger("MX3.QUEUE").exception(
                    "Failed to pretty print queue: %s", e
                )
            except Exception:
                # last resort fallback
                print("[QueueSerializer] Failed to pretty print queue:", e)

    def get_node_state(self, node_id):
        if node_id is None:
            return True, UNCOLLECTED

        node, entry = HWR.beamline.queue_manager.get_entry(node_id)

        enabled = node.is_enabled()
        curr_entry = HWR.beamline.queue_manager.get_current_entry()
        running = HWR.beamline.queue_manager.is_executing() and (
            curr_entry == entry or curr_entry == entry._parent_container
        )

        if entry.status == QUEUE_ENTRY_STATUS.FAILED:
            state = FAILED
        elif entry.status == QUEUE_ENTRY_STATUS.WARNING:
            # e.g. a Characterisation that ran to completion but produced no
            # collection plan (see queue_entry/characterisation.py) - checked
            # before is_executed()/SUCCESS below, since such an entry is also
            # is_executed() but should be reported as WARNING, not COLLECTED.
            state = WARNING
        elif node.is_executed() or entry.status == QUEUE_ENTRY_STATUS.SUCCESS:
            state = COLLECTED
        elif running or entry.status == QUEUE_ENTRY_STATUS.RUNNING:
            state = RUNNING
        else:
            state = UNCOLLECTED

        return enabled, state

    def _subdir_from_path(self, path: str) -> str:
        try:
            base_path = HWR.beamline.session.get_base_image_directory()
            rel_path = os.path.relpath(path, base_path)

            if rel_path not in (".", "..") and not rel_path.startswith(f"..{os.sep}"):
                return rel_path.strip(os.sep).replace(os.sep, "/")

        except (TypeError, ValueError) as ex:
            raise RuntimeError(
                "Could not de-serialize subdir from path: %s" % path
            ) from ex

        raise RuntimeError("Could not de-serialize subdir from path: %s" % path)

    def _handle_char_node(self, sample_node, node) -> TaskNodeModel:
        enabled, state = self.get_node_state(node._node_id)
        originID, tasks = self._handle_diffraction_plan(node, sample_node)

        parameters = node.characterisation_parameters.as_dict()
        parameters["shape"] = node.get_point_index()
        refp = self._handle_dc_node(
            sample_node, node.reference_image_collection
        ).parameters.dict()

        parameters.update(refp)

        return CharacterisationNodeModel(
            label="CHARACTERISATION",
            type="Characterisation",
            parameters=parameters,
            checked=node.is_enabled(),
            sampleID=sample_node.loc_str,
            sampleQueueID=sample_node._node_id,
            taskIndex=HWR.beamline.queue_model.node_index(node)["idx"],
            queueID=node._node_id,
            state=state,
            diffractionPlan=tasks if isinstance(tasks, list) else None,
            diffractionPlanID=originID,
        )

    def _handle_dc_node(self, sample_node, node) -> TaskNodeModel:
        enabled, state = self.get_node_state(node._node_id)
        parameters = node.as_dict()
        parameters["shape"] = getattr(node, "shape", "")
        parameters["subdir"] = self._subdir_from_path(parameters["path"])

        pt = node.acquisitions[0].path_template

        # Remove python %s formatting for number of images and replace with #
        parameters["fileName"] = pt.get_image_file_name().replace(
            "%" + ("0%sd" % str(pt.precision)), int(pt.precision) * "#"
        )

        parameters["fullPath"] = os.path.join(
            parameters["path"], parameters["fileName"]
        )

        # Create a more user friendly label
        dtype_label = qme.EXPERIMENT_TYPE._fields[node.experiment_type]
        dtype_label = "OSCILLATION" if dtype_label == "NATIVE" else dtype_label
        dtype_label = (
            "LINE"
            if dtype_label == "HELICAL" and parameters["osc_range"] == 0
            else dtype_label
        )

        return DataCollectionNodeModel(
            label=dtype_label + " (" + parameters["fileName"] + ")",
            type="DataCollection",
            parameters=parameters,
            checked=node.is_enabled(),
            sampleID=sample_node.loc_str,
            sampleQueueID=sample_node._node_id,
            # node._node_id and taskIndex are None for reference collections for an
            # characterisation, we should default handle this case in mxcubecore
            taskIndex=HWR.beamline.queue_model.node_index(node)["idx"] or 0,
            queueID=node._node_id or -1,
            state=state,
        )

    def _handle_wf_node(self, sample_node, node) -> TaskNodeModel:
        enabled, state = self.get_node_state(node._node_id)
        parameters = node.parameters.copy()
        parameters.update(node.path_template.as_dict())
        parameters["path"] = parameters["directory"]
        parameters["subdir"] = self._subdir_from_path(parameters["path"])
        pt = node.path_template
        parameters["fileName"] = pt.get_image_file_name().replace(
            "%" + ("%sd" % str(pt.precision)), int(pt.precision) * "#"
        )
        parameters["fullPath"] = os.path.join(
            parameters["path"], parameters["fileName"]
        )
        return WorkflowNodeModel(
            label=parameters["label"],
            type="Workflow",
            name=node._type,
            parameters=parameters,
            checked=node.is_enabled(),
            sampleID=sample_node.loc_str,
            taskIndex=HWR.beamline.queue_model.node_index(node)["idx"],
            queueID=node._node_id,
            state=state,
        )

    def _handle_gphl_node(self, sample_node, node) -> TaskNodeModel:
        enabled, state = self.get_node_state(node._node_id)
        pt = node.path_template
        parameters = pt.as_dict()
        parameters["path"] = parameters["directory"]
        parameters["subdir"] = self._subdir_from_path(parameters["path"])
        parameters["strategy_name"] = node.strategy_name
        parameters["label"] = f"GPhL {parameters['strategy_name']}"
        parameters["shape"] = node.shape
        parameters["fileName"] = pt.get_image_file_name().replace(
            "%" + ("%sd" % str(pt.precision)), int(pt.precision) * "#"
        )
        parameters["fullPath"] = os.path.join(
            parameters["directory"], parameters["fileName"]
        )
        return DataCollectionNodeModel(
            label=parameters["label"],
            type="GphlWorkflow",
            parameters=parameters,
            checked=node.is_enabled(),
            sampleID=sample_node.loc_str,
            sampleQueueID=sample_node._node_id,
            taskIndex=HWR.beamline.queue_model.node_index(node)["idx"],
            queueID=node._node_id,
            state=state,
        )

    def _handle_xrf_node(self, sample_node, node) -> TaskNodeModel:
        enabled, state = self.get_node_state(node._node_id)
        # This should be moved to as_dict of the XRFSpectrum node in mxcubecore
        parameters = {"countTime": node.count_time, "shape": str(node.shape)}
        parameters.update(node.path_template.as_dict())
        parameters["path"] = parameters["directory"]
        parameters["subdir"] = self._subdir_from_path(parameters["path"])
        pt = node.path_template
        parameters["prefix"] = pt.get_prefix()
        parameters["fileName"] = pt.get_image_file_name().replace(
            "%" + ("%sd" % str(pt.precision)), int(pt.precision) * "#"
        )
        parameters["fullPath"] = os.path.join(
            parameters["path"], parameters["fileName"]
        )

        return XRFNodeModel(
            label="XRF Scan",
            type="xrf_spectrum",
            parameters=parameters,
            checked=node.is_enabled(),
            sampleID=sample_node.loc_str,
            sampleQueueID=sample_node._node_id,
            taskIndex=HWR.beamline.queue_model.node_index(node)["idx"],
            queueID=node._node_id,
            state=state,
        )

    def _handle_energy_node(self, sample_node, node) -> TaskNodeModel:
        enabled, state = self.get_node_state(node._node_id)
        parameters = {
            "element": node.element_symbol,
            "edge": node.edge,
            "shape": str(node.shape),
        }
        parameters.update(node.path_template.as_dict())
        parameters["path"] = parameters["directory"]
        parameters["subdir"] = self._subdir_from_path(parameters["path"])
        pt = node.path_template
        parameters["prefix"] = pt.get_prefix()
        parameters["fileName"] = pt.get_image_file_name().replace(
            "%" + ("%sd" % str(pt.precision)), int(pt.precision) * "#"
        )
        parameters["fullPath"] = os.path.join(
            parameters["path"], parameters["fileName"]
        )

        return EnergyScanNodeModel(
            label="Energy Scan",
            type="energy_scan",
            parameters=parameters,
            checked=node.is_enabled(),
            sampleID=sample_node.loc_str,
            sampleQueueID=sample_node._node_id,
            taskIndex=HWR.beamline.queue_model.node_index(node)["idx"],
            queueID=node._node_id,
            state=state,
        )

    def _handle_interleaved_node(self, sample_node, node) -> TaskNodeModel:
        wedges = [self._handle_dc_node(sample_node, c) for c in node.get_children()]
        _, state = self.get_node_state(node._node_id)
        return DataCollectionNodeModel(
            label="Interleaved",
            type="Interleaved",
            parameters={
                "wedges": [w.dict() for w in wedges],
                "swNumImages": node.interleave_num_images,
            },
            checked=node.is_enabled(),
            sampleID=sample_node.loc_str,
            sampleQueueID=sample_node._node_id,
            taskIndex=HWR.beamline.queue_model.node_index(node)["idx"],
            queueID=node._node_id,
            state=state,
        )

    def _handle_task_node(self, sample_node, node) -> TaskNodeModel:
        parameters = {
            **node.task_data.collection_parameters.dict(),
            **node.task_data.user_collection_parameters.dict(),
            **node.task_data.path_parameters.dict(),
            **node.task_data.common_parameters.dict(),
            **node.task_data.legacy_parameters.dict(),
        }
        pt = node.acquisitions[0].path_template
        parameters["path"] = pt.directory
        parameters["subdir"] = os.path.join(
            *parameters["path"].split(HWR.beamline.session.raw_data_folder_name)[1:]
        ).lstrip("/")
        parameters["fileName"] = pt.get_image_file_name().replace(
            "%" + ("%sd" % str(pt.precision)), int(pt.precision) * "#"
        )
        parameters["fullPath"] = os.path.join(
            parameters["path"], parameters["fileName"]
        )
        _, state = self.get_node_state(node._node_id)
        return DataCollectionNodeModel(
            label=parameters.get("label", "TaskNode"),
            type=parameters.get("type", "TaskNode"),
            parameters=parameters,
            checked=node.is_enabled(),
            sampleID=sample_node.loc_str,
            sampleQueueID=sample_node._node_id,
            taskIndex=HWR.beamline.queue_model.node_index(node)["idx"],
            queueID=node._node_id,
            state=state,
        )

    def _handle_diffraction_plan(self, node, sample_node):
        model, _ = HWR.beamline.queue_manager.get_entry(node._node_id)
        originID = model.get_origin()
        tasks = []
        if len(model.diffraction_plan) > 0:
            collections = model.diffraction_plan[0]
            for col in collections:
                t = self._handle_dc_node(sample_node, col)
                t_dict = t.dict()
                t_dict["isDiffractionPlan"] = True
                tasks.append(t_dict)
            return originID, tasks
        return -1, []

    def _add_task(self, node_id: int, item) -> int:
        """Build and enqueue a single (non-Sample) task under node_id.

        :param node_id: id of the sample the task belongs to
        :param item: a validated TaskNodeUnion instance (see models.py)
        :returns: the new task's queue id
        """
        if item.type == "DataCollection":
            return self.builder.add_data_collection(node_id, item.dict())

        elif item.type == "Characterisation":
            return self.builder.add_characterisation(node_id, item.dict())

        elif item.type in ("Workflow", "GphlWorkflow"):
            return self.builder.add_workflow(node_id, item.dict())

        elif item.type == "Interleaved":
            return self.builder.add_interleaved(node_id, item.dict())

        elif item.type == "xrf_spectrum":
            return self.builder.add_xrf_scan(node_id, item.dict())

        elif item.type == "energy_scan":
            return self.builder.add_energy_scan(node_id, item.dict())

        else:
            return self.builder.add_queue_entry(node_id, item.dict(), item.type)

    def _resolve_sample_node_id(self, parent: int | str) -> int:
        """Resolve a sample locator (queueID or loc_str) to its node id."""
        if isinstance(parent, str):
            sample_model = HWR.beamline.queue_model.get_sample_by_loc_str(parent)

            if sample_model is None:
                raise RuntimeError(f"No queued sample with sampleID/loc_str {parent!r}")

            return sample_model._node_id

        return parent

    def add_task(self, parent: int | str, item: dict) -> int:
        """Add a single task to an already-queued sample.

        Unlike queue_add_item (which validates and adds a whole batch of
        samples/tasks at once), this adds exactly one task to a sample that
        must already be in the queue - it never creates a Sample node.

        :param parent: the sample's queueID, or its sampleID/loc_str
        :param item: task dict, e.g. {"type": "DataCollection",
            "parameters": {...}}
        :returns: the new task's queue id
        """
        node_id = self._resolve_sample_node_id(parent)

        try:
            task = build_task_node_model(item)
        except ValidationError:
            logging.getLogger("MX3.QUEUE").exception(
                "Failed to validate task: %s" % item
            )
            raise

        task_id = self._add_task(node_id, task)

        if logging.getLogger("MX3.QUEUE").isEnabledFor(logging.DEBUG):
            try:
                self.pretty_print_queue(f"Added task type={task.type} parent={parent}")
            except Exception:
                logging.getLogger("MX3.HWR").exception(
                    "Failed to pretty print queue after adding task"
                )

        return task_id

    def _queue_add_item_rec(self, parent_node_id: int | None, item: SampleNode):
        if item.type == "Sample":
            sample_node_id = self.builder.add_sample(item.sampleID, item.dict())

            for task in item.tasks or []:
                self._queue_add_item_rec(sample_node_id, task)

        else:
            self._add_task(parent_node_id, item)

        # Print the queue after adding an item for easier debugging

        if logging.getLogger("MX3.QUEUE").isEnabledFor(logging.DEBUG):
            try:
                self.pretty_print_queue(
                    f"Added item type={item.type} parent={parent_node_id}"
                )
            except Exception:
                logging.getLogger("MX3.HWR").exception(
                    "Failed to pretty print queue after adding item"
                )

    def queue_add_item(self, item_list):
        """Add queue items to the queue.

        Add the queue items in item_list to the queue. The items in the list can
        be either samples and or tasks. Samples are only added if they are not
        already in the queue  and tasks are appended to the end of an
        (already existing) sample. A task is ignored if the sample is not already
        in the queue.

        The items in item_list are dictionaries with the following structure:

        { "type": "Sample | DataCollection | Characterisation",
        "sampleID": sid
        ... task or sample specific data
        }

        Each item (dictionary) describes either a sample or a task.
        """
        try:
            parsed_items = [SampleNode.model_validate(i) for i in item_list]
        except ValidationError:
            logging.getLogger("MX3.QUEUE").exception(
                "Failed to validate queue item(s): %s" % item_list
            )
            raise
        for item in parsed_items:
            self._queue_add_item_rec(None, item)

        # Handling interleaved data collections, swap interleave task with
        # the first of the data collections that are used as wedges, and then
        # remove all collections that were used as wedges
        first_tasks = parsed_items[0].tasks or []
        for task in first_tasks:
            if (
                task.type == "Interleaved"
                and task.parameters
                and task.parameters.taskIndexList
            ):
                current_queue = self.queue_to_dict()
                sid = task.sampleID
                interleaved_tindex = len(current_queue[sid]["tasks"]) - 1
                tindex_list = sorted(task.parameters.taskIndexList)

                # Swap first "wedge task" and the actual interleaved collection
                # so that the interleaved task is the first task
                HWR.beamline.queue_manager.swap_task_entry(
                    sid, interleaved_tindex, tindex_list[0]
                )

                # We remove the swapped wedge index from the list, (now pointing
                # at the interleaved collection) and add its new position
                # (last task item) to the list.
                tindex_list = tindex_list[1:]
                tindex_list.append(interleaved_tindex)

                # The delete operation can be done all in one call if we make sure
                # that we remove the items starting from the end (not altering
                # previous indices)
                for ti in reversed(tindex_list):
                    HWR.beamline.queue_manager.delete_entry_at([[sid, int(ti)]])

        return self.queue_to_dict()
