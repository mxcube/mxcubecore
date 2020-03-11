# -*- coding: utf-8 -*-
import jsonschema

from .common import ValidationError


class BaseModel(dict):
    _SCHEMA = ""

    def __init__(self, *args, **kwargs):
        super(BaseModel, self).__init__(*args, **kwargs)

        if self._SCHEMA:
            try:
                jsonschema.validate(instance=self, schema=self._SCHEMA)
            except jsonschema.exceptions.ValidationError as ex:
                raise ValidationError(ex)

    __getattr__ = dict.__getitem__

    @property
    def schema_json(self):
        return self._SCHEMA


class MockDataModel(BaseModel):
    """
    Example DataModel used by the MockProcedure (for testing)
    """

    # Not defining any attributes as it is a dictionary
    # but it needs to exist so that the type exists
