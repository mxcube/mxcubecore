from pydantic import BaseModel, Field


class CommonCollectionParamters(BaseModel):
    skip_existing_images: bool
    take_snapshots: int
    type: str
    label: str


class PathParameters(BaseModel):
    prefix: str
    subdir: str
    experiment_name: str

    class Config:
        extra: "ignore"


class LegacyParameters(BaseModel):
    take_dark_current: int
    inverse_beam: bool
    num_passes: int
    overlap: float

    class Config:
        extra: "ignore"


class StandardCollectionParameters(BaseModel):
    num_images: int
    osc_start: float
    osc_range: float
    energy: float
    transmission: float
    resolution: float
    first_image: int
    kappa: float
    kappa_phi: float
    beam_size: float
    shutterless: bool
    selection: list = Field([])

    class Config:
        extra: "ignore"


class BeamlineParameters(BaseModel):
    energy: float
    transmission: float
    resolution: float
    wavelength: float
    detector_distance: float
    beam_x: float
    beam_y: float
