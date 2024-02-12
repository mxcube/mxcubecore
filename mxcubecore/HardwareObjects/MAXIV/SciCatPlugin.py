"""
A plugin to connect to SciCat.
"""
import os
import math
from datetime import datetime
import logging

from scifish import SciFish


SKIP_VALUES = [
    "fileinfo",
    "auto_dir",
    "EDNA_files_dir",
    "xds_dir",
    "actualCenteringPosition",
]


class SciCatPlugin:
    """
    SciCat Plugin.
    """

    def __init__(self):
        self.scifish = SciFish()
        self.files = []
        self.log = logging.getLogger(__name__)

    def start_scan(self, proposalId, parameters):
        directory = parameters["fileinfo"]["directory"]
        filename = parameters["fileinfo"]["template"]
        num_files = int(
            math.ceil(parameters["oscillation_sequence"][0]["number_of_images"] / 100.0)
        )
        sampleId = parameters["blSampleId"]

        self.scifish.start_scan(datasetName=filename)
        self.scifish.scicat_data.proposalId = proposalId
        self.scifish.scicat_data.sourceFolder = directory
        self.files = []
        self.files.append(os.path.join(directory, filename))
        for i in range(1, num_files + 1):
            formatted_filename = filename.replace("master", f"data_{i:06d}")
            self.files.append(os.path.join(directory, formatted_filename))
        self.scifish.sampleId = sampleId

    def end_scan(self, parameters):
        for item in parameters:
            try:
                if item in SKIP_VALUES:
                    continue
                elif type(parameters[item]) is dict or type(parameters[item]) is list:
                    self.scifish.scicat_data.scientificMetadata.update({item: {}})
                    for subitem in parameters[item]:
                        if type(subitem) is dict:
                            for subsubitem in subitem:
                                smd = self._scientific_metadata_writer(
                                    subsubitem, subitem[subsubitem]
                                )
                                self.scifish.scicat_data.scientificMetadata[
                                    item
                                ].update(smd)
                        else:
                            smd = self._scientific_metadata_writer(
                                subitem, parameters[item][subitem]
                            )
                            self.scifish.scicat_data.scientificMetadata[item].update(
                                smd
                            )
                else:
                    smd = self._scientific_metadata_writer(item, parameters[item])
                    self.scifish.scicat_data.scientificMetadata.update(smd)
            except Exception as e:
                self.log.exception(
                    f"[HWR] Error creating scientificMetadata for {item}: {e}"
                )

        files_list = list(set(self.files))
        for file in files_list:
            try:
                file_size = os.path.getsize(file)
                file_time = datetime.utcfromtimestamp(
                    os.path.getmtime(file)
                ).isoformat()
                self.scifish.scicat_data.files.append(
                    {"path": file, "time": file_time, "size": file_size}
                )
            except OSError:
                self.log.warning(f"Could not add file '{file}'")

        self.scifish.end_scan()

    def _scientific_metadata_writer(self, label, value):
        units = {
            "energy": "keV",
            "sampx": "mm",
            "sampy": "mm",
            "focus": "mm",
            "phi": "deg",
            "kappa": "deg",
            "kappa_phi": "deg",
            "phiz": "deg",
            "phiy": "deg",
            "wavelength": "angstrom",
            "slitGapHorizontal": "mm",
            "detectorDistance": "mm",
            "undulatorGap1": "mm",
            "beamSizeAtSampleX": "mm",
            "beamSizeAtSampleY": "mm",
            "resolution": "angstrom",
            "photon flux": "s^-1",
        }

        if label == "flux":
            label = "photon flux"

        if label in units:
            smd = {label: {"value": value, "unit": units[label]}}
        else:
            smd = {label: value}

        return smd
