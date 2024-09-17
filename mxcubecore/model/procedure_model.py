# -*- coding: utf-8 -*-

from pydantic.v1 import BaseModel, Field


class ValidationError(Exception):
    pass


class BaseModel(BaseModel):
    def __init__(self, *args, **kwargs):
        try:
            super(BaseModel, self).__init__(*args, **kwargs)
        except Exception as ex:
            raise ValidationError(ex)


class MockDataModel(BaseModel):
    """
    Example DataModel used by the MockProcedure (for testing)
    """

    transmission: float = Field(0)
    energy: float = Field(0)
    resolution: float = Field(0)
    exposure_time: float = Field(0)
    number_of_images: float = Field(0)
