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
"""QueueBuilder: constructs queue model nodes (and, indirectly, their
matching QueueEntry objects - see QueueModel.queue_model_child_added) from
client task data.
"""

import itertools
import os

from mxcubecore import HardwareRepository as HWR
from mxcubecore import queue_entry as qe
from mxcubecore.model import queue_model_enumerables as qme
from mxcubecore.model import queue_model_objects as qmo
from mxcubecore.queuelib.constants import ORIGIN_MX3


class QueueBuilder:
    """Creates queue models the creation of queue entries are handled
    in queue_model_child_added event handler"""

    def get_run_number(self, pt):
        # Path templates of files not yet written to disk, we are only
        # interested in the prefix path

        pt.run_number = HWR.beamline.queue_model.get_next_run_number(pt)
        start_fname, end_fname = pt.get_first_and_last_file()

        while os.path.isfile(start_fname) or os.path.isfile(end_fname):
            pt.run_number += 1

            if pt.run_number > 1000:
                msg = "Over a thousand runs of the same collection"
                raise RuntimeError(msg)

            start_fname, end_fname = pt.get_first_and_last_file()

        return pt.run_number

    def get_default_prefix(self, sample_data, generic_name=False):
        """Thin pass-through to HWR.beamline.session.get_default_prefix.

        Kept as its own method (rather than called inline) so
        apply_template can call it as self.get_default_prefix(...).
        """
        return HWR.beamline.session.get_default_prefix(sample_data, generic_name)

    def get_default_subdir(self, sample_data):
        """Thin pass-through to HWR.beamline.session.get_default_subdir."""
        return HWR.beamline.session.get_default_subdir(sample_data)

    def apply_template(self, params, sample_model, path_template):
        # Apply subdir template if used:
        if "{" in params.get("subdir", ""):
            if sample_model.crystals[0].protein_acronym:
                # POSITION is accepted (see VALID_SUBDIR_TEMPLATE_FIELDS in
                # models.py) but unused.
                params["subdir"] = params["subdir"].format(
                    NAME=sample_model.get_name(),
                    ACRONYM=sample_model.crystals[0].protein_acronym,
                    POSITION=params.get("shape") or "",
                )
            else:
                stripped = params["subdir"][0 : params["subdir"].find("{")]
                params["subdir"] = stripped + sample_model.get_name()

            # The template was only applied partially if subdir ends with '-'
            # probably because either acronym or protein name is null in LIMS
            if params["subdir"].endswith("-"):
                params["subdir"] = sample_model.get_name()

        # Making sure that there are no ":" left from the sample name incase
        # no synchronisation with LIMS was done
        params["subdir"] = params["subdir"].replace(":", "-")

        if "{" in params.get("prefix", ""):
            # sample_model is already the authoritative, up-to-date copy of
            # this sample's identity (see the design doc's step 4 item 2
            # investigation: every path that refreshes the web UI's sample
            # list also syncs onto sample_model before this can run), so
            # read directly from it instead of the web-only sample list.
            prefix = self.get_default_prefix(sample_model)
            shape = params.get("shape") or ""
            params["prefix"] = params["prefix"].format(PREFIX=prefix, POSITION=shape)

            if params["prefix"].endswith("_"):
                params["prefix"] = params["prefix"][:-1]

        # mxcube web passes entire prefix as prefix, including reference, mad and wedge
        # prefix. So we strip those before setting the actual base_prefix.
        params["prefix"] = self.strip_prefix(path_template, params["prefix"])

    def strip_prefix(self, pt, prefix):
        """Strip the reference, wedge and mad prefix from a given prefix.

        For example,
        remove ``ref-`` from the beginning
        and ``_w[n]`` and ``-pk``, ``-ip``, ``-ipp`` from the end.

        :param PathTemplate pt: path template used to create the prefix
        :param str prefix: prefix from the client
        :returns: stripped prefix
        """
        if (
            pt.reference_image_prefix
            and pt.reference_image_prefix == prefix[0 : len(pt.reference_image_prefix)]
        ):
            prefix = prefix[len(pt.reference_image_prefix) + 1 :]

        if pt.wedge_prefix and pt.wedge_prefix == prefix[-len(pt.wedge_prefix) :]:
            prefix = prefix[: -(len(pt.wedge_prefix) + 1)]

        if pt.mad_prefix and pt.mad_prefix == prefix[-len(pt.mad_prefix) :]:
            prefix = prefix[: -(len(pt.mad_prefix) + 1)]

        return prefix

    def add_sample(self, sample_id: str, item):
        """Add a sample with sample id <sample_id> the queue.

        :param sample_id: Sample id (often sample changer location)
        :returns: SampleQueueEntry
        """
        # Sample is already in the queue, just enable it (incase it was disabled)
        if item.get("queueID", -1) != -1:
            HWR.beamline.queue_manager.enable_entry(item["queueID"], True)
            return item["queueID"]

        sample_model = qmo.Sample()
        sample_model.set_origin(ORIGIN_MX3)
        sample_model.set_from_dict(item)

        # Explicitly set parameters that are not sent by the client
        sample_model.loc_str = sample_id
        sample_model.free_pin_mode = item["location"] == "Manual"
        sample_model.cell_no = item.get("cell_no", 0)
        sample_model.puck_no = item.get("puck_no", 1)
        sample_model.set_name(item["sampleName"])
        sample_model.name = item["sampleName"]

        if sample_model.free_pin_mode:
            sample_model.location = (None, sample_id)
        elif HWR.beamline.diffractometer.in_plate_mode:
            component = HWR.beamline.sample_changer._resolve_component(item["location"])
            sample_model.location = component.get_coords()
        else:
            sample_model.location = tuple(map(int, item["location"].split(":")))

        # The matching SampleQueueEntry is created and enqueued automatically
        # by Queue.queue_model_child_added
        HWR.beamline.queue_model.add_child(
            HWR.beamline.queue_model.get_model_root(), sample_model
        )

        return sample_model._node_id

    def get_folder_tag(self, params):
        tag = "datacollection"

        if params["helical"] and params["osc_range"] == 0:
            tag = "line"
        elif params["helical"]:
            tag = "helical"
        elif params.get("mesh"):
            tag = "mesh"
        elif params.get("type") == "Characterisation":
            tag = "characterisation"

        return tag

    def set_dc_params(
        self,
        model: qmo.DataCollection,
        entry: qe.BaseQueueEntry,
        task_data: dict,
        sample_model,
    ):
        """Helper method that sets the data collection parameters for a DataCollection.

        :param model: The model to set parameters of
        :param entry: The queue entry of the model
        :param task_data: Dictionary with new parameters
        """
        acq = model.acquisitions[0]
        params = task_data["parameters"]
        acq.acquisition_parameters.set_from_dict(params)

        self._set_processing_params(model.processing_parameters, params)

        ftype = HWR.beamline.detector.get_property("file_suffix")
        ftype = ftype if ftype else ".?"

        acq.path_template.set_from_dict(params)
        # certain attributes have to be updated explicitly,
        # like precision, suffix ...
        acq.path_template.start_num = params["first_image"]
        acq.path_template.num_files = params["num_images"]
        acq.path_template.suffix = ftype
        acq.path_template.precision = "0" + str(qmo.PathTemplate.precision)

        self.apply_template(params, sample_model, acq.path_template)

        self._set_default_prefix(acq.path_template, params, sample_model)

        run_number_dir_parts = (
            params.get("subdir", "").strip("/").split("/")[-1].split("_")
        )

        # When duplicating an item the "run number" directory of the original
        # item is already part of the data subfolder, so we need to strip ita
        # to avoid nesting.

        # Sub directory is a run number directory if it starts
        # with run folowed by a number and a tag spereated by a
        # underscore (_) for instance, run_01_datacollection
        # The run number directory is passed as the last folder of the
        # data sub direecotry when and item is duplicated. We strip
        # the run number folder in this case to remove duplication
        if (
            len(run_number_dir_parts) == 3
            and run_number_dir_parts[0] == "run"
            and run_number_dir_parts[1].isnumeric()
            and run_number_dir_parts[2] == self.get_folder_tag(params)
        ):
            params["subdir"] = "/".join(
                params.get("subdir", "").strip("/").split("/")[0:-1]
            )

        full_path, process_path = HWR.beamline.session.get_full_paths(
            params.get("subdir", ""), self.get_folder_tag(params)
        )

        acq.path_template.directory = full_path
        acq.path_template.process_directory = process_path

        # MXCuBE Web specific shape attribute
        model.shape = params["shape"]

        # If there is a centered position associated with this data collection, get
        # the necessary data for the position and pass it to the collection.
        if params["helical"]:
            model.experiment_type = qme.EXPERIMENT_TYPE.HELICAL
            acq2 = qmo.Acquisition()
            model.acquisitions.append(acq2)

            line = HWR.beamline.sample_view.get_shape(params["shape"])
            p1, p2 = line.refs
            p1, p2 = (
                HWR.beamline.sample_view.get_shape(p1),
                HWR.beamline.sample_view.get_shape(p2),
            )
            cpos1 = p1.get_centred_position()
            cpos2 = p2.get_centred_position()

            acq.acquisition_parameters.centred_position = cpos1
            acq2.acquisition_parameters.centred_position = cpos2
        elif params.get("mesh", False):
            grid = HWR.beamline.sample_view.get_shape(params["shape"])
            acq.acquisition_parameters.mesh_range = (
                grid.width,
                grid.height,
            )
            mesh_center = HWR.beamline.get_default_acquisition_parameters(
                "mesh"
            ).mesh_center
            if mesh_center == "top-left":
                acq.acquisition_parameters.centred_position = (
                    grid.get_centred_positions()[0]
                )
            else:
                acq.acquisition_parameters.centred_position = (
                    grid.get_centred_positions()[1]
                )
            acq.acquisition_parameters.mesh_steps = grid.get_num_lines()
            acq.acquisition_parameters.num_images = task_data["parameters"][
                "num_images"
            ]

            model.experiment_type = qme.EXPERIMENT_TYPE.MESH
            model.set_requires_centring(False)
        elif params["shape"] != -1:
            point = HWR.beamline.sample_view.get_shape(params["shape"])
            cpos = point.get_centred_position()
            acq.acquisition_parameters.centred_position = cpos

        # Only get a run number for new tasks, keep the already existing
        # run number for existing items.
        if not task_data.get("queueID", ""):
            acq.path_template.run_number = self.get_run_number(acq.path_template)

        model.set_enabled(task_data["checked"])
        entry.set_enabled(task_data["checked"])

    def set_gphl_wf_params(
        self,
        model: qmo.GphlWorkflow,
        entry: qe.BaseQueueEntry,
        task_data: dict,
        sample_model,
    ):
        """Helper method that sets the parameters for a GPhL workflow task.

        :param model: The model to set parameters of
        :param entry: The queue entry of the model
        :param task_data: Dictionary with new parameters
        :param sample_model: The Sample queueModelObject
        """
        params = task_data["parameters"]
        self.apply_template(params, sample_model, model.path_template)

        # params include only path_template-related parametes and strategy_name
        model.init_from_task_data(sample_model, params)

        # # NBNB
        # # These two calls seems to be needed by the Global phasing workflows
        # # Adding them resolves the current conflict
        # # NBNB CHECK REMOVAL
        # model.set_pre_strategy_params(**params)
        # model.set_pre_acquisition_params(**params)

        model.set_enabled(task_data["checked"])
        entry.set_enabled(task_data["checked"])

    def set_wf_params(
        self,
        model: qmo.Workflow,
        entry: qe.BaseQueueEntry,
        task_data: dict,
        sample_model,
    ):
        """Helper method that sets the parameters for a workflow task.

        :param model: The model to set parameters of
        :param entry: The queue entry of the model
        :param task_data: Dictionary with new parameters
        """
        params = task_data["parameters"]
        model.parameters = params
        model.path_template.set_from_dict(params)
        model.path_template.num_files = 0
        model.path_template.precision = "0" + str(qmo.PathTemplate.precision)

        self.apply_template(params, sample_model, model.path_template)
        self._set_default_prefix(model.path_template, params, sample_model)

        full_path = os.path.join(
            HWR.beamline.session.get_base_image_directory(),
            params.get("subdir", ""),
        )

        model.path_template.directory = full_path

        process_path = os.path.join(
            HWR.beamline.session.get_base_process_directory(),
            params.get("subdir", ""),
        )
        model.path_template.process_directory = process_path

        model.set_name("Workflow task")
        model.set_type(params["wfname"])

        beamline_params = {}
        beamline_params["directory"] = model.path_template.directory
        beamline_params["prefix"] = model.path_template.get_prefix()
        beamline_params["run_number"] = model.path_template.run_number
        beamline_params["collection_software"] = "MXCuBE - 3.0"
        beamline_params["sample_node_id"] = sample_model._node_id
        beamline_params["workflow_node_id"] = model._node_id
        beamline_params["sample_lims_id"] = sample_model.lims_id
        beamline_params["beamline"] = HWR.beamline.session.endstation_name
        beamline_params["shape"] = params["shape"]

        params_list = list(
            map(
                str,
                list(itertools.chain(*iter(beamline_params.items()))),
            )
        )
        params_list.insert(0, params["wfpath"])
        params_list.insert(0, "modelpath")

        model.params_list = params_list

        model.set_enabled(task_data["checked"])
        entry.set_enabled(task_data["checked"])

    def set_char_params(
        self,
        model: qmo.Characterisation,
        entry: qe.BaseQueueEntry,
        task_data: dict,
        sample_model,
    ):
        """Helper method that sets the characterisation parameters.

        Helper method that sets the characterisation parameters for a Characterisation.

        :param model: The mode to set parameters of
        :param entry: The queue entry of the model
        :param task_data: Dictionary with new parameters
        """
        params = task_data["parameters"]
        self.set_dc_params(
            model.reference_image_collection,
            entry,
            task_data,
            sample_model,
        )

        model.characterisation_parameters.set_from_dict(params)

        # MXCuBE Web specific shape attribute
        # TODO: Please consider defining shape attribute properly !
        model.shape = params["shape"]

        model.set_enabled(task_data["checked"])
        entry.set_enabled(task_data["checked"])

    def set_xrf_params(
        self,
        model: qmo.XRFSpectrum,
        entry: qe.BaseQueueEntry,
        task_data: dict,
        sample_model,
    ):
        """Helper method that sets the xrf scan parameters for a XRF spectrum Scan.

        :param model: The model to set parameters of
        :param entry: The queue entry of the model
        :param task_data: Dictionary with new parameters
        """
        params = task_data["parameters"]

        ftype = HWR.beamline.xrf_spectrum.get_property("file_suffix", "dat").strip()

        model.path_template.set_from_dict(params)
        model.path_template.suffix = ftype
        model.path_template.precision = "0" + str(qmo.PathTemplate.precision)
        self._set_default_prefix(model.path_template, params, sample_model)

        full_path, process_path = HWR.beamline.session.get_full_paths(
            params.get("subdir", ""), "xrf"
        )
        model.path_template.directory = full_path
        model.path_template.process_directory = process_path

        # Only get a run number for new tasks, keep the already existing
        # run number for existing items.
        if not params.get("queueID", ""):
            model.path_template.run_number = self.get_run_number(model.path_template)

        # Set count time, and if any, other paramters
        model.count_time = params.get("exp_time", 0)

        # MXCuBE Web specific shape attribute
        model.shape = params["shape"]

        model.set_enabled(task_data["checked"])
        entry.set_enabled(task_data["checked"])

    def set_energy_scan_params(
        self,
        model: qmo.EnergyScan,
        entry: qe.BaseQueueEntry,
        task_data: dict,
        sample_model,
    ):
        """Helper method that sets the xrf scan parameters for a XRF spectrum Scan.

        :param model: The model to set parameters of
        :param entry: The queue entry of the model
        :param task_data: Dictionary with new parameters
        """
        params = task_data["parameters"]

        ftype = HWR.beamline.energy_scan.get_property("file_suffix", "raw").strip()

        model.path_template.set_from_dict(params)
        model.path_template.suffix = ftype
        model.path_template.precision = "0" + str(qmo.PathTemplate.precision)
        self._set_default_prefix(model.path_template, params, sample_model)

        full_path, process_path = HWR.beamline.session.get_full_paths(
            params.get("subdir", ""), "energy_scan"
        )
        model.path_template.directory = full_path
        model.path_template.process_directory = process_path

        # Only get a run number for new tasks, keep the already existing
        # run number for existing items.
        if not params.get("queueID", ""):
            model.path_template.run_number = self.get_run_number(model.path_template)

        # Set element, and if any, other parameters
        model.element_symbol = params.get("element", "")
        model.edge = params.get("edge", "")

        # MXCuBE Web specific shape attribute
        model.shape = params["shape"]

        model.set_enabled(task_data["checked"])
        entry.set_enabled(task_data["checked"])

    def _create_dc(self) -> qmo.DataCollection:
        """Create a data collection model.

        Its corresponding DataCollectionQueueEntry is created and enqueued
        automatically once the model is added to the tree - see
        Queue.queue_model_child_added.

        :returns: The data collection model.
        """
        dc_model = qmo.DataCollection()
        dc_model.set_origin(ORIGIN_MX3)
        dc_model.center_before_collect = True
        dc_model.take_snapshots = HWR.beamline.collect.get_property(
            "num_snapshots", HWR.beamline.collect.number_of_snapshots
        )

        return dc_model

    def _create_queue_entry(self, task: dict, task_name):  # noqa: D417
        """Create the data model for a queue entry.

        Its corresponding QueueEntry is created and enqueued automatically
        once the model is added to the tree - see
        Queue.queue_model_child_added.

        Args:
            task: Collection parameters
        Return:
            The data model.
        """
        if not task["parameters"]["osc_range"]:
            task["parameters"]["osc_range"] = None

        queue_entry_name = task_name.title().replace("_", "") + "QueueEntry"
        entry_cls = getattr(qe, queue_entry_name)
        data = entry_cls.DATA_MODEL(
            path_parameters=task["parameters"],
            common_parameters=task["parameters"],
            user_collection_parameters=task["parameters"],
            collection_parameters=task["parameters"],
            legacy_parameters=task["parameters"],
        )

        model = entry_cls.QMO(task_data=data)
        model.set_origin(ORIGIN_MX3)

        return model

    def _create_wf(self) -> qmo.Workflow:
        """Create a workflow model.

        :returns: The workflow model.
        """
        wf_model = qmo.Workflow()
        wf_model.set_origin(ORIGIN_MX3)

        return wf_model

    def _create_gphl_wf(self) -> qmo.GphlWorkflow:
        """Create a gphl workflow model.

        :returns: The GPhL workflow model.
        """
        wf_model = qmo.GphlWorkflow()
        wf_model.set_origin(ORIGIN_MX3)

        return wf_model

    def _create_xrf(self, sample_model: qmo.Sample) -> qmo.XRFSpectrum:
        """Create a XRFSpectrum model.

        :param sample_model: The sample the collection belongs to
        :returns: The XRFSpectrum model.
        """
        xrf_model = qmo.XRFSpectrum(sample=sample_model)
        xrf_model.set_origin(ORIGIN_MX3)

        return xrf_model

    def _create_energy_scan(self, sample_model: qmo.Sample) -> qmo.EnergyScan:
        """Create an energy scan model.

        :param sample_model: The sample the collection belongs to
        :returns: The energy scan model.
        """
        escan_model = qmo.EnergyScan(sample=sample_model)
        escan_model.set_origin(ORIGIN_MX3)

        return escan_model

    def _create_and_enqueue_task_group(self, parent_model, group_model=None):
        """Create a task group and add it as a child of parent_model.

        The matching TaskGroupQueueEntry is created and enqueued
        automatically, see Queue.queue_model_child_added.
        """
        if group_model is None:
            group_model = qmo.TaskGroup()

        group_model.set_origin(ORIGIN_MX3)
        group_model.set_enabled(True)
        HWR.beamline.queue_model.add_child(parent_model, group_model)

        group_entry = HWR.beamline.queue_manager.get_entry_with_model(group_model)

        return group_model, group_entry

    def _attach_model_to_group(self, group_model, model):
        """Add model as a child of group_model.

        The matching QueueEntry is created and enqueued automatically, see
        Queue.queue_model_child_added.

        :returns: The automatically created QueueEntry for model.
        """
        HWR.beamline.queue_model.add_child(group_model, model)

        return HWR.beamline.queue_manager.get_entry_with_model(model)

    def _set_processing_params(self, processing_params, params):
        processing_params.space_group = params.get("space_group", "")
        processing_params.cell_a = params.get("cellA", "")
        processing_params.cell_alpha = params.get("cellAlpha", "")
        processing_params.cell_b = params.get("cellB", "")
        processing_params.cell_beta = params.get("cellBeta", "")
        processing_params.cell_c = params.get("cellC", "")
        processing_params.cell_gamma = params.get("cellGamma", "")

    def _set_default_prefix(self, path_template, params, sample_model):
        prefix = params.get("prefix", "")
        path_template.base_prefix = (
            prefix if prefix else HWR.beamline.session.get_default_prefix(sample_model)
        )

    def add_characterisation(self, node_id: int, task: dict) -> int:
        """Add a data characterisation task to the sample with id: <id>.

        :param node_id: id of the sample to which the task belongs
        :param task: Task data (parameters)

        :returns: The queue id of the Data collection
        """
        sample_model, sample_entry = HWR.beamline.queue_manager.get_entry(node_id)
        params = task["parameters"]

        refdc_model = self._create_dc()
        refdc_model.acquisitions[0].path_template.reference_image_prefix = "ref"
        refdc_model.set_name("refdc")
        char_params = qmo.CharacterisationParameters().set_from_dict(params)

        char_model = qmo.Characterisation(refdc_model, char_params)
        char_model.set_origin(ORIGIN_MX3)

        # A characterisation has two TaskGroups one for the characterisation itself
        # and its reference collection and one for the resulting diffraction plans.
        # But we only create a reference group if there is a result !
        refgroup_model, refgroup_entry = self._create_and_enqueue_task_group(
            sample_model
        )
        char_entry = self._attach_model_to_group(refgroup_model, char_model)
        char_entry.queue_model = HWR.beamline.queue_model

        # Set the characterisation and reference collection parameters
        self.set_char_params(char_model, char_entry, task, sample_model)

        # the default value is True, here we adapt to mxcube Web needs
        char_model.auto_add_diff_plan = HWR.beamline.queue_manager.auto_add_diff_plan
        char_entry.auto_add_diff_plan = HWR.beamline.queue_manager.auto_add_diff_plan

        char_model.set_enabled(task["checked"])
        char_entry.set_enabled(task["checked"])

        return char_model._node_id

    def add_data_collection(self, node_id: int, task: dict) -> int:
        """Add a data collection task to the sample with id: <id>.

        :param node_id: id of the sample to which the task belongs
        :param task: task data

        :returns: The queue id of the data collection
        """
        sample_model, _sample_entry = HWR.beamline.queue_manager.get_entry(node_id)
        dc_model = self._create_dc()

        group_model, _group_entry = self._create_and_enqueue_task_group(sample_model)
        dc_entry = self._attach_model_to_group(group_model, dc_model)
        self.set_dc_params(dc_model, dc_entry, task, sample_model)

        return dc_model._node_id

    def add_queue_entry(self, node_id: int, task: dict, task_name: str):
        """Add a queue entry to the sample with id <node_id>.

        Args:
            node_id: id of the sample to which the task belongs
            task: task data
            task_name: The task name
        """
        sample_model, _sample_entry = HWR.beamline.queue_manager.get_entry(node_id)
        model = self._create_queue_entry(task, task_name)
        model.set_origin(ORIGIN_MX3)

        acq = model.acquisitions[0]
        params = task["parameters"]

        self._set_processing_params(model.processing_parameters, params)

        ftype = HWR.beamline.detector.get_property("file_suffix")
        ftype = ftype if ftype else ".?"

        acq.path_template.set_from_dict(params)
        # certain attributes have to be updated explicitly,
        # like precision, suffix ...
        acq.path_template.start_num = params["first_image"]
        acq.path_template.num_files = params["num_images"]
        acq.path_template.suffix = ftype
        acq.path_template.precision = "0" + str(qmo.PathTemplate.precision)

        self._set_default_prefix(acq.path_template, params, sample_model)

        full_path, process_path = HWR.beamline.session.get_full_paths(
            # Note that 'experiment_name' field can either be omitted, set to None
            # or some string value. For cases it is not defined (omitted or None)
            # the "" will be used for the path generation.
            os.path.join(
                params.get("subdir", ""), params.get("experiment_name", "") or ""
            ),
            task_name,
        )
        acq.path_template.directory = full_path
        acq.path_template.process_directory = process_path

        model.shape = params["shape"]

        group_model, _group_entry = self._create_and_enqueue_task_group(sample_model)
        self._attach_model_to_group(group_model, model)

        return model._node_id

    def add_workflow(self, node_id: int, task: dict) -> int:
        """Add a worklfow task to the parent node with id: <id>.

        For adding GPhL Auto workflow, call with node_id==parent_node_id
        and all required parameters in task["parameters"]

        :param node_id: id of the parent node to which the task belongs
        :param task: task data

        :returns: The queue id of the data collection
        """
        parent_model, _parent_entry = HWR.beamline.queue_manager.get_entry(node_id)
        sample_model = parent_model.get_sample_node()

        group_model, _group_entry = self._create_and_enqueue_task_group(parent_model)

        if task["parameters"]["wfpath"] == "Gphl":
            wf_model = self._create_gphl_wf()
            dc_entry = self._attach_model_to_group(group_model, wf_model)
            self.set_gphl_wf_params(
                wf_model,
                dc_entry,
                task,
                sample_model,
            )
        else:
            wf_model = self._create_wf()
            dc_entry = self._attach_model_to_group(group_model, wf_model)
            self.set_wf_params(wf_model, dc_entry, task, sample_model)

        return wf_model._node_id

    def add_interleaved(self, node_id: int, task: dict) -> int:
        """Add a interleaved data collection task to the sample with id: <id>.

        :param node_id: id of the sample to which the task belongs
        :param task: task data

        :returns: The queue id of the data collection
        """
        sample_model, _sample_entry = HWR.beamline.queue_manager.get_entry(node_id)

        group_model, _group_entry = self._create_and_enqueue_task_group(sample_model)
        group_model.interleave_num_images = task["parameters"]["swNumImages"]

        wc = 0

        for wedge in task["parameters"]["wedges"]:
            wc = wc + 1
            dc_model = self._create_dc()
            dc_entry = self._attach_model_to_group(group_model, dc_model)
            self.set_dc_params(dc_model, dc_entry, wedge, sample_model)

            # Add wedge prefix to path
            dc_model.acquisitions[0].path_template.wedge_prefix = "wedge-%s" % wc

            # Disable snapshots for sub-wedges
            dc_model.acquisitions[0].acquisition_parameters.take_snapshots = False

        return group_model._node_id

    def add_xrf_scan(self, node_id: int, task: dict) -> int:
        """Add a XRF Scan task to the sample with id: <id>.

        :param node_id: id of the sample to which the task belongs
        :param task: task data

        :returns: The queue id of the data collection
        """
        sample_model, _sample_entry = HWR.beamline.queue_manager.get_entry(node_id)
        xrf_model = self._create_xrf(sample_model)

        group_model, _group_entry = self._create_and_enqueue_task_group(sample_model)
        xrf_entry = self._attach_model_to_group(group_model, xrf_model)
        self.set_xrf_params(xrf_model, xrf_entry, task, sample_model)

        return xrf_model._node_id

    def add_energy_scan(self, node_id: int, task: dict) -> int:
        """Add a energy scan task to the sample with id: <id>.

        :param node_id: id of the sample to which the task belongs
        :param task: task data

        :returns: The queue id of the data collection
        """
        sample_model, _sample_entry = HWR.beamline.queue_manager.get_entry(node_id)
        escan_model = self._create_energy_scan(sample_model)

        group_model, _group_entry = self._create_and_enqueue_task_group(sample_model)
        escan_entry = self._attach_model_to_group(group_model, escan_model)
        self.set_energy_scan_params(escan_model, escan_entry, task, sample_model)

        return escan_model._node_id

    def queue_update_item(self, sqid, tqid, data):
        model, entry = HWR.beamline.queue_manager.get_entry(tqid)
        sample_model, _ = HWR.beamline.queue_manager.get_entry(sqid)

        if data["type"] == "DataCollection":
            self.set_dc_params(model, entry, data, sample_model)
        elif data["type"] == "Characterisation":
            self.set_char_params(model, entry, data, sample_model)

        return model
