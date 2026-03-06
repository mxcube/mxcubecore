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

import contextlib
import copy
import logging
from typing import List

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects import edna_test_data
from mxcubecore.HardwareObjects.EDNACharacterisation import EDNACharacterisation
from mxcubecore.HardwareObjects.XSDataMXCuBEv1_4 import (
    XSDataInputMXCuBE,
    XSDataResultMXCuBE,
)
from mxcubecore.model import queue_model_objects as qmo

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3"


class EDNACharacterisationMockup(EDNACharacterisation):
    def __init__(self, name) -> None:
        super(EDNACharacterisationMockup, self).__init__(name)

    def input_from_params(self, data_collection, char_params) -> XSDataInputMXCuBE:
        return XSDataInputMXCuBE.parseString(self.edna_default_input)

    def characterise(self, edna_input) -> XSDataResultMXCuBE:
        return XSDataResultMXCuBE.parseString(edna_test_data.EDNA_RESULT_DATA)

    def is_running(self) -> bool:
        return False

    def get_default_characterisation_parameters(self) -> qmo.CharacterisationParameters:
        return super(
            EDNACharacterisationMockup, self
        ).get_default_characterisation_parameters()

    def dc_from_output(  # noqa: C901, PLR0915
        self, edna_result, reference_image_collection
    ) -> List[qmo.DataCollection]:
        data_collections = []

        crystal = copy.deepcopy(reference_image_collection.crystal)
        ref_proc_params = reference_image_collection.processing_parameters
        processing_parameters = copy.deepcopy(ref_proc_params)

        try:
            char_results = edna_result.getCharacterisationResult()
            edna_strategy = char_results.getStrategyResult()
            collection_plan = edna_strategy.getCollectionPlan()[0]
            wedges = collection_plan.getCollectionStrategy().getSubWedge()
        except Exception:
            logging.getLogger("HWR").exception("")
        else:
            try:
                resolution = (
                    collection_plan.getStrategySummary().getResolution().getValue()
                )
                resolution = round(resolution, 3)
            except AttributeError:
                resolution = None

            try:
                transmission = (
                    collection_plan.getStrategySummary().getAttenuation().getValue()
                )
                transmission = round(transmission, 2)
            except AttributeError:
                transmission = None

            try:
                screening_id = edna_result.getScreeningId().getValue()
            except AttributeError:
                screening_id = None

            for i in range(len(wedges)):
                wedge = wedges[i]
                exp_condition = wedge.getExperimentalCondition()
                goniostat = exp_condition.getGoniostat()
                beam = exp_condition.getBeam()

                acq = qmo.Acquisition()
                acq.acquisition_parameters = (
                    HWR.beamline.get_default_acquisition_parameters()
                )
                acquisition_parameters = acq.acquisition_parameters

                acquisition_parameters.centred_position = (
                    reference_image_collection.acquisitions[
                        0
                    ].acquisition_parameters.centred_position
                )

                acq.path_template = HWR.beamline.get_default_path_template()

                # Use the same path template as the reference_collection
                # and update the members the needs to be changed. Keeping
                # the directories of the reference collection.
                ref_pt = reference_image_collection.acquisitions[0].path_template

                acq.path_template = copy.deepcopy(ref_pt)
                acq.path_template.directory = "/".join(
                    ref_pt.directory.split("/")[0:-2]
                )
                acq.path_template.wedge_prefix = "w" + str(i + 1)
                acq.path_template.reference_image_prefix = str()

                if resolution:
                    acquisition_parameters.resolution = resolution

                if transmission:
                    acquisition_parameters.transmission = transmission

                if screening_id:
                    acquisition_parameters.screening_id = screening_id

                with contextlib.suppress(AttributeError):
                    acquisition_parameters.osc_start = (
                        goniostat.getRotationAxisStart().getValue()
                    )

                with contextlib.suppress(AttributeError):
                    acquisition_parameters.osc_end = (
                        goniostat.getRotationAxisEnd().getValue()
                    )

                with contextlib.suppress(AttributeError):
                    acquisition_parameters.osc_range = (
                        goniostat.getOscillationWidth().getValue()
                    )

                try:
                    num_images = int(
                        abs(
                            acquisition_parameters.osc_end
                            - acquisition_parameters.osc_start
                        )
                        / acquisition_parameters.osc_range
                    )

                    acquisition_parameters.first_image = 1
                    acquisition_parameters.num_images = num_images
                    acq.path_template.num_files = num_images
                    acq.path_template.start_num = 1

                except AttributeError:
                    logging.getLogger("HWR").exception("")

                with contextlib.suppress(AttributeError):
                    acquisition_parameters.transmission = (
                        beam.getTransmission().getValue()
                    )

                with contextlib.suppress(AttributeError):
                    acquisition_parameters.energy = round(
                        (123984.0 / beam.getWavelength().getValue()) / 10000.0, 4
                    )

                with contextlib.suppress(AttributeError):
                    acquisition_parameters.exp_time = beam.getExposureTime().getValue()

                dc = qmo.DataCollection([acq], crystal, processing_parameters)
                data_collections.append(dc)

        return data_collections
