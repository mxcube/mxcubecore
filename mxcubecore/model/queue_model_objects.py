# encoding: utf-8
#
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
This module contain objects that combined make up the data model.
Any object that inherhits from TaskNode can be added to and handled by
the QueueModel.
"""
import copy
import os
import logging

from mxcubecore.model import queue_model_enumerables

# This module is used as a self contained entity by the BES
# workflows, so we need to make sure that this module can be
# imported eventhough HardwareRepository is not avilable.
try:
    from mxcubecore import HardwareRepository as HWR
except ImportError as ex:
    logging.getLogger("HWR").exception("Could not import HardwareRepository")


__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class TaskNode(object):
    """
    Objects that inherit TaskNode can be added to and handled by
    the QueueModel object.
    """

    def __init__(self, task_data=None):
        self._children = []
        self._name = str()
        self._number = 0
        self._executed = False
        self._running = False
        self._parent = None
        self._names = {}
        self._enabled = True
        self._node_id = None
        self._requires_centring = True
        self._origin = None
        self._task_data = task_data

    @property
    def task_data(self):
        return self._task_data

    def is_enabled(self):
        """
        :returns: True if enabled and False if disabled
        """
        return self._enabled

    def set_enabled(self, state):
        """
        Sets the enabled state, True represents enabled (executable)
        and false disabled (not executable).

        :param state: The state, True or False
        :type state: bool
        """
        self._enabled = state

    def get_children(self):
        """
        :returns: The children of this node.
        :rtype: List of TaskNode objects.
        """
        return self._children

    def get_parent(self):
        """
        :returns: The parent of this node.
        :rtype: TaskNode
        """
        return self._parent

    def set_name(self, name):
        """
        Sets the name.

        :param name: The new name.
        :type name: str

        :returns: none
        """
        if self.get_parent():
            self._set_name(str(name))
        else:
            self._name = str(name)

    def set_origin(self, node_id):
        """
        Sets the origin of this node, the node id of the node, if any,
        that somehow generated this node.

        :param name: node_id
        :type name: The node id that is the origin of this node

        :returns: none
        """
        self._origin = node_id

    def get_origin(self):
        """
        :returns: The node id that is the origin of this node.
        :rtype: int
        """
        return self._origin

    def set_number(self, number):
        """
        Sets the number of this node. The number can be used
        to give the task a unique number when for instance,
        the name is not unique for this node.

        :param number: number
        :type number: int
        """
        self._number = int(number)

        if self.get_parent():
            # Bumb the run number for nodes with this name
            if self.get_parent()._names[self._name] < number:
                self.get_parent()._names[self._name] = number

    def _set_name(self, name):
        if name in self.get_parent()._names:
            if self.get_parent()._names[name] < self._number:
                self.get_parent()._names[name] = self._number
            else:
                self.get_parent()._names[name] += 1
        else:
            self.get_parent()._names[name] = self._number

        self._name = name

    def get_name(self):
        return "%s - %i" % (self._name, self._number)

    def get_next_number_for_name(self, name):
        num = self._names.get(name)

        if num:
            num += 1
        else:
            num = 1

        return num

    def get_full_name(self):
        name_list = [self.get_name()]
        parent = self._parent

        while parent:
            name_list.append(parent.get_name())
            parent = parent._parent

        return name_list

    def get_display_name(self):
        return self.get_name()

    def get_acq_parameters(self):
        return None

    def get_path_template(self):
        return None

    def get_files_to_be_written(self):
        return []

    def get_centred_positions(self):
        return []

    def set_centred_positions(self, cp):
        pass

    def is_executed(self):
        return self._executed

    def set_executed(self, executed):
        self._executed = executed

    def is_running(self):
        # IK maybe replace is_executed and is_running with state?
        return self._running

    def set_running(self, running):
        self._running = running

    def requires_centring(self):
        return self._requires_centring

    def set_requires_centring(self, state):
        self._requires_centring = state

    def get_root(self):
        parent = self._parent
        root = self

        if parent:
            while parent:
                root = parent
                parent = parent._parent

        return root

    def copy(self):
        new_node = copy.deepcopy(self)
        return new_node

    def __repr__(self):
        s = "<%s object at %s>" % (self.__class__.__name__, hex(id(self)))

        return s

    def get_sample_node(self):
        """get Sample task node that this entry is executed on"""

        result = self
        while result is not None and not isinstance(result, Sample):
            result = result._parent
        #
        return result

    def set_snapshot(self, snapshot):
        pass


class DelayTask(TaskNode):
    """Dummy task, for mock testing only"""

    def __init__(self, delay=10):
        TaskNode.__init__(self)
        self._name = "Delay"
        self.delay = delay


class RootNode(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)
        self._name = "root"
        self._total_node_count = 0


class TaskGroup(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)
        self.lims_group_id = None
        self.interleave_num_images = None
        self.inverse_beam_num_images = None

    def set_name_from_task(self, task):
        if isinstance(task, DataCollection):
            self._name = "Standard"


class Sample(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)

        self.code = str()
        self.lims_code = str()
        self.holder_length = 22.0
        self.lims_id = -1
        self.name = str()
        self.lims_sample_location = -1
        self.lims_container_location = -1
        self.free_pin_mode = False
        self.loc_str = str()
        self.diffraction_plan = None

        # A pair <basket_number, sample_number>
        self.location = (None, None)
        self.lims_location = (None, None)
        self.container_code = None

        # Crystal information
        self.crystals = [Crystal()]
        self.processing_parameters = ProcessingParameters()
        self.processing_parameters.num_residues = 200
        self.processing_parameters.process_data = True
        self.processing_parameters.anomalous = False
        self.processing_parameters.pdb_code = None
        self.processing_parameters.pdb_file = str()

        self.energy_scan_result = EnergyScanResult()

    def __str__(self):
        s = "<%s object at %s>" % (self.__class__.__name__, hex(id(self)))
        return s

    def _print(self):
        print(("sample: %s" % self.loc_str))

    def has_lims_data(self):
        try:
            if int(self.lims_id) > -1:
                return True
        except TypeError:
            return False
        return False

    def get_name(self):
        return self._name

    def get_display_name(self):
        display_name = HWR.beamline.session.get_default_prefix(self)
        if self.lims_code:
            display_name += " (%s)" % self.lims_code
        return display_name

    def init_from_sc_sample(self, sc_sample):
        self.loc_str = str(sc_sample[1]) + ":" + str(sc_sample[2])
        self.location = (sc_sample[1], sc_sample[2])

        self.set_name(self.loc_str)
        if sc_sample[3] != "":
            self.set_name(sc_sample[3])
        else:
            self.set_name(self.loc_str)

    def init_from_lims_object(self, lims_sample):
        if hasattr(lims_sample, "cellA"):
            self.crystals[0].cell_a = lims_sample.cellA
            self.processing_parameters.cell_a = lims_sample.cellA
        else:
            self.crystals[0].cell_a = lims_sample.get("cellA")
            self.processing_parameters.cell_a = lims_sample.get("cellA")

        if hasattr(lims_sample, "cellAlpha"):
            self.crystals[0].cell_alpha = lims_sample.cellAlpha
            self.processing_parameters.cell_alpha = lims_sample.cellAlpha
        else:
            self.crystals[0].cell_alpha = lims_sample.get("cellAlpha")
            self.processing_parameters.cell_alpha = lims_sample.get("cellAlpha")

        if hasattr(lims_sample, "cellB"):
            self.crystals[0].cell_b = lims_sample.cellB
            self.processing_parameters.cell_b = lims_sample.cellB
        else:
            self.crystals[0].cell_b = lims_sample.get("cellB")
            self.processing_parameters.cell_b = lims_sample.get("cellB")

        if hasattr(lims_sample, "cellBeta"):
            self.crystals[0].cell_beta = lims_sample.cellBeta
            self.processing_parameters.cell_beta = lims_sample.cellBeta
        else:
            self.crystals[0].cell_beta = lims_sample.get("cellBeta")
            self.processing_parameters.cell_beta = lims_sample.get("cellBeta")

        if hasattr(lims_sample, "cellC"):
            self.crystals[0].cell_c = lims_sample.cellC
            self.processing_parameters.cell_c = lims_sample.cellC
        else:
            self.crystals[0].cell_c = lims_sample.get("cellC")
            self.processing_parameters.cell_c = lims_sample.get("cellC")

        if hasattr(lims_sample, "cellGamma"):
            self.crystals[0].cell_gamma = lims_sample.cellGamma
            self.processing_parameters.cell_gamma = lims_sample.cellGamma
        else:
            self.crystals[0].cell_gamma = lims_sample.get("cellGamma")
            self.processing_parameters.cell_gamma = lims_sample.get("cellGamma")

        if hasattr(lims_sample, "proteinAcronym"):
            self.crystals[0].protein_acronym = lims_sample.proteinAcronym
            self.processing_parameters.protein_acronym = lims_sample.proteinAcronym
        else:
            self.crystals[0].protein_acronym = lims_sample.get("proteinAcronym")
            self.processing_parameters.protein_acronym = lims_sample.get(
                "proteinAcronym"
            )

        if hasattr(lims_sample, "crystalSpaceGroup"):
            self.crystals[0].space_group = lims_sample.crystalSpaceGroup
            self.processing_parameters.space_group = lims_sample.crystalSpaceGroup
        else:
            self.crystals[0].space_group = lims_sample.get("crystalSpaceGroup")
            self.processing_parameters.space_group = lims_sample.get(
                "crystalSpaceGroup"
            )

        if hasattr(lims_sample, "code"):
            self.lims_code = lims_sample.code
        else:
            self.lims_code = lims_sample.get("code")

        if hasattr(lims_sample, "holderLength"):
            self.holder_length = lims_sample.holderLength
        else:
            self.holder_length = lims_sample.get("holderLength")

        if hasattr(lims_sample, "sampleId"):
            self.lims_id = lims_sample.sampleId
        else:
            self.lims_id = lims_sample.get("sampleId")

        if hasattr(lims_sample, "sampleName"):
            self.name = str(lims_sample.sampleName)
        else:
            self.name = str(lims_sample.get("sampleName"))

        if hasattr(lims_sample, "containerSampleChangerLocation") and hasattr(
            lims_sample, "sampleLocation"
        ):

            if (
                lims_sample.containerSampleChangerLocation
                and lims_sample.sampleLocation
            ):

                self.lims_sample_location = int(lims_sample.sampleLocation)
                self.lims_container_location = int(
                    lims_sample.containerSampleChangerLocation
                )
        else:
            try:
                self.lims_sample_location = int(lims_sample.get("sampleLocation"))
                self.lims_container_location = int(
                    lims_sample.get("containerSampleChangerLocation")
                )
            except Exception:
                pass

        _lims = (self.lims_container_location, self.lims_sample_location)
        self.lims_location = _lims
        self.location = _lims

        self.loc_str = str(self.lims_location[0]) + ":" + str(self.lims_location[1])

        if hasattr(lims_sample, "containerCode"):
            self.container_code = str(lims_sample.containerCode)
        else:
            self.container_code = str(lims_sample.get("containerCode"))

        if hasattr(lims_sample, "diffractionPlan"):
            self.diffraction_plan = lims_sample.diffractionPlan
        else:
            self.diffraction_plan = lims_sample.get("diffractionPlan")
        self.set_name(HWR.beamline.session.get_default_prefix(self))

    def set_from_dict(self, p):
        self.code = p.get("code", "")
        self.lims_code = p.get("limsCode", "")
        self.holder_length = p.get("holderLength", 22.0)
        self.lims_id = p.get("limsID", -1)
        self.lims_sample_location = p.get("sampleLocation", -1)
        self.lims_container_location = p.get("containerSampleChangerLocation", -1)
        self.free_pin_mode = p.get("freePinMode", False)
        self.loc_str = p.get("locStr", "")
        self.diffraction_plan = p.get("diffractionPlan")

        self.crystals[0].space_group = p.get("spaceGroup") or p.get(
            "crystalSpaceGroup", ""
        )
        self.crystals[0].cell_a = p.get("cellA", "")
        self.crystals[0].cell_alpha = p.get("cellAlpha", "")
        self.crystals[0].cell_b = p.get("cellB", "")
        self.crystals[0].cell_beta = p.get("cellBeta", "")
        self.crystals[0].cell_c = p.get("cellC", "")
        self.crystals[0].cell_gamma = p.get("cellGamma", "")
        self.crystals[0].protein_acronym = p.get("proteinAcronym", "")

    def get_processing_parameters(self):
        processing_params = ProcessingParameters()
        processing_params.space_group = self.crystals[0].space_group
        processing_params.cell_a = self.crystals[0].cell_a
        processing_params.cell_alpha = self.crystals[0].cell_alpha
        processing_params.cell_b = self.crystals[0].cell_b
        processing_params.cell_beta = self.crystals[0].cell_beta
        processing_params.cell_c = self.crystals[0].cell_c
        processing_params.cell_gamma = self.crystals[0].cell_gamma
        processing_params.protein_acronym = self.crystals[0].protein_acronym

        return processing_params


class Basket(TaskNode):
    """
    Class represents a basket in the tree. It has not task assigned.
    It represents a parent for samples with the same basket id.
    """

    def __init__(self):
        TaskNode.__init__(self)
        self.name = str()
        self.location = None
        self.free_pin_mode = False
        self.sample_list = []

    @property
    def is_present(self):
        return self.get_is_present()

    def init_from_sc_basket(self, sc_basket, name="Puck"):
        self._basket_object = sc_basket[1]  # self.is_present = sc_basket[2]

        if name == "Row" or self._basket_object is None:
            self.location = sc_basket[0]
            if name == "Row":
                self.name = "%s %s" % (name, chr(65 + self.location))
            else:
                self.name = "%s %d" % (name, self.location)
        else:
            self.location = self._basket_object.get_coords()
            if len(self.location) == 2:
                self.name = "Cell %d, puck %d" % self.location
            elif len(self.location) == 1:
                self.name = "%s %s" % (name, self.location[0])
            else:
                self.name = "%s %s" % (name, self.location)

    def get_name(self):
        return self.name

    def get_location(self):
        return self.location

    def get_is_present(self):
        return self._basket_object.present

    def clear_sample_list(self):
        self.sample_list = []

    def add_sample(self, sample):
        self.sample_list.append(sample)

    def get_sample_list(self):
        return self.sample_list

    def get_display_name(self):
        display_name = self.name
        if self.sample_list:
            for sample in self.sample_list:
                if sample.container_code:
                    display_name += " (%s)" % sample.container_code
                    break

        return display_name


class DataCollection(TaskNode):
    """
    Adds the child node <child>. Raises the exception TypeError
    if child is not of type TaskNode.

    Moves the child (reparents it) if it already has a parent.

    :param parent: Parent TaskNode object.
    :type parent: TaskNode

    :param acquisition_list: List of Acquisition objects.
    :type acquisition_list: list

    :crystal: Crystal object
    :type crystal: Crystal

    :param processing_paremeters: Parameters used by autoproessing software.
    :type processing_parameters: ProcessingParameters

    :returns: None
    :rtype: None
    """

    def __init__(
        self,
        acquisition_list=None,
        crystal=None,
        processing_parameters=None,
        name="",
        task_data=None,
    ):
        TaskNode.__init__(self, task_data=task_data)

        if not acquisition_list:
            acquisition_list = [Acquisition()]

        if not crystal:
            crystal = Crystal()

        if not processing_parameters:
            processing_parameters = ProcessingParameters()

        self.acquisitions = acquisition_list
        self.crystal = crystal
        self.processing_parameters = processing_parameters
        self.set_name(name)

        self.previous_acquisition = None
        self.experiment_type = queue_model_enumerables.EXPERIMENT_TYPE.NATIVE
        self.html_report = str()
        self.id = int()
        self.lims_group_id = None
        self.run_offline_processing = True
        self.run_online_processing = False
        self.grid = None
        self.shape = None
        self.online_processing_results = {"raw": None, "aligned": None}
        self.processing_msg_list = []
        self.workflow_id = None
        self.center_before_collect = False

    @staticmethod
    def set_processing_methods(processing_methods):
        DataCollection.processing_methods = processing_methods

    def as_dict(self):

        acq = self.acquisitions[0]
        path_template = acq.path_template
        parameters = acq.acquisition_parameters

        return {
            "prefix": path_template.get_prefix(),
            "run_number": path_template.run_number,
            "first_image": parameters.first_image,
            "num_images": parameters.num_images,
            "osc_start": parameters.osc_start,
            "osc_range": parameters.osc_range,
            "kappa": parameters.kappa,
            "kappa_phi": parameters.kappa_phi,
            "overlap": parameters.overlap,
            "exp_time": parameters.exp_time,
            "num_passes": parameters.num_passes,
            "path": path_template.directory,
            "centred_position": parameters.centred_position,
            "energy": parameters.energy,
            "resolution": parameters.resolution,
            "transmission": parameters.transmission,
            "detector_binning_mode": parameters.detector_binning_mode,
            "detector_roi_mode": parameters.detector_roi_mode,
            "shutterless": parameters.shutterless,
            "inverse_beam": parameters.inverse_beam,
            "sample": str(self.crystal),
            "acquisitions": str(self.acquisitions),
            "acq_parameters": str(parameters),
            "snapshot": parameters.centred_position.snapshot_image,
        }

    def set_experiment_type(self, exp_type):
        self.experiment_type = exp_type
        if self.experiment_type == queue_model_enumerables.EXPERIMENT_TYPE.MESH:
            self.set_requires_centring(False)

    def is_fast_characterisation(self):
        return self.experiment_type == queue_model_enumerables.EXPERIMENT_TYPE.EDNA_REF

    def is_helical(self):
        return self.experiment_type == queue_model_enumerables.EXPERIMENT_TYPE.HELICAL

    def is_mesh(self):
        return self.experiment_type == queue_model_enumerables.EXPERIMENT_TYPE.MESH

    def is_still(self):
        return self.experiment_type == queue_model_enumerables.EXPERIMENT_TYPE.STILL

    def get_name(self):
        return "%s_%i" % (
            self.acquisitions[0].path_template.get_prefix(),
            self.acquisitions[0].path_template.run_number,
        )

    def is_collected(self):
        return self.is_executed()

    def set_collected(self, collected):
        return self.set_executed(collected)

    def set_comments(self, comments):
        self.acquisitions[0].acquisition_parameters.comments = comments

    def get_acq_parameters(self):
        return self.acquisitions[0].acquisition_parameters

    def get_path_template(self):
        return self.acquisitions[0].path_template

    def get_files_to_be_written(self):
        path_template = self.acquisitions[0].path_template
        file_locations = path_template.get_files_to_be_written()

        return file_locations

    def get_centred_positions(self):
        centred_pos = []
        for pos in self.acquisitions:
            centred_pos.append(pos.acquisition_parameters.centred_position)
        return centred_pos

        # return [self.acquisitions[0].acquisition_parameters.centred_position]

    def set_centred_positions(self, cp):
        self.acquisitions[0].acquisition_parameters.centred_position = cp

    def __str__(self):
        s = "<%s object at %s>" % (self.__class__.__name__, hex(id(self)))
        return s

    def copy(self):
        new_node = copy.deepcopy(self)
        cpos = self.acquisitions[0].acquisition_parameters.centred_position

        if cpos:
            snapshot_image = self.acquisitions[
                0
            ].acquisition_parameters.centred_position.snapshot_image

            if snapshot_image:
                # snapshot_image_copy = snapshot_image.copy()
                acq_parameters = new_node.acquisitions[0].acquisition_parameters
                acq_parameters.centred_position.snapshot_image = None

        return new_node

    def get_point_index(self):
        """
        Descript. : Returns point index associated to the data collection
        Args.     :
        Return    : index (integer)
        """
        cp = self.get_centred_positions()
        return cp[0].get_index()

    def get_helical_point_index(self):
        """
        Descript. : Return indexes of points associated to the helical line
        Args.     :
        Return    : index (integer), index (integer)
        """
        cp = self.get_centred_positions()
        return cp[0].get_index(), cp[1].get_index()

    def set_grid_id(self, grid_id):
        """
        Descript. : Sets grid id associated to the data collection
        Args.     : grid_id (integer)
        Return    :
        """
        self.grid_id = grid_id

    def get_display_name(self):
        """
        Descript. : Returns display name depending from collection type
        Args.     :
        Return    : display_name (string)
        """
        if self.is_helical():
            start_index, end_index = self.get_helical_point_index()
            if None not in (start_index, end_index):
                display_name = "%s (Line %d:%d)" % (
                    self.get_name(),
                    start_index,
                    end_index,
                )
            else:
                display_name = self.get_name()
        elif self.is_mesh():
            display_name = "%s (%s)" % (self.get_name(), self.grid.get_display_name())
        else:
            if self.requires_centring():
                index = self.get_point_index()
                if index:
                    index = str(index)
                else:
                    index = "not defined"
                display_name = "%s (Point %s)" % (self.get_name(), index)
            else:
                display_name = self.get_name()
        return display_name

    def set_online_processing_results(self, raw, aligned):
        self.online_processing_results["raw"] = raw
        self.online_processing_results["aligned"] = aligned

    def get_online_processing_results(self):
        return self.online_processing_results

    def set_snapshot(self, snapshot):
        self.acquisitions[
            0
        ].acquisition_parameters.centred_position.snapshot_image = snapshot

    def add_processing_msg(self, time, method, status, msg):
        self.processing_msg_list.append((time, method, status, msg))


class ProcessingParameters(object):
    def __init__(self):
        self.space_group = 0
        self.cell_a = 0
        self.cell_alpha = 0
        self.cell_b = 0
        self.cell_beta = 0
        self.cell_c = 0
        self.cell_gamma = 0
        self.protein_acronym = ""
        self.num_residues = 200
        self.process_data = True
        self.anomalous = False
        self.pdb_code = None
        self.pdb_file = str()
        self.resolution_cutoff = 2.0

    def get_cell_str(self):
        return ",".join(
            map(
                str,
                (
                    self.cell_a,
                    self.cell_b,
                    self.cell_c,
                    self.cell_alpha,
                    self.cell_beta,
                    self.cell_gamma,
                ),
            )
        )


class Characterisation(TaskNode):
    def __init__(
        self, ref_data_collection=None, characterisation_parameters=None, name=""
    ):
        TaskNode.__init__(self)

        if not characterisation_parameters:
            characterisation_parameters = CharacterisationParameters()

        if not ref_data_collection:
            ref_data_collection = DataCollection()

        self.reference_image_collection = ref_data_collection
        self.characterisation_parameters = characterisation_parameters
        self.set_name(name)

        self.html_report = None
        self.run_characterisation = True
        self.characterisation_software = None
        self.wait_result = None
        self.run_diffraction_plan = None

        self.auto_add_diff_plan = True
        self.diffraction_plan = []

    @staticmethod
    def set_char_compression(state):
        Characterisation.diff_plan_compression = state

    def get_name(self):
        return "%s_%i" % (self._name, self._number)

    def set_comments(self, comments):
        self.reference_image_collection.acquisitions[
            0
        ].acquisition_parameters.comments = comments

    def get_acq_parameters(self):
        return self.reference_image_collection.acquisitions[0].acquisition_parameters

    def get_path_template(self):
        return self.reference_image_collection.acquisitions[0].path_template

    def get_files_to_be_written(self):
        path_template = self.reference_image_collection.acquisitions[0].path_template

        file_locations = path_template.get_files_to_be_written()

        return file_locations

    def get_centred_positions(self):
        return [
            self.reference_image_collection.acquisitions[
                0
            ].acquisition_parameters.centred_position
        ]

    def set_centred_positions(self, cp):
        self.reference_image_collection.acquisitions[
            0
        ].acquisition_parameters.centred_position = cp

    def copy(self):
        new_node = copy.deepcopy(self)
        new_node.reference_image_collection = self.reference_image_collection.copy()

        return new_node

    def get_point_index(self):
        """
        Descript. : Returns point index associated to the data collection
        Args.     :
        Return    : index (integer)
        """
        cp = self.get_centred_positions()
        return cp[0].get_index()

    def get_display_name(self):
        """
        Descript. : Returns display name of the collection
        Args.     :
        Return    : display_name (string)
        """
        index = self.get_point_index()
        if index:
            index = str(index)
        else:
            index = "not defined"
        display_name = "%s (Point - %s)" % (self.get_name(), index)
        return display_name

    def set_snapshot(self, snapshot):
        self.reference_image_collection.acquisitions[
            0
        ].acquisition_parameters.centred_position.snaphot_image = snapshot


class CharacterisationParameters(object):
    def __init__(self):
        # Setting num_ref_images to EDNA_NUM_REF_IMAGES.NONE
        # will disable characterisation.
        self.path_template = PathTemplate()
        self.experiment_type = 0

        # Optimisation parameters
        self.use_aimed_resolution = bool()
        self.aimed_resolution = float()
        self.use_aimed_multiplicity = bool()
        self.aimed_multiplicity = int()
        self.aimed_i_sigma = float()
        self.aimed_completness = float()
        self.strategy_complexity = int()
        self.induce_burn = bool()
        self.use_permitted_rotation = bool()
        self.permitted_phi_start = float()
        self.permitted_phi_end = float()
        self.low_res_pass_strat = bool()

        # Crystal
        self.max_crystal_vdim = float()
        self.min_crystal_vdim = float()
        self.max_crystal_vphi = float()
        self.min_crystal_vphi = float()
        self.space_group = ""

        # Characterisation type
        self.use_min_dose = bool()
        self.use_min_time = bool()
        self.min_dose = float()
        self.min_time = float()
        self.account_rad_damage = bool()
        self.auto_res = bool()
        self.opt_sad = bool()
        self.sad_res = float()
        self.determine_rad_params = bool()
        self.burn_osc_start = float()
        self.burn_osc_interval = int()

        # Radiation damage model
        self.rad_suscept = float()
        self.beta = float()
        self.gamma = float()

    def as_dict(self):
        return {
            "experiment_type": self.experiment_type,
            "use_aimed_resolution": self.use_aimed_resolution,
            "use_aimed_multiplicity": self.use_aimed_multiplicity,
            "aimed_multiplicity": self.aimed_multiplicity,
            "aimed_i_sigma": self.aimed_i_sigma,
            "aimed_completness": self.aimed_completness,
            "strategy_complexity": self.strategy_complexity,
            "induce_burn": self.induce_burn,
            "use_permitted_rotation": self.use_permitted_rotation,
            "permitted_phi_start": self.permitted_phi_start,
            "permitted_phi_end": self.permitted_phi_end,
            "low_res_pass_strat": self.low_res_pass_strat,
            "max_crystal_vdim": self.max_crystal_vdim,
            "min_crystal_vdim": self.min_crystal_vdim,
            "max_crystal_vphi": self.max_crystal_vphi,
            "min_crystal_vphi": self.min_crystal_vphi,
            "space_group": self.space_group,
            "use_min_dose": self.use_min_dose,
            "use_min_time": self.use_min_time,
            "min_dose": self.min_dose,
            "min_time": self.min_time,
            "account_rad_damage": self.account_rad_damage,
            "auto_res": self.auto_res,
            "opt_sad": self.opt_sad,
            "sad_res": self.sad_res,
            "determine_rad_params": self.determine_rad_params,
            "burn_osc_start": self.burn_osc_start,
            "burn_osc_interval": self.burn_osc_interval,
            "rad_suscept": self.rad_suscept,
            "beta": self.beta,
            "gamma": self.gamma,
        }

    def set_from_dict(self, params_dict):
        for dict_item in params_dict.items():
            if hasattr(self, dict_item[0]):
                setattr(self, dict_item[0], dict_item[1])

    def __repr__(self):
        s = "<%s object at %s>" % (self.__class__.__name__, hex(id(self)))

        return s


class EnergyScan(TaskNode):
    def __init__(self, sample=None, path_template=None, cpos=None):
        TaskNode.__init__(self)
        self.element_symbol = None
        self.edge = None
        self.comments = None
        self.set_requires_centring(True)
        self.centred_position = cpos

        if not sample:
            self.sample = Sample()
        else:
            self.sample = sample

        if not path_template:
            self.path_template = PathTemplate()
        else:
            self.path_template = path_template

        self.result = EnergyScanResult()

    def get_run_number(self):
        return self.path_template.run_number

    def get_prefix(self):
        return self.path_template.get_prefix()

    def set_comments(self, comments):
        self.comments = comments

    def get_path_template(self):
        return self.path_template

    def set_scan_result_data(self, data):
        self.result.data = data

    def get_scan_result(self):
        return self.result

    def is_collected(self):
        return self.is_executed()

    def set_collected(self, collected):
        return self.set_executed(collected)

    def get_point_index(self):
        if self.centred_position:
            return self.centred_position.get_index()

    def get_display_name(self):
        index = self.get_point_index()
        if index:
            index = str(index)
        else:
            index = "not defined"
        display_name = "%s (%s %s, Point - %s)" % (
            self.get_name(),
            self.element_symbol,
            self.edge,
            index,
        )
        return display_name

    def copy(self):
        new_node = copy.deepcopy(self)
        cpos = self.centred_position
        if cpos:
            snapshot_image = self.centred_position.snapshot_image
            if snapshot_image:
                snapshot_image_copy = snapshot_image.copy()
                new_node.centred_position.snapshot_image = snapshot_image_copy
        return new_node

    def set_snapshot(self, snapshot):
        self.centred_position.snapshot_image = snapshot


class EnergyScanResult(object):
    def __init__(self):
        object.__init__(self)
        self.inflection = None
        self.peak = None
        self.first_remote = None
        self.second_remote = None
        self.data_file_path = PathTemplate()

        self.data = []

        self.pk = None
        self.fppPeak = None
        self.fpPeak = None
        self.ip = None
        self.fppInfl = None
        self.fpInfl = None
        self.rm = None
        self.chooch_graph_x = None
        self.chooch_graph_y1 = None
        self.chooch_graph_y2 = None
        self.title = None


class XRFSpectrum(TaskNode):
    """
    Class represents XRF spectrum task
    """

    def __init__(self, sample=None, path_template=None, cpos=None):
        TaskNode.__init__(self)
        self.count_time = 1
        self.comments = None
        self.set_requires_centring(True)
        self.centred_position = cpos
        self.adjust_transmission = True

        if not sample:
            self.sample = Sample()
        else:
            self.sample = sample

        if not path_template:
            self.path_template = PathTemplate()
        else:
            self.path_template = path_template

        self.result = XRFSpectrumResult()

    def get_run_number(self):
        return self.path_template.run_number

    def get_prefix(self):
        return self.path_template.get_prefix()

    def get_path_template(self):
        return self.path_template

    def get_point_index(self):
        if self.centred_position:
            return self.centred_position.get_index()

    def get_display_name(self):
        index = self.get_point_index()
        if index:
            index = str(index)
        else:
            index = "not defined"
        display_name = "%s (Point - %s)" % (self.get_name(), index)
        return display_name

    def set_count_time(self, count_time):
        self.count_time = count_time

    def is_collected(self):
        return self.is_executed()

    def set_collected(self, collected):
        return self.set_executed(collected)

    def set_comments(self, comments):
        self.comments = comments

    def get_spectrum_result(self):
        return self.result

    def copy(self):
        new_node = copy.deepcopy(self)
        cpos = self.centred_position
        if cpos:
            snapshot_image = self.centred_position.snapshot_image
            if snapshot_image:
                snapshot_image_copy = snapshot_image.copy()
                new_node.centred_position.snapshot_image = snapshot_image_copy
        return new_node

    def set_snaphot(self, snapshot):
        self.centred_position.snapshot_image = snapshot


class XRFSpectrumResult(object):
    def __init__(self):
        object.__init__(self)
        self.mca_data = None
        self.mca_calib = None
        self.mca_config = None


class XrayCentering(TaskNode):
    def __init__(self, ref_data_collection=None, crystal=None):
        TaskNode.__init__(self)

        self.set_requires_centring(False)
        if not ref_data_collection:
            ref_data_collection = DataCollection()

        if not crystal:
            crystal = Crystal()

        self.reference_image_collection = ref_data_collection

        self.line_collection = ref_data_collection.copy()
        self.line_collection.set_experiment_type(
            queue_model_enumerables.EXPERIMENT_TYPE.HELICAL
        )
        self.line_collection.run_online_processing = "XrayCentering"
        self.line_collection.grid = None

        acq_two = Acquisition()
        self.line_collection.acquisitions.append(acq_two)
        self.line_collection.acquisitions[0].acquisition_parameters.num_images = 100
        self.line_collection.acquisitions[0].acquisition_parameters.num_lines = 1
        helical_acq_path_template = self.line_collection.acquisitions[0].path_template
        helical_acq_path_template.base_prefix = (
            "line_" + helical_acq_path_template.base_prefix
        )

        self.crystal = crystal

        self.html_report = None

    def get_display_name(self):
        return "Xray centring"

    def get_path_template(self):
        return self.reference_image_collection.acquisitions[0].path_template

    def get_files_to_be_written(self):
        path_template = self.reference_image_collection.acquisitions[0].path_template
        file_locations = path_template.get_files_to_be_written()
        return file_locations

    def add_task(self, task):
        pass


class XrayCentring2(TaskNode):
    """X-ray centring (2022 version)

    Contains all parameters necessary for X-ray centring
    This object is passed to the QueueEntry and HardwareObject
    Parameters not defined here must be set as defaults, somehow
    (transmission, grid step, ...)
    """

    def __init__(self, name=None, motor_positions=None, grid_size=None):
        """

        :param name: (str) Task name - for queue display. Default to std. name
        :param motor_positions: (dict) Motor positions for centring (default to current)
        :param grid_size: (tuple) grid_size_x, grid_size_y (in mm)
        """
        TaskNode.__init__(self)
        self._centring_result = None
        self._motor_positions = motor_positions.copy() if motor_positions else {}
        self._grid_size = tuple(grid_size) if grid_size else None

        # I do nto now if you need a path template; if not remove this
        # and the access to it in init_from_task_data
        self.path_template = PathTemplate()

        if name:
            self.set_name(name)

    def get_name(self):
        return self._name

    def get_motor_positions(self):
        return self._motor_positions.copy()

    def set_motor_positions(self, value):
        self._motor_positions = dict(value) if value else {}

    def get_grid_size(self):
        return self._grid_size

    def set_grid_size(self, value):
        self._grid_size = tuple(value) if value else None

    def get_centring_result(self):
        return self._centring_result

    def set_centring_result(self, value):
        if value is None or isinstance(value, CentredPosition):
            self._centring_result = value
        else:
            raise TypeError(
                "SampleCentring.centringResult must be a CentredPosition"
                " or None, was a %s" % value.__class__.__name__
            )

    def init_from_task_data(self, sample_model, params):
        """Set parameters from task input dictionary.

        sample_model is required as this may be called before the object is enqueued
        params is a dictionary with structure determined by mxcube3 usage
        """

        # Set path template
        self.path_template.set_from_dict(params)
        if params["prefix"]:
            self.path_template.base_prefix = params["prefix"]
        else:
            self.path_template.base_prefix = HWR.beamline.session.get_default_prefix(
                sample_model
            )
        self.path_template.num_files = 0
        self.path_template.directory = os.path.join(
            HWR.beamline.session.get_base_image_directory(), params.get("subdir", "")
        )
        self.path_template.process_directory = os.path.join(
            HWR.beamline.session.get_base_process_directory(),
            params.get("subdir", ""),
        )

        # Set paramaters from params dict
        if "name" in params:
            self.set_name(params["name"])
        if "motor_positions" in params:
            self.set_motor_positions(params["motor_positions"])
        if "grid_size" in params:
            self.set_grid_size(params["grid_size"])


class SampleCentring(TaskNode):
    """Manual 3 click centering

    kappa and kappa_phi settings are applied first, and assume that the
    beamline does have axes with exactly these names

    Other motor_positions are applied afterwards, but in random order.
    motor_positions override kappa and kappa_phi if both are set

    Since setting one motor can change the position of another
    (on ESRF ID30B setting kappa and kappa_phi changes the translation motors)
     the order is important.

    """

    def __init__(self, name=None, kappa=None, kappa_phi=None, motor_positions=None):
        TaskNode.__init__(self)
        self._tasks = []
        self._other_motor_positions = motor_positions.copy() if motor_positions else {}
        self._centring_result = None

        if name:
            self.set_name(name)

        if "kappa" in self._other_motor_positions:
            kappa = self._other_motor_positions.pop("kappa")

        if "kappa_phi" in self._other_motor_positions:
            kappa_phi = self._other_motor_positions.pop("kappa_phi")

        self.kappa = kappa
        self.kappa_phi = kappa_phi

    def add_task(self, task_node):
        self._tasks.append(task_node)

    def get_tasks(self):
        return self._tasks

    def get_name(self):
        return self._name

    def get_kappa(self):
        return self.kappa

    def get_kappa_phi(self):
        return self.kappa_phi

    def get_other_motor_positions(self):
        return self._other_motor_positions.copy()

    def get_centring_result(self):
        return self._centring_result

    def set_centring_result(self, value):
        if value is None or isinstance(value, CentredPosition):
            self._centring_result = value
        else:
            raise TypeError(
                "SampleCentring.centringResult must be a CentredPosition"
                " or None, was a %s" % value.__class__.__name__
            )


class OpticalCentring(TaskNode):
    """Optical automatic centering with lucid"""

    def __init__(self, user_confirms=False):
        TaskNode.__init__(self)

        if user_confirms:
            self.set_name("Optical automatic centring (user confirms)")
        else:
            self.set_name("Optical automatic centring")
        if user_confirms:
            self.try_count = 3
        else:
            self.try_count = 1

    def add_task(self, task_node):
        pass

    def get_name(self):
        return self._name


class Acquisition(object):
    def __init__(self):
        object.__init__(self)

        self.path_template = PathTemplate()
        self.acquisition_parameters = AcquisitionParameters()

    def get_preview_image_paths(self):
        """
        Returns the full paths, including the filename, to preview/thumbnail
        images stored in the archive directory.

        :param acquisition: The acqusition object to generate paths for.
        :type acquisition: Acquisition

        :returns: The full paths.
        :rtype: str
        """
        paths = []

        for i in range(
            self.acquisition_parameters.first_image,
            self.acquisition_parameters.num_images
            + self.acquisition_parameters.first_image,
        ):

            path = os.path.join(
                self.path_template.get_archive_directory(),
                self.path_template.get_image_file_name(suffix="thumb.jpeg") % i,
            )

            paths.append(path)
        return paths


class PathTemplate(object):
    @staticmethod
    def set_data_base_path(base_directory):
        # os.path.abspath returns path without trailing slash, if any
        # eg. '/data/' => '/data'.
        PathTemplate.base_directory = os.path.abspath(base_directory)

    @staticmethod
    def set_archive_path(archive_base_directory, archive_folder):
        PathTemplate.archive_base_directory = os.path.abspath(archive_base_directory)
        PathTemplate.archive_folder = archive_folder

    @staticmethod
    def set_path_template_style(synchrotron_name, template=None):
        PathTemplate.synchrotron_name = synchrotron_name
        PathTemplate.template = template

    @staticmethod
    def set_precision(precision):
        PathTemplate.precision = precision

    @staticmethod
    def interpret_path(path):
        try:
            dirname, fname = os.path.split(path)
            fname, ext = os.path.splitext(fname)
            fname_parts = fname.split("_")

            # Get run number and image number from path
            run_number, img_number = map(try_parse_int, fname_parts[-2:])

            # Get the prefix and filename part
            prefix = "_".join(fname_parts[:-2])
            prefix_path = os.path.join(dirname, prefix)
        except IndexError:
            prefix_path, run_number, img_number = ["", -1, -1]

        return prefix_path, run_number, img_number

    def __init__(self):
        object.__init__(self)

        self.directory = str()
        self.process_directory = str()
        self.xds_dir = str()
        self.base_prefix = str()
        self.mad_prefix = str()
        self.reference_image_prefix = str()
        self.wedge_prefix = str()
        self.run_number = int()
        self.suffix = str()
        self.start_num = int()
        self.num_files = int()
        self.compression = False

        if not hasattr(self, "precision"):
            self.precision = str()

    def as_dict(self):
        return {
            "directory": self.directory,
            "process_directory": self.process_directory,
            "xds_dir": self.xds_dir,
            "base_prefix": self.base_prefix,
            "mad_prefix": self.mad_prefix,
            "reference_image_prefix": self.reference_image_prefix,
            "wedge_prefix": self.wedge_prefix,
            "run_number": self.run_number,
            "suffix": self.suffix,
            "precision": self.precision,
            "start_num": self.start_num,
            "num_files": self.num_files,
            "compression": self.compression,
        }

    def set_from_dict(self, params_dict):
        for dict_item in params_dict.items():
            if hasattr(self, dict_item[0]):
                setattr(self, dict_item[0], dict_item[1])

    def get_prefix(self):
        prefix = self.base_prefix

        if self.mad_prefix:
            prefix = str(self.base_prefix) + "-" + str(self.mad_prefix)

        if self.reference_image_prefix:
            prefix = self.reference_image_prefix + "-" + prefix

        if self.wedge_prefix:
            prefix = prefix + "_" + self.wedge_prefix

        return prefix

    def get_image_file_name(self, suffix=None):
        template = "%s_%s_%%0" + str(self.precision) + "d.%s"

        if suffix:
            file_name = template % (self.get_prefix(), self.run_number, suffix)
        else:
            file_name = template % (self.get_prefix(), self.run_number, self.suffix)
        if self.compression:
            file_name = "%s.gz" % file_name

        return file_name

    def get_image_path(self):
        path = os.path.join(self.directory, self.get_image_file_name())
        return path

    def get_archive_directory(self):
        """
        Returns the archive directory, for longer term storage. synchrotron_name
        is set via static function calles from session hwobj

        :rtype: str
        :returns: Archive directory
        """
        folders = self.directory.split("/")
        if PathTemplate.synchrotron_name == "MAXLAB":
            archive_directory = self.directory
            archive_directory = archive_directory.replace(
                "/data/data1/visitor", "/data/ispyb"
            )
            archive_directory = archive_directory.replace(
                "/data/data1/inhouse", "/data/ispyb"
            )
            archive_directory = archive_directory.replace("/data/data1", "/data/ispyb")

        elif PathTemplate.synchrotron_name == "EMBL-HH":
            archive_directory = os.path.join(
                PathTemplate.archive_base_directory,
                PathTemplate.archive_folder,
                *folders[4:]
            )
        elif PathTemplate.synchrotron_name == "ALBA":
            logging.getLogger("HWR").debug(
                "PathTemplate (ALBA) - directory is %s" % self.directory
            )
            directory = self.directory
            folders = directory.split(os.path.sep)
            user_dir = folders[5]
            session_date = folders[6]
            try:
                more = folders[8:]
            except Exception:
                more = []
            archive_directory = os.path.join(
                PathTemplate.archive_base_directory, user_dir, session_date, *more
            )
            logging.getLogger("HWR").debug(
                "PathTemplate (ALBA) - archive_directory is %s" % archive_directory
            )
        else:
            directory = self.directory[len(PathTemplate.base_directory) :]
            folders = directory.split("/")
            if "visitor" in folders:
                endstation_name = folders[3]
                folders[1] = PathTemplate.archive_folder
                folders[3] = folders[2]
                folders[2] = endstation_name
            else:
                endstation_name = folders[1]
                folders[1] = PathTemplate.archive_folder
                folders[2] = endstation_name

            archive_directory = os.path.join(
                PathTemplate.archive_base_directory, *folders[1:]
            )
        return archive_directory

    def __eq__(self, path_template):
        result = False
        lh_dir = os.path.normpath(self.directory)
        rh_dir = os.path.normpath(path_template.directory)

        if self.get_prefix() == path_template.get_prefix() and lh_dir == rh_dir:
            result = True

        return result

    def intersection(self, rh_pt):
        result = False

        # Only do the intersection if there is possibilty for
        # Collision, that is directories are the same.
        if (self == rh_pt) and (self.run_number == rh_pt.run_number):
            if self.start_num < (
                rh_pt.start_num + rh_pt.num_files
            ) and rh_pt.start_num < (self.start_num + self.num_files):

                result = True

        return result

    def get_files_to_be_written(self):
        file_locations = []
        file_name_template = self.get_image_file_name()

        for i in range(self.start_num, self.start_num + self.num_files):

            file_locations.append(os.path.join(self.directory, file_name_template % i))

        return file_locations

    def is_part_of(self, path_template):
        result = False

        if self == path_template and self.run_number == path_template.run_number:
            if (
                path_template.start_num >= self.start_num
                and path_template.num_files + path_template.start_num
                <= self.num_files + self.start_num
            ):

                result = True
        else:
            result = False

        return result

    def copy(self):
        return copy.deepcopy(self)


class AcquisitionParameters(object):
    def __init__(self):
        object.__init__(self)

        self.first_image = int()
        self.num_images = int()
        self.osc_start = float()
        self.osc_range = float()
        self.osc_total_range = float()
        self.overlap = float()
        self.kappa = float()
        self.kappa_phi = float()
        self.exp_time = float()
        self.num_passes = int()
        self.num_lines = 1
        self.energy = float()
        self.centred_position = CentredPosition()
        self.resolution = float()
        # detector_distance used if resolution is 0 or None
        self.detector_distance = float()
        self.transmission = float()
        self.inverse_beam = False
        self.shutterless = False
        self.take_snapshots = True
        self.take_video = False
        self.take_dark_current = True
        self.skip_existing_images = False
        self.detector_binning_mode = str()
        self.detector_roi_mode = str()
        self.induce_burn = False
        self.mesh_range = ()
        self.cell_counting = "zig-zag"
        self.mesh_center = "top-left"
        self.cell_spacing = (0, 0)
        self.mesh_snapshot = None
        self.comments = ""
        self.in_queue = False
        self.in_interleave = None
        self.sub_wedge_size = 10

        self.num_triggers = int()
        self.num_images_per_trigger = int()
        self.hare_num = 1

    def set_from_dict(self, params_dict):
        for item in params_dict.items():
            if hasattr(self, item[0]):
                if item[0] == "centred_position":
                    self.centred_position.set_from_dict(item[1])
                else:
                    setattr(self, item[0], item[1])

    def as_dict(self):
        return {
            "first_image": self.first_image,
            "num_images": self.num_images,
            "osc_start": self.osc_start,
            "osc_range": self.osc_range,
            "osc_total_range": self.osc_total_range,
            "overlap": self.overlap,
            "kappa": self.kappa,
            "kappa_phi": self.kappa_phi,
            "exp_time": self.exp_time,
            "num_passes": self.num_passes,
            "num_lines": self.num_lines,
            "energy": self.energy,
            "resolution": self.resolution,
            "detector_distance": self.detector_distance,
            "transmission": self.transmission,
            "inverse_beam": self.inverse_beam,
            "shutterless": self.shutterless,
            "take_snapshots": self.take_snapshots,
            "take_video": self.take_video,
            "take_dark_current": self.take_dark_current,
            "skip_existing_images": self.skip_existing_images,
            "detector_binning_mode": self.detector_binning_mode,
            "detector_roi_mode": self.detector_roi_mode,
            "induce_burn": self.induce_burn,
            "mesh_range": self.mesh_range,
            "mesh_snapshot": self.mesh_snapshot,
            "comments": self.comments,
            "in_queue": self.in_queue,
            "in_interleave": self.in_interleave,
            "num_triggers": self.num_triggers,
            "num_images_per_trigger": self.num_images_per_trigger,
            "cell_counting": self.cell_counting,
            "mesh_center": self.mesh_center,
            "cell_spacing": self.cell_spacing,
            "sub_wedge_size": self.sub_wedge_size,
        }

    def copy(self):
        return copy.deepcopy(self)


class XrayImagingParameters(object):
    def __init__(self):
        object.__init__(self)

        self.ff_num_images = 30
        self.ff_pre = False
        self.ff_post = False
        self.ff_apply = False
        self.ff_ssim_enabled = False

        self.sample_offset_a = 0.0
        self.sample_offset_b = -1.0
        self.sample_offset_c = 0.0

        self.camera_trigger = True
        self.camera_live_view = False

        self.camera_hw_binning = 0
        self.camera_hw_roi = 0
        self.camera_write_data = True

        self.detector_distance = float()

    def copy(self):
        return copy.deepcopy(self)

    def as_dict(self):
        return {
            "ff_num_images": self.ff_num_images,
            "ff_pre": self.ff_pre,
            "ff_post": self.ff_post,
            "ff_apply": self.ff_apply,
            "ff_ssim_enabled": self.ff_ssim_enabled,
            "sample_offset_a": self.sample_offset_a,
            "sample_offset_b": self.sample_offset_b,
            "sample_offset_c": self.sample_offset_c,
            "camera_trigger": self.camera_trigger,
            "camera_live_view": self.camera_live_view,
            "camera_write_data": self.camera_write_data,
            "detector_distance": self.detector_distance,
        }


class Crystal(object):
    def __init__(self):
        object.__init__(self)
        self.space_group = 0
        self.cell_a = 0
        self.cell_alpha = 0
        self.cell_b = 0
        self.cell_beta = 0
        self.cell_c = 0
        self.cell_gamma = 0
        self.protein_acronym = ""

        # MAD energies
        self.energy_scan_result = EnergyScanResult()

    def set_from_dict(self, params_dict):
        for dict_item in params_dict.items():
            if hasattr(self, dict_item[0]):
                setattr(self, dict_item[0], dict_item[1])


class CentredPosition(object):
    """
    Class that represents a centred position.
    Can also be initialized with a mxcube motor dict
    which simply is a dictonary with the motornames and
    their corresponding values.
    """

    MOTOR_POS_DELTA = 1e-4
    DIFFRACTOMETER_MOTOR_NAMES = []

    @staticmethod
    def set_diffractometer_motor_names(*names):
        CentredPosition.DIFFRACTOMETER_MOTOR_NAMES = names[:]

    def __init__(self, motor_dict=None):
        self.snapshot_image = None
        self.centring_method = True
        self.index = None
        self.motor_pos_delta = CentredPosition.MOTOR_POS_DELTA

        for motor_name in CentredPosition.DIFFRACTOMETER_MOTOR_NAMES:
            setattr(self, motor_name, None)

        if motor_dict is not None:
            for motor_name, position in motor_dict.items():
                setattr(self, motor_name, position)

    def as_dict(self):
        return dict(
            zip(
                CentredPosition.DIFFRACTOMETER_MOTOR_NAMES,
                [
                    getattr(self, motor_name)
                    for motor_name in CentredPosition.DIFFRACTOMETER_MOTOR_NAMES
                ],
            )
        )

    def set_from_dict(self, params_dict):
        for dict_item in params_dict.items():
            if hasattr(self, dict_item[0]):
                setattr(self, dict_item[0], dict_item[1])

    def as_str(self):
        motor_str = ""
        for motor_name in CentredPosition.DIFFRACTOMETER_MOTOR_NAMES:
            if getattr(self, motor_name):
                motor_str += "%s: %.3f " % (motor_name, abs(getattr(self, motor_name)))
        return motor_str

    def __repr__(self):
        return str(self.as_dict())

    def __eq__(self, cpos):
        eq = len(CentredPosition.DIFFRACTOMETER_MOTOR_NAMES) * [False]
        for i, motor_name in enumerate(CentredPosition.DIFFRACTOMETER_MOTOR_NAMES):
            self_pos = getattr(self, motor_name)
            if not hasattr(cpos, motor_name):
                continue
            else:
                cpos_pos = getattr(cpos, motor_name)

            if self_pos == cpos_pos is None:
                eq[i] = True
            elif None in (self_pos, cpos_pos):
                continue
            else:
                eq[i] = abs(self_pos - cpos_pos) <= self.motor_pos_delta
        return all(eq)

    def __ne__(self, cpos):
        return not (self == cpos)

    def set_index(self, index):
        self.index = index

    def set_motor_pos_delta(self, delta):
        self.motor_pos_delta = delta

    def get_index(self):
        return self.index

    def get_kappa_value(self):
        return self.kappa

    def get_kappa_phi_value(self):
        return self.kappa_phi


class Workflow(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)
        self.path_template = PathTemplate()
        self._type = str()
        self.set_requires_centring(False)
        self.lims_id = None

    def set_type(self, workflow_type):
        self._type = workflow_type

    def get_type(self):
        return self._type

    def get_path_template(self):
        return self.path_template


class GphlWorkflow(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)

        workflow_hwobj = HWR.beamline.gphl_workflow

        # Workflow start attributes
        self.path_template = PathTemplate()
        self._type = str()
        self.shape = str()
        self.characterisation_strategy = str()
        self.maximum_dose_budget = 20.0
        self.decay_limit = 25
        self.characterisation_budget_fraction = 0.05
        self.relative_rad_sensitivity = 1.0

        # string. Only active mode currently is 'MASSIF1'
        self.automation_mode = None
        # Automation mode acquisition parameters. Replace UI queried values
        # multiple dictionaries, in acquisition order (characterisation, then main)
        self.auto_acq_parameters = [{}]

        # Pre-strategy attributes
        # Set in  def set_pre_strategy_params(
        self.input_space_group = str()
        self.space_group = str()
        self.crystal_classes = ()
        self._cell_parameters = ()
        self.detector_setting = None  # from 'resolution' parameter or defaults
        self.aimed_resolution = None  # from 'resolution' parameter or defaults
        self.wavelengths = ()  # from 'energies' parametes
        self.use_cell_for_processing = False
        self.strategy_options = {}  # includes variant. Overrides config/defuault
        # Directory containing SPOT.XDS file
        # For cases where characterisation and XDS processing are done
        # before workflow is started
        self.init_spot_dir = None

        # Pre-collection attributes
        # Attributes for workflow
        self.exposure_time = 0.0
        self.image_width = 0.0
        self.wedge_width = 0.0
        self.transmission = 0.0
        self.snapshot_count = 2
        self.recentring_mode = "sweep"
        self.repetition_count = 1

        # Internal / config-only attributes
        # Workflow interleave order (string).
        # Slowest changing first, characters 'g' (Goniostat position);
        # 's' (Scan number), 'b' (Beam wavelength), 'd' (Detector position)
        self.interleave_order = "gs"  # from workflow strategy
        self.beamstop_setting = None  # Not currently set or used
        self.goniostat_translations = ()  # Internal only - set by program
        self.current_rotation_id = None
        self.characterisation_done = False
        self.characterisation_dose = 0.0
        self.acquisition_dose = 0.0
        self.strategy_length = 0.0

        # # Centring handling and MXCuBE-side flow
        self.set_requires_centring(False)

        self.set_from_dict(workflow_hwobj.settings["defaults"])

    def parameter_summary(self):
        """Main parameter summary, for output purposes"""
        summary = {"strategy":self.get_type()}
        for tag in (
            "automation_mode",
            "init_spot_dir",
            "exposure_time",
            "image_width",
            "strategy_length",
            "transmission",
            "input_space_group",
            "space_group",
            "crystal_classes",
            "_cell_parameters",
            "use_cell_for_processing",
            "relative_rad_sensitivity",
            "aimed_resolution",
            "repetition_count",
        ):
            summary[tag] = getattr(self, tag)
        summary["wavelengths"] = tuple(x.wavelength for x in self.wavelengths)
        summary["resolution"] = self.detector_setting.resolution
        summary["orgxy"] = self.detector_setting.orgxy
        summary["strategy_variant"] = self.strategy_options.get("variant", "not set")
        summary["orientation_count"] = len(self.goniostat_translations)
        summary["radiation_dose"] = self.calculate_dose()
        summary["total_dose_budget"] = self.recommended_dose_budget()
        #
        return summary

    def set_from_dict(self, params_dict):
        for dict_item in params_dict.items():
            if hasattr(self, dict_item[0]):
                setattr(self, dict_item[0], dict_item[1])

    def set_pre_strategy_params(
            self,
            crystal_classes=(),
            input_space_group="",
            space_group="",
            cell_parameters=(),
            resolution=None,
            energies=(),
            strategy_options=None,
            init_spot_dir=None,
            use_cell_for_processing=False,
            **unused):
        """

        :param crystal_classes (tuple(str)):
        :param space_group (str):
        :param cell_parameters tuple(float):
        :param resolution (Optional[float]):
        :param energies tuple(float):
        :param strategy_options (dict):
        :param init_spot_dir (str):
        :param unused (dict):
        :return (None):
        """

        from mxcubecore.HardwareObjects.Gphl import GphlMessages

        self.input_space_group = input_space_group
        self.space_group = space_group
        self.crystal_classes = tuple(crystal_classes)
        if cell_parameters:
            self.cell_parameters = cell_parameters

        workflow_parameters = self.get_workflow_parameters()

        interleave_order = workflow_parameters.get("interleave_order")
        if interleave_order:
            self.interleave_order = interleave_order

        # NB this is an internal dictionary. DO NOT MODIFY
        settings = HWR.beamline.gphl_workflow.settings

        if energies:
            # Energies *reset* existing list, and there must be at least one
            if self.characterisation_done:
                energy_tags = workflow_parameters.get(
                    "beam_energy_tags", (settings["default_beam_energy_tag"],)
                )
            elif self.get_type() == "diffractcal":
                energy_tags = ("Main",)
            else:
                energy_tags = ("Characterisation",)
            if len(energies) not in (len(energy_tags), 1):
                raise ValueError(
                    "Number of energies %s do not match available slots %s"
                    % (energies, energy_tags)
                )
            wavelengths = []
            for iii, energy in enumerate(energies):
                role = energy_tags[iii]
                wavelengths.append(
                    GphlMessages.PhasingWavelength(
                        wavelength=HWR.beamline.energy.calculate_wavelength(energy),
                        role=role,
                    )
                )
            self.wavelengths = tuple(wavelengths)
        if not self.wavelengths:
            raise ValueError("Value for energy missing. Coding error?")

        wavelength = self.wavelengths[0].wavelength

        if self.detector_setting is None:
            resolution = resolution or self.aimed_resolution
        if resolution:
            distance = HWR.beamline.resolution.resolution_to_distance(
                resolution, wavelength
            )
            orgxy = HWR.beamline.detector.get_beam_position(distance, wavelength)

            self.detector_setting = GphlMessages.BcsDetectorSetting(
                resolution, orgxy=orgxy, Distance=distance
            )

        self.strategy_options = {
            "strategy_type": workflow_parameters["strategy_type"],
            "angular_tolerance": settings["angular_tolerance"],
            "clip_kappa": settings["angular_tolerance"],
            "maximum_chi": settings["maximum_chi"],
            "variant": workflow_parameters["variants"][0],
        }
        if strategy_options:
            self.strategy_options.update(strategy_options)

        self.init_spot_dir = init_spot_dir
        self.use_cell_for_processing = use_cell_for_processing


    def set_pre_acquisition_params(
        self,
        exposure_time=None,
        image_width=None,
        wedge_width=None,
        transmission=None,
        image_count=None,
        snapshot_count=None,
        energies = (),
        **unused,
    ):
        """"""
        from mxcubecore.HardwareObjects.Gphl import GphlMessages

        workflow_parameters = self.get_workflow_parameters()
        # NB this is an internal dictionary. DO NOT MODIFY
        settings = HWR.beamline.gphl_workflow.settings

        if exposure_time:
            self.exposure_time = float(exposure_time)
        if image_width:
            self.image_width = float(image_width)
        if wedge_width:
            self.wedge_width = float(wedge_width)
        if transmission:
            self.transmission = float(transmission)
        if snapshot_count:
            self.snapshot_count = int(snapshot_count)
        if image_count:
            self.strategy_length = int(image_count) * self.image_width
        if energies:
            # Energies are *added* to existing list
            energy_tags = workflow_parameters.get(
                "beam_energy_tags", (settings["default_beam_energy_tag"],)
            )
            wavelengths = list(self.wavelengths)
            offset = len(wavelengths)
            if len(energies) == len(energy_tags) - offset:
                for iii, energy in enumerate(energies):
                    role = energy_tags[iii + offset]
                    wavelengths.append(
                        GphlMessages.PhasingWavelength(
                            wavelength=HWR.beamline.energy.calculate_wavelength(
                                energy
                            ),
                            role=role,
                        )
                    )
                self.wavelengths = tuple(wavelengths)
            else:
                raise ValueError(
                    "Number of energies %s do not match remaining slots %s"
                    % (energies, energy_tags[len(self.wavelengths):])
                )
            

    def init_from_task_data(self, sample_model, params):
        """
        sample_model is required as this may be called before the object is enqueued
        params is a dictionary with structure determined by mxcube3 usage
        """

        from mxcubecore.HardwareObjects.Gphl import GphlMessages

        # Set attributes directly from params
        self.set_type(params["strategy_name"])
        self.shape = params.get("shape", "")
        for tag in (
            "decay_limit",
            "maximum_dose_budget",
            "characterisation_budget_fraction",
            "characterisation_strategy"
        ):
            value = params.get(tag)
            if value:
                setattr(self, tag, value)

        settings = HWR.beamline.gphl_workflow.settings
        # NB settings is an internal attribute DO NOT MODIFY

        # Auto acquisition parameters
        acq_param_settings = settings.get("auto_acq_parameters") or [{}]
        self.auto_acq_parameters = ll1 = [copy.deepcopy(acq_param_settings[0])]
        if acq_param_settings[0] is acq_param_settings[-1]:
            ll1.append(copy.deepcopy(acq_param_settings[0]))
        else:
            ll1.append(copy.deepcopy(acq_param_settings[-1]))
        new_acq_params = params.pop("auto_acq_parameters", [{}])
        ll1[0].update (new_acq_params[0])
        ll1[-1].update(new_acq_params[-1])

        if "automation_mode" in params:
            self.automation_mode = params["automation_mode"]

        # Set automation switches and basic acquisition parameters
        if new_acq_params[0].get("init_spot_dir"):
            # Characterisation is pre-acquired
            if not self.automation_mode:
                raise ValueError("init_spot_dir setting only valid in automation mode")
            if (
                "exposure_time" not in new_acq_params[0]
                or "image_width" not in new_acq_params[0]
            ):
                raise ValueError(
                    "Parameters 'exposure_time', and 'image_width' are mandatory"
                    "when 'init_spot_dir' is set"
                )
            self.transmission = HWR.beamline.transmission.get_value()

        else:
            # Normal characterisation, set some parameters from defaults
            default_parameters = HWR.beamline.get_default_acquisition_parameters()
            self.exposure_time = default_parameters.exp_time
            self.image_width = default_parameters.osc_range

        # Path template and prefixes
        base_prefix = self.path_template.base_prefix = (
            params.get("prefix")
            or HWR.beamline.session.get_default_prefix(sample_model)
        )
        self.set_name(base_prefix)
        self.path_template.suffix = (
            params.get("suffix") or HWR.beamline.session.suffix
        )
        self.path_template.num_files = 0

        self.path_template.directory = os.path.join(
            HWR.beamline.session.get_base_image_directory(), params.get("subdir", "")
        )
        self.path_template.process_directory = os.path.join(
            HWR.beamline.session.get_base_process_directory(),
            params.get("subdir", ""),
        )

        # Set crystal parameters from sample node
        crystal = sample_model.crystals[0]
        tpl = (
            crystal.cell_a,
            crystal.cell_b,
            crystal.cell_c,
            crystal.cell_alpha,
            crystal.cell_beta,
            crystal.cell_gamma,
        )
        if all(tpl):
            self.cell_parameters = tpl
        self.protein_acronym = crystal.protein_acronym
        self.space_group = self.input_space_group = crystal.space_group
        self.crystal_classes = params.get("crystal_classes", ())

        # Set to current wavelength for now - nothing else available
        wavelength = HWR.beamline.energy.get_wavelength()
        role = HWR.beamline.gphl_workflow.settings["default_beam_energy_tag"]
        self.wavelengths = (
            GphlMessages.PhasingWavelength(wavelength=wavelength, role=role),
        )

        # Set parameters from diffraction plan
        diffraction_plan = sample_model.diffraction_plan
        if diffraction_plan:
            # It is not clear if diffraction_plan is a dict or an object,
            # and if so which kind
            if hasattr(diffraction_plan, "radiationSensitivity"):
                radiation_sensitivity = diffraction_plan.radiationSensitivity
            else:
                radiation_sensitivity = diffraction_plan.get("radiationSensitivity")

            if radiation_sensitivity:
                self.relative_rad_sensitivity = radiation_sensitivity

            if hasattr(diffraction_plan, "aimedResolution"):
                resolution = diffraction_plan.aimedResolution
            else:
                resolution = diffraction_plan.get("aimedResolution")

            if resolution:
                self.aimed_resolution = resolution

    def get_workflow_parameters(self):
        """Get parameters dictionary for workflow strategy"""
        name = self.get_type()
        result = HWR.beamline.gphl_workflow.workflow_strategies.get(name)
        if result is None:
            raise ValueError("No GPhL workflow strategy named %s found" % name)
        #
        return result

    # Parameters for start of workflow
    def get_path_template(self):
        return self.path_template

    # Strategy type (string); e.g. 'phasing'
    def get_type(self):
        return self._type

    def set_type(self, value):
        self._type = value

    # Run name equal to base_prefix
    def get_name(self):
        return self._name

    def set_name(self, value):
        self._name = value

    # Cell parameters - sequence of six floats (a,b,c,alpha,beta,gamma)
    @property
    def cell_parameters(self):
        return self._cell_parameters

    @cell_parameters.setter
    def cell_parameters(self, value):
        self._cell_parameters = None
        if value:
            if len(value) == 6:
                self._cell_parameters = tuple(float(x) for x in value)
            else:
                raise ValueError("invalid value for cell_parameters: %s" % str(value))


    def calculate_transmission(self, use_dose=None):
        """Calculate transmission correspoiding to using up a given dose
        NBNB value may be higher than 100%; this must be dealt with by the caller

        :param use_dose (float): Dose to consume, in MGy
        :return (float): transmission in %
        """
        if not use_dose:
            use_dose = self.recommended_dose_budget()
        max_dose = self.calculate_dose(transmission=100.0)
        if max_dose:
            return 100. * use_dose / max_dose
        else:
            raise ValueError("Could not calculate transmission")


    def calculate_dose(self, transmission=None):
        """Calculate dose consumed with current parameters

        :param transmission (float): Transmission in %. Defaults to current setting
        :return:
        """

        result = None
        if transmission is None:
            transmission = self.transmission
        energy = HWR.beamline.energy.calculate_energy(self.wavelengths[0].wavelength)
        flux_density = HWR.beamline.flux.get_average_flux_density(
            transmission=transmission
        )
        strategy_length = self.strategy_length
        exposure_time = self.exposure_time
        image_width = self.image_width
        if flux_density:
            if strategy_length and exposure_time and image_width:
                duration = exposure_time * strategy_length / image_width
                return HWR.beamline.gphl_workflow.calculate_dose(
                    duration, energy, flux_density
                )
        msg = (
            "WARNING: Dose could not be calculated from:\n"
            " energy:%s keV, strategy_length:%s deg, exposure_time:%s s, "
            "image_width:%s deg, transmission: %s  flux_density:%s  photons/mm^2"
        )
        print(
            msg % (
                energy,
                strategy_length,
                exposure_time,
                image_width,
                transmission,
                flux_density
            )
        )
        return 0

    def recommended_dose_budget(self, resolution=None):
        """Get resolution-dependent dose budget using current configuration

        :param resolution (float): Target resolution (in A), defauls to current setting
        :return:
        """
        resolution = resolution or self.detector_setting.resolution
        if not resolution:
            raise ValueError("No resolution set to calculate dose budget")
        return HWR.beamline.gphl_workflow.resolution2dose_budget(
            resolution,
            decay_limit=self.decay_limit,
            maximum_dose_budget=self.maximum_dose_budget,
            relative_rad_sensitivity=self.relative_rad_sensitivity
        )


class XrayImaging(TaskNode):
    def __init__(self, xray_imaging_params, acquisition=None, crystal=None, name=""):
        TaskNode.__init__(self)

        self.xray_imaging_parameters = xray_imaging_params
        if not acquisition:
            acquisition = Acquisition()

        if not crystal:
            crystal = Crystal()

        self.acquisitions = [acquisition]
        self.processing_parameters = ProcessingParameters()
        self.crystal = crystal
        self.set_name(name)
        self.experiment_type = (
            queue_model_enumerables.EXPERIMENT_TYPE.NATIVE
        )  # TODO use IMAGING
        self.set_requires_centring(True)
        self.run_offline_processing = False
        self.run_online_processing = False
        self.lims_group_id = None

    def get_name(self):
        return "%s_%i" % (
            self.acquisitions[0].path_template.get_prefix(),
            self.acquisitions[0].path_template.run_number,
        )

    def get_path_template(self):
        return self.acquisitions[0].path_template

    def get_files_to_be_written(self):
        return self.acquisitions[0].path_template.get_files_to_be_written()


def addXrayCentring(parent_node, **centring_parameters):
    """Add Xray centring to queue."""
    xc_model = XrayCentring2(**centring_parameters)
    HWR.beamline.queue_model.add_child(parent_node, xc_model)
    #
    return xc_model


#
# Collect hardware object utility function.
#
def to_collect_dict(data_collection, session, sample, centred_pos=None):
    """ return [{'comment': '',
          'helical': 0,
          'motors': {},
          'take_video': False,
          'take_snapshots': False,
          'fileinfo': {'directory': '/data/id14eh4/inhouse/opid144/' +\
                                    '20120808/RAW_DATA',
                       'prefix': 'opid144', 'run_number': 1,
                       'process_directory': '/data/id14eh4/inhouse/' +\
                                            'opid144/20120808/PROCESSED_DATA'},
          'in_queue': 0,
          'detector_binning_mode': 2,
          'shutterless': 0,
          'sessionId': 32368,
          'do_inducedraddam': False,
          'sample_reference': {},
          'processing': 'False',
          'residues': '',
          'dark': True,
          'scan4d': 0,
          'input_files': 1,
          'oscillation_sequence': [{'exposure_time': 1.0,
                                    'kappaStart': 0.0,
                                    'phiStart': 0.0,
                                    'start_image_number': 1,
                                    'number_of_images': 1,
                                    'overlap': 0.0,
                                    'start': 0.0,
                                    'range': 1.0,
                                    'number_of_passes': 1}],
          'nb_sum_images': 0,
          'EDNA_files_dir': '',
          'anomalous': 'False',
          'file_exists': 0,
          'experiment_type': 'SAD',
          'skip_images': 0}]"""

    acquisition = data_collection.acquisitions[0]
    acq_params = acquisition.acquisition_parameters
    proc_params = data_collection.processing_parameters

    result = [
        {
            "comments": acq_params.comments,
            "take_video": acq_params.take_video,
            "take_snapshots": acq_params.take_snapshots,
            "fileinfo": {
                "directory": acquisition.path_template.directory,
                "prefix": acquisition.path_template.get_prefix(),
                "run_number": acquisition.path_template.run_number,
                "archive_directory": acquisition.path_template.get_archive_directory(),
                # "process_directory": session.get_process_directory(),
                "process_directory": acquisition.path_template.process_directory,
                "template": acquisition.path_template.get_image_file_name(),
                "compression": acquisition.path_template.compression,
            },
            "in_queue": acq_params.in_queue,
            "in_interleave": acq_params.in_interleave,
            "detector_binning_mode": acq_params.detector_binning_mode,
            "detector_roi_mode": acq_params.detector_roi_mode,
            "shutterless": acq_params.shutterless,
            "sessionId": session.session_id,
            "do_inducedraddam": acq_params.induce_burn,
            "sample_reference": {
                "spacegroup": proc_params.space_group,
                "cell": proc_params.get_cell_str(),
                "blSampleId": sample.lims_id,
            },
            "processing": str(proc_params.process_data and True),
            "processing_offline": data_collection.run_offline_processing,
            "processing_online": data_collection.run_online_processing,
            "residues": proc_params.num_residues,
            "dark": acq_params.take_dark_current,
            "detector_distance": acq_params.detector_distance,
            "resolution": {"upper": acq_params.resolution or 0.0},
            "transmission": acq_params.transmission,
            "energy": acq_params.energy,
            "oscillation_sequence": [
                {
                    "exposure_time": acq_params.exp_time,
                    "kappaStart": acq_params.kappa,
                    "phiStart": acq_params.kappa_phi,
                    "start_image_number": acq_params.first_image,
                    "number_of_images": acq_params.num_images,
                    "overlap": acq_params.overlap,
                    "start": acq_params.osc_start,
                    "range": acq_params.osc_range,
                    "number_of_passes": acq_params.num_passes,
                    "number_of_lines": acq_params.num_lines,
                    "mesh_range": acq_params.mesh_range,
                    "num_triggers": acq_params.num_triggers,
                    "num_images_per_trigger": acq_params.num_images_per_trigger,
                }
            ],
            "group_id": data_collection.lims_group_id,
            "EDNA_files_dir": acquisition.path_template.process_directory,
            "xds_dir": acquisition.path_template.xds_dir,
            "anomalous": proc_params.anomalous,
            "experiment_type": queue_model_enumerables.EXPERIMENT_TYPE_STR[
                data_collection.experiment_type
            ],
            "skip_images": acq_params.skip_existing_images,
            "motors": centred_pos.as_dict() if centred_pos is not None else {},
        }
    ]

    # NBNB HACK. These start life as default values, and you do NOT want to keep
    # resetting the beamline to the current value,
    # as this causes unnecessary hardware activities
    # So remove them altogether if the value is (was excplicitly set to)  None or 0
    dd = result[0]
    for tag in ("detector_distance", "energy", "transmission"):
        if tag in dd and not dd[tag]:
            del dd[tag]
    resolution = dd.get("resolution")
    if resolution is not None and not resolution.get("upper"):
        del dd["resolution"]
    return result


def create_subwedges(total_num_images, sw_size, osc_range, osc_start):
    """
    Creates n subwedges where n = total_num_images / subwedge_size.

    :param total_num_images: The total number of images
    :type total_num_images: int

    :param osc_range: Oscillation range for each image
    :type osc_range: double

    :param osc_start: The start angle/offset of the oscillation
    :type osc_start: double

    :returns: List of tuples with the format:
              (start image number, number of images, oscilation start)
    """
    number_of_subwedges = total_num_images / sw_size
    subwedges = []

    for sw_num in range(0, number_of_subwedges):
        _osc_start = osc_start + (osc_range * sw_size * sw_num)
        subwedges.append((sw_num * sw_size + 1, sw_size, _osc_start))

    return subwedges


def create_inverse_beam_sw(num_images, sw_size, osc_range, osc_start, run_number):
    """
    Creates subwedges for inverse beam, and interleves the result.
    Wedges W1 and W2 are created 180 degres apart, the result is
    interleaved and given on the form:
    (W1_1, W2_1), ... (W1_n-1, W2_n-1), (W1_n, W2_n)

    :param num_images: The total number of images
    :type num_images: int

    :param sw_size: Number of images in each subwedge
    :type sw_size: int

    :param osc_range: Oscillation range for each image
    :type osc_range: double

    :param osc_start: The start angle/offset of the oscillation
    :type osc_start: double

    :param run_number: Run number for the first wedge (W1), the run number
                       of the second wedge will be run_number + 1.

    :returns: A list of tuples containing the swb wedges.
              The tuples are on the form:
              (start_image, num_images, osc_start, run_number)

    :rtype: List [(...), (...)]
    """
    w1 = create_subwedges(num_images, sw_size, osc_range, osc_start)
    w2 = create_subwedges(num_images, sw_size, osc_range, 180 + osc_start)
    w1 = [pair + (run_number,) for pair in w1]
    w2 = [pair + (run_number + 1,) for pair in w2]

    # Interlave subwedges
    subwedges = [sw_pair for pair in zip(w1, w2) for sw_pair in pair]

    return subwedges


def create_interleave_sw(interleave_list, num_images, sw_size):
    """
    Creates subwedges for interleved collection.
    Wedges W1, W2, Wm (where m is num_collections) are created:
    (W1_1, W2_1, ..., W1_m), ... (W1_n-1, W2_n-1, ..., Wm_n-1),
    (W1_n, W2_n, ..., Wm_n)

    :param interleave_list: list of interleaved items
    :type interleave_list: list of dict

    :param num_images: number of images of first collection. Based on the
    first collection certain number of subwedges will be created. If
    first collection contains more images than others then in the end
    the rest of images from first collections are created as last subwedge
    :type num_images: int

    :param sw_size: Number of images in each subwedge
    :type sw_size: int

    :returns: A list of tuples containing the swb wedges.
              The tuples are in the form:
              (collection_index, subwedge_index, subwedge_firt_image,
               subwedge_start_osc)
    :rtype: List [(...), (...)]
    """
    subwedges = []
    sw_first_image = None
    for sw_index in range(int(num_images / sw_size)):
        for collection_index in range(len(interleave_list)):
            collection_osc_start = (
                interleave_list[collection_index]["data_model"]
                .acquisitions[0]
                .acquisition_parameters.osc_start
            )
            collection_osc_range = (
                interleave_list[collection_index]["data_model"]
                .acquisitions[0]
                .acquisition_parameters.osc_range
            )
            collection_first_image = (
                interleave_list[collection_index]["data_model"]
                .acquisitions[0]
                .acquisition_parameters.first_image
            )
            collection_num_images = (
                interleave_list[collection_index]["data_model"]
                .acquisitions[0]
                .acquisition_parameters.num_images
            )
            if sw_index * sw_size <= collection_num_images:
                sw_actual_size = sw_size
                if sw_size > collection_num_images - (sw_index + 1) * sw_size > 0:
                    sw_actual_size = collection_num_images % sw_size
                sw_first_image = collection_first_image + sw_index * sw_size
                sw_osc_start = (
                    collection_osc_start + collection_osc_range * sw_index * sw_size
                )
                sw_osc_range = collection_osc_range * sw_actual_size
                subwedges.append(
                    {
                        "collect_index": collection_index,
                        "collect_first_image": collection_first_image,
                        "collect_num_images": collection_num_images,
                        "sw_index": sw_index,
                        "sw_first_image": sw_first_image,
                        "sw_actual_size": sw_actual_size,
                        "sw_osc_start": sw_osc_start,
                        "sw_osc_range": sw_osc_range,
                    }
                )
        sw_first_image += sw_actual_size
    return subwedges


def try_parse_int(n):
    try:
        return int(n)
    except ValueError:
        return -1
