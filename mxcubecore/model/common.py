from datetime import datetime
from typing import Optional

from pydantic.v1 import (
    BaseModel,
    Field,
)


class CommonCollectionParamters(BaseModel):
    skip_existing_images: bool
    take_snapshots: int
    type: str
    label: str


class PathParameters(BaseModel):
    prefix: str
    subdir: str
    experiment_name: Optional[str]

    class Config:
        extra = "ignore"


class LegacyParameters(BaseModel):
    take_dark_current: int
    inverse_beam: bool
    num_passes: int
    overlap: float

    class Config:
        extra = "ignore"


class StandardCollectionParameters(BaseModel):
    num_images: int
    osc_start: Optional[float]
    osc_range: Optional[float]
    energy: float
    transmission: float
    resolution: float
    first_image: int
    kappa: Optional[float]
    kappa_phi: Optional[float]
    beam_size: float
    shutterless: bool
    selection: list = Field([])
    shape: str = ""

    class Config:
        extra = "ignore"


class BeamlineParameters(BaseModel):
    energy: float
    transmission: float
    resolution: float
    wavelength: float
    detector_distance: float
    beam_x: float
    beam_y: float
    beam_size_x: float
    beam_size_y: float
    beam_shape: str
    energy_bandwidth: float


class ISPYBCollectionParameters(BaseModel):
    flux_start: float
    flux_end: float
    start_time: datetime
    end_time: datetime
    chip_model: str
    mono_stripe: str
    number_of_rows: int
    number_of_columns: int
