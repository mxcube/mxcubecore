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

import logging

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model import queue_model_objects
from mxcubecore.queue_entry.base_queue_entry import (
    QUEUE_ENTRY_STATUS,
    BaseQueueEntry,
)
from mxcubecore.queue_entry.data_collection import DataCollectionQueueEntry

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class CharacterisationGroupQueueEntry(BaseQueueEntry):
    """
    Used to group (couple) a CollectionQueueEntry and a
    CharacterisationQueueEntry, creating a virtual entry for characterisation.
    """

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
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
        dc_qe = DataCollectionQueueEntry(
            self.get_view(), reference_image_collection, view_set_queue_entry=False
        )
        dc_qe.set_enabled(True)
        dc_qe.in_queue = self.in_queue
        self.enqueue(dc_qe)
        self.dc_qe = dc_qe
        if char.run_characterisation:
            try:
                char_qe = CharacterisationQueueEntry(
                    self.get_view(), char, view_set_queue_entry=False
                )
            except Exception as ex:
                logging.getLogger("HWR").exception(
                    "Could not create CharacterisationQueueEntry"
                )
                self.char_qe = None
            else:
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

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)
        self.edna_result = None
        self.auto_add_diff_plan = True

    def __getstate__(self):
        d = BaseQueueEntry.__getstate__(self)

        d["data_analysis_hwobj"] = (
            HWR.beamline.characterisation.name
            if HWR.beamline.characterisation
            else None
        )
        d["diffractometer_hwobj"] = (
            HWR.beamline.diffractometer.name if HWR.beamline.diffractometer else None
        )
        d["queue_model_hwobj"] = (
            HWR.beamline.queue_model.name if HWR.beamline.queue_model else None
        )
        d["session_hwobj"] = HWR.beamline.session.name if HWR.beamline.session else None

        return d

    def __setstate__(self, d):
        BaseQueueEntry.__setstate__(self, d)

    def execute(self):
        BaseQueueEntry.execute(self)

        if HWR.beamline.characterisation is not None:
            if self.get_data_model().wait_result:
                logging.getLogger("user_level_log").warning(
                    "Characterisation: Please wait ..."
                )
                self.start_char()
            else:
                logging.getLogger("user_level_log").warning(
                    "Characterisation: Please wait ..."
                )
                gevent.spawn(self.start_char)

    def start_char(self):
        char = self.get_data_model()
        characterisation_parameters = char.characterisation_parameters

        if characterisation_parameters.strategy_program != "None":
            log = logging.getLogger("user_level_log")
            self.get_view().setText(1, "Characterising")
            log.info("Characterising, please wait ...")
            reference_image_collection = char.reference_image_collection

            if HWR.beamline.characterisation is not None:
                edna_input = HWR.beamline.characterisation.input_from_params(
                    reference_image_collection, characterisation_parameters
                )

                self.edna_result = HWR.beamline.characterisation.characterise(
                    edna_input
                )

                if self.edna_result:
                    log.info("Characterisation completed.")

                    char.html_report = HWR.beamline.characterisation.get_html_report(
                        self.edna_result
                    )

                    try:
                        strategy_result = self.edna_result.getCharacterisationResult().getStrategyResult()
                    except Exception:
                        strategy_result = None

                    if strategy_result:
                        collection_plan = strategy_result.getCollectionPlan()
                    else:
                        collection_plan = None

                    if collection_plan:
                        if char.auto_add_diff_plan:
                            # default action
                            self.handle_diffraction_plan(self.edna_result, None)
                        else:
                            collections = HWR.beamline.characterisation.dc_from_output(
                                self.edna_result, char.reference_image_collection
                            )
                            char.diffraction_plan.append(collections)
                            HWR.beamline.queue_model.emit(
                                "diff_plan_available", (char, collections)
                            )

                        self.get_view().setText(1, "Done")
                    else:
                        self.get_view().setText(1, "No result")
                        self.status = QUEUE_ENTRY_STATUS.WARNING
                        log.warning(
                            "Characterisation completed "
                            + "successfully but without collection plan."
                        )
                else:
                    self.get_view().setText(1, "Charact. Failed")
                    log.error("EDNA-Characterisation completed with a failure.")

        char.set_executed(True)
        self.get_view().setHighlighted(True)

    def handle_diffraction_plan(self, edna_result, edna_collections):
        char = self.get_data_model()
        reference_image_collection = char.reference_image_collection

        dcg_model = char.get_parent()
        sample_data_model = dcg_model.get_parent()

        new_dcg_name = "Diffraction plan"
        new_dcg_num = dcg_model.get_parent().get_next_number_for_name(new_dcg_name)

        new_dcg_model = queue_model_objects.TaskGroup()
        new_dcg_model.set_enabled(False)
        new_dcg_model.set_name(new_dcg_name)
        new_dcg_model.set_number(new_dcg_num)
        new_dcg_model.set_origin(char._node_id)

        HWR.beamline.queue_model.add_child(sample_data_model, new_dcg_model)
        if edna_collections is None:
            edna_collections = HWR.beamline.characterisation.dc_from_output(
                edna_result, reference_image_collection
            )
        for edna_dc in edna_collections:
            path_template = edna_dc.acquisitions[0].path_template
            run_number = HWR.beamline.queue_model.get_next_run_number(path_template)
            path_template.run_number = run_number
            path_template.compression = char.diff_plan_compression

            edna_dc.set_enabled(char.run_diffraction_plan)
            edna_dc.set_name(path_template.get_prefix())
            edna_dc.set_number(path_template.run_number)
            HWR.beamline.queue_model.add_child(new_dcg_model, edna_dc)

        return edna_collections

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self.get_view().setOn(True)
        self.get_view().setHighlighted(False)

    def post_execute(self):
        BaseQueueEntry.post_execute(self)

    def get_type_str(self):
        return "Characterisation"

    def stop(self):
        BaseQueueEntry.stop(self)
        HWR.beamline.characterisation.stop()
