"""Dose rate estimation from the beamline flux."""

from typing import Literal

from pydantic import BaseModel

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import ConfiguredObject, HardwareObject


class StaticGoal(BaseModel):
    type: Literal["static"]
    label: str
    mgy: float


class ResolutionDependentGoal(BaseModel):
    type: Literal["resolution_dependent"]
    label: str
    mgy_per_angstrom: float


ExperimentalGoal = StaticGoal | ResolutionDependentGoal


class DoseEstimationError(Exception):
    """The dose can not be estimated. The message is shown to the user."""


class DoseEstimator(HardwareObject):
    """Estimates the dose rate from the average flux density over the beam.

    This is an example YAML configuration
    .. code-block:: yaml
        class: DoseEstimator.DoseEstimator
        configuration:
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

    class HOConfig(ConfiguredObject.HOConfig):
        # Default value of ~10MGy per Å comes from literature, e.g. here:
        # https://journals.iucr.org/d/issues/2010/04/00/ba5150/index.html#SEC5
        experimental_goals: dict[str, ExperimentalGoal] = {
            "cryo": ResolutionDependentGoal(
                type="resolution_dependent",
                label="Cryo High Resolution",
                mgy_per_angstrom=10,
            )
        }

    def estimate_dose_rate(self, energy_kev: float, transmission_pct: float) -> float:
        """Dose rate for a standard composition crystal.

        Args:
            energy_kev: Beam energy in keV.
            transmission_pct: Transmission value as a percentage.

        Returns:
            Dose rate in MGy/s.

        Raises:
            DoseEstimationError: If the dose rate can not be estimated.
        """
        flux = HWR.beamline.flux
        density = flux.get_average_flux_density(
            transmission=transmission_pct, energy=energy_kev
        )
        if not density:
            msg = f"Flux at {energy_kev} keV is not known, measure it first."
            raise DoseEstimationError(msg)
        try:
            gy_per_photon_per_mmsq = flux.get_dose_rate_per_photon_per_mmsq(energy_kev)
        except ValueError as ex:
            # The default table raises a ValueError outside of its energy range
            msg = f"No dose model for {energy_kev} keV."
            raise DoseEstimationError(msg) from ex
        # Gy/(photons/mm^2) * photons/s/mm^2 = Gy/s
        return float(gy_per_photon_per_mmsq * density * 1e-6)

    @property
    def experimental_goals(self) -> dict[str, ExperimentalGoal]:
        """Preset dose limits exposed to the user."""
        return self._config.experimental_goals
