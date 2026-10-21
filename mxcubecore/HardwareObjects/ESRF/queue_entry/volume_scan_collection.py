import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ESRF.queue_entry.mx_base_queue_entry import (
    BaseUserCollectionParameters,
    MXBaseQueueEntry,
    MXPathParameters,
)
from mxcubecore.HardwareObjects.SampleView import Grid
from mxcubecore.model.common import (
    CommonCollectionParamters,
    LegacyParameters,
    StandardCollectionParameters,
)
from mxcubecore.model.queue_model_enumerables import EXPERIMENT_TYPE
from mxcubecore.model.queue_model_objects import CentredPosition, DataCollection
from mxcubecore.queue_entry.base_queue_entry import TaskPrerequisite

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


@dataclass
class MeshParameters:
    """Position/dimensions of a single mesh scan within a volume scan."""

    grid_centre: CentredPosition
    mesh_range: dict
    nb_lines: int
    nb_frames_total: int


def process_mesh(previous_mesh: MeshParameters, mesh_index: int) -> MeshParameters:
    """Compute the position/dimensions of the next mesh scan, centeter of diffraction
    plus safe margin.

    Placeholder for the real processing program: it will analyse the data
    from the current mesh and propose where the next mesh should be centred and how 
    large it should be.
    """
    return previous_mesh


def mesh_from_grid(grid: Grid) -> MeshParameters:
    """Build the MeshParameters for the (user-drawn) grid shape <grid>."""
    grid_dict = grid.as_dict()
    return MeshParameters(
        grid_centre=grid.get_centred_position(),
        mesh_range={
            "horizontal_range": grid_dict["dx_mm"],
            "vertical_range": grid_dict["dy_mm"],
        },
        nb_lines=grid.get_num_lines(),
        nb_frames_total=grid.num_cols * grid.num_rows,
    )


class VolumeScanUserCollectionParameters(BaseUserCollectionParameters):
    omega_angles: list[float] = Field(
        default_factory=list,
        description=(
            "Omega angle (deg) for each mesh scan in the volume, one mesh "
            "is collected per angle, in the given order"
        ),
    )
    class Config:
        extra = "ignore"


class VolumeScanTaskParameters(BaseModel):
    path_parameters: MXPathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: VolumeScanUserCollectionParameters
    legacy_parameters: LegacyParameters

    @staticmethod
    def update_dependent_fields(field_data):
        return {}


class VolumeScanQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class VolumeScanQueueEntry(MXBaseQueueEntry):
    """
    Performs a series of mesh scans ("volume scan"), rotating omega before
    each one. The first mesh is the user-drawn grid shape; the position and
    dimensions of each subsequent mesh are computed by process_mesh(), to be
    defined, but currently returns the previous mesh unchanged.
    """

    QMO = VolumeScanQueueModel
    DATA_MODEL = VolumeScanTaskParameters
    NAME = "Volume Scan"
    REQUIRES = [TaskPrerequisite.GRID]

    def __init__(self, view, data_model: VolumeScanQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()

        params = self._data_model._task_data.user_collection_parameters
        omega_angles = params.omega_angles

        if not omega_angles:
            raise ValueError("VolumeScanQueueEntry requires at least one omega angle")

        shape_id = self.get_data_model().shape
        grid = HWR.beamline.sample_view.get_shape(shape_id)

        if not isinstance(grid, Grid):
            raise ValueError(
                f"VolumeScanQueueEntry requires a grid shape, got {grid}"
            )

        # The initial mesh is in this case drawn by the user, but could come from
        # optical loop centring, as discussed. In that case perhaps supplied as a
        # point cloud. That next step would then be to select a intersecting plane
        # of that point cloud. I.e the one where the crystal occupies most space.
        # mesh = get_mesh_from_point_cloud(point_cloud).
        mesh = mesh_from_grid(grid)

        diffr = HWR.beamline.diffractometer
        log = logging.getLogger("user_level_log")
        num_meshes = len(omega_angles)

        for mesh_index, omega in enumerate(omega_angles):
            if mesh_index > 0:
                mesh = process_mesh(mesh, mesh_index)

            log.info(
                "Volume scan: rotating omega to %s deg (mesh %d/%d)",
                omega,
                mesh_index + 1,
                num_meshes,
            )
            diffr.omega.set_value(omega, timeout=None)

            log.info("Volume scan: starting mesh %d/%d", mesh_index + 1, num_meshes)
            diffr.do_mesh_scan(
                omega,
                omega,
                params.exp_time,
                HWR.beamline.detector.dead_time,
                mesh.nb_lines,
                mesh.nb_frames_total,
                mesh.grid_centre,
                mesh.mesh_range,
            )

            self.emit_progress((mesh_index + 1) / num_meshes)

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        HWR.beamline.diffractometer.abort()
        super().stop()
