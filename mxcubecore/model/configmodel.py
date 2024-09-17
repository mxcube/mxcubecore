from pydantic.v1 import BaseModel, Field


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
