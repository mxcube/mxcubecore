from abc import abstractmethod
from typing import Annotated, Literal, Union

from pydantic.v1 import BaseModel, Field

from mxcubecore.BaseHardwareObjects import HardwareObject


class DoseEstimationOk(BaseModel):
    status: Literal["ok"] = "ok"
    dose_mgy: float
    max_images: int | None


class DoseEstimationError(BaseModel):
    status: Literal["error"] = "error"
    msg: str


class DoseEstimation(BaseModel):
    __root__: Annotated[
        Union[DoseEstimationOk, DoseEstimationError],
        Field(discriminator="status"),
    ]


class StaticGoal(BaseModel):
    type: Literal["static"]
    label: str
    mgy: float


class ResolutionDependentGoal(BaseModel):
    type: Literal["resolution_dependent"]
    label: str
    mgy_per_angstrom: float


ExperimentalGoal = StaticGoal | ResolutionDependentGoal


class DoseEstimateParameters(BaseModel):
    num_images: int
    exp_time_s: float
    energy_kev: float
    transmission_pct: float
    resolution_a: float
    dose_limit_mgy: float | None = None
    experimental_goal: str | None = None


class AbstractDoseEstimator(HardwareObject):
    """Estimates absorbed radiation dose for given collection parameters."""

    @abstractmethod
    def estimate_dose(self, params: DoseEstimateParameters) -> DoseEstimation:
        """
        Performs the dose estimation.

        Args:
            num_images: Number of images taken during collection
            exp_time_s: Total time the sample is exposed per detector image.
            energy_kev: Beam energy in keV
            transmission_pct: Transmission value as a percentage.
            resolution_a: Resolution in Å.
            dose_limit: Max acceptable total absorbed dose in MGy.
                Can be used to e.g. derive maxImages.
            experimental_goal: Describes experimental setting / goal.
        """
        ...

    @property
    def experimental_goals(self) -> dict[str, ExperimentalGoal]:
        """Preset dose limits exposed to the user.

        Default value of ~10MGy per Å comes from literature, e.g. here:
        https://journals.iucr.org/d/issues/2010/04/00/ba5150/index.html#SEC5
        """
        return {
            "cryo": ResolutionDependentGoal(
                type="resolution_dependent",
                label="Cryo High Resolution",
                mgy_per_angstrom=10,
            )
        }
