"""Pydantic models for N-state hardware option lists."""

from typing import Literal

from pydantic import BaseModel

Severity = Literal["info", "warning", "danger"]


class NStateOption(BaseModel):
    """A single selectable value from an N-state device.

    Stores a value along some optional information for the user
    to make a better informed choice.
    """

    value: str
    label: str | None = None
    description: str | None = None
    severity: Severity | None = None
