from typing import Optional
from pydantic import BaseModel, Field, Extra


class ExporterNStateConfigModel(BaseModel):
    _class: str = Field("", alias="@class")
    defualt_value: bool = Field(False)
    exporter_address: str
    use_hwstate: bool = Field(True)
    username: str
    value_channel_name: str
    values: str


class Motor(BaseModel):
    _class: str = Field("", alias="@class")
    exporter_address: str
    username: str
    motor_name: str


class BeamInterpolationConfiguration(BaseModel):
    ax: float
    ay: float
    bx: float
    by: float


class AbstractDetectorConfiguration(BaseModel):  # , extra=Extra.forbid):
    file_suffix: str = Field("h5", descriptiom="File name extension/suffix")
    beam: Optional[BeamInterpolationConfiguration]
    has_shutterless: bool = Field(True)
    height: int
    width: int
    humidity_threshold: float
    manufacturer: str
    model: str
    px: float
    py: float
    roi_modes: Optional[list]
    temp_threshold: float
    tolerance: float
