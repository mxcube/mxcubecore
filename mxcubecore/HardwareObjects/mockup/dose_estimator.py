"""Mock-up class to simulate dose estimation, used for testing."""

import random

from pydantic import BaseModel

from mxcubecore.HardwareObjects.abstract.AbstractDoseEstimator import (
    AbstractDoseEstimator,
    DoseEstimateParameters,
    DoseEstimation,
    DoseEstimationError,
    DoseEstimationOk,
    ExperimentalGoal,
    ResolutionDependentGoal,
    StaticGoal,
)

_DEFAULT_EXPERIMENTAL_GOALS: dict[str, ExperimentalGoal] = {
    "cryo_highres": ResolutionDependentGoal(
        type="resolution_dependent",
        label="Cryo High Resolution",
        mgy_per_angstrom=10,
    ),
    "room": StaticGoal(type="static", label="Room Temperature", mgy=0.2),
    "s_sad": StaticGoal(type="static", label="S-SAD", mgy=5),
}


class MockupDoseEstimator(AbstractDoseEstimator):
    """Simulated dose estimation.

    There is no physics here: the dose is simply proportional to the total
    exposure and the transmission, with an arbitrary dose rate. That is enough
    to see on the demo beamline that the estimation is wired up.

    A fraction of the estimations fails at random, so that the error path shows
    up in the demo on its own.

    This is an example YAML configuration
    .. code-block:: yaml
        class: mxcubecore.HardwareObjects.mockup.dose_estimator.MockupDoseEstimator
        configuration:
            dose_rate_mgy_per_s: 1.0
            error_probability: 0.1
            experimental_goals:
                cryo_highres:
                    label: Cryo High Resolution
                    type: resolution_dependent
                    mgy_per_angstrom: 10
                room:
                    label: Room Temperature
                    type: static
                    mgy: 0.2
    """

    class HOConfig(BaseModel):
        # Arbitrary dose rate at 100% transmission, in MGy/s.
        dose_rate_mgy_per_s: float = 1.0
        experimental_goals: dict[str, ExperimentalGoal] = _DEFAULT_EXPERIMENTAL_GOALS
        # Fraction of the estimations that fail.
        error_probability: float = 0.1

    def estimate_dose(self, params: DoseEstimateParameters) -> DoseEstimation:
        if random.random() < self._config.error_probability:  # noqa: S311
            return DoseEstimationError(
                msg="Randomly generated error, to simulate a failing estimation."
            )

        if params.num_images <= 0 or params.exp_time_s <= 0:
            return DoseEstimationError(
                msg="Number of images and exposure time must be positive."
            )

        dose_per_image_mgy = (
            self._config.dose_rate_mgy_per_s
            * params.exp_time_s
            * params.transmission_pct
            / 100
        )
        max_images = (
            int(params.dose_limit_mgy / dose_per_image_mgy)
            if params.dose_limit_mgy and dose_per_image_mgy > 0
            else None
        )
        return DoseEstimationOk(
            dose_mgy=dose_per_image_mgy * params.num_images,
            max_images=max_images,
        )

    @property
    def experimental_goals(self) -> dict[str, ExperimentalGoal]:
        return self._config.experimental_goals
