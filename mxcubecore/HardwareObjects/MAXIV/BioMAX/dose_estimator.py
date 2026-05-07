from typing import TYPE_CHECKING

from pydantic.v1 import BaseModel

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractDoseEstimator import (
    AbstractDoseEstimator,
    DoseEstimateParameters,
    DoseEstimation,
    DoseEstimationError,
    DoseEstimationOk,
    ExperimentalGoal,
)

if TYPE_CHECKING:
    from mxcubecore.HardwareObjects.MAXIV.BioMAX.BIOMAXFlux import BIOMAXFlux
    from mxcubecore.HardwareObjects.MAXIV.Energy import Energy


class _PolynomialSegment(BaseModel):
    """
    Represents the coefficients of piecewise cubic regression.

    Flux value for given energy is being estimated using
    parameters gathered during beamline operation at BioMAX.
    Estimated energy is calculated differently for specific
    thresholds.
    """

    max_energy_ev: int
    coeffs: list[float]


class DoseEstimator(AbstractDoseEstimator):
    """Implementation of dose estimation for BioMAX.

    This is an example YAML configuration
    .. code-block:: yaml
        class: MAXIV.BioMAX.dose_estimator.DoseEstimator
        configuration:
            flux_coefficients:
                - max_energy_ev: 9060
                    coeffs: [1.40919e14, -6.95909e10, 1.10638e7, -553.774]
                - max_energy_ev: 12610
                    coeffs: [1.40919e14, -6.95909e10, 1.10638e7, -553.774]
                - max_energy_ev: 18750
                    coeffs: [1.59363e14, -2.78613e10, 1.69424e6, -35.0571]
                - max_energy_ev: 20400
                    coeffs: [1.00206e12, 2.65477e9, -240059, 5.44578]
                - max_energy_ev: 24000
                    coeffs: [5.06378e14, -6.52503e10, 2.81565e6, -40.6289]
            experimental_goals:
                cryo_highres:
                    label: Cryo High Resolution
                    type: resolution_dependent
                    mgy_per_angstrom: 10
                room:
                    label: Room Temperature
                    type: static
                    mgy: 0.2
                cys_cys:
                    label: Cys-Cys
                    type: static
                    mgy: 2
                s_sad:
                    label: S-SAD
                    type: static
                    mgy: 5
                mad_sad:
                    label: MAD/SAD
                    type: static
                    mgy: 6
    """

    class HOConfig(BaseModel):
        flux_coefficients: list[_PolynomialSegment]
        experimental_goals: dict[str, ExperimentalGoal]

    def __init__(self, name: str) -> None:
        self._energy_hwo: Energy | None = None
        self._flux_hwo: BIOMAXFlux | None = None
        super().__init__(name)

    def init(self) -> None:
        super().init()

        self._energy_hwo = HWR.beamline.energy
        self._flux_hwo = HWR.beamline.flux

    def _get_flux_t_current(self, energy_ev: float) -> float:
        buckets = self._config.flux_coefficients
        for bucket in buckets:
            # in here flux_coefficients is assumed to always have
            # the max_energy_ev thresholds in ascending order.
            if energy_ev <= bucket.max_energy_ev:
                return sum(
                    coeff * energy_ev**exponent
                    for exponent, coeff in enumerate(bucket.coeffs)
                )
        max_energy_ev = max(bucket.max_energy_ev for bucket in buckets)
        err_msg = f"Energy out of bounds. Max available value is {max_energy_ev} eV."
        raise ValueError(err_msg)

    def estimate_dose(  # noqa: PLR0911  many returns make it clearer :)
        self,
        params: DoseEstimateParameters,
    ) -> DoseEstimation:
        flux = self._flux_hwo.get_value()  # ph/s

        if flux <= 0:
            return DoseEstimationError(msg="No flux detected, can't estimate dose.")

        beamline_flux_density = self._flux_hwo.flux_density

        if beamline_flux_density == -1:
            return DoseEstimationError(
                msg="Flux has not been measured. Please measure it first"
            )
        if beamline_flux_density == 0:
            return DoseEstimationError(
                msg="No beam has been detected during flux measurements!"
            )

        flux_density_energy = self._flux_hwo.flux_density_energy

        if flux_density_energy <= 0:
            return DoseEstimationError(msg="Energy at the time of measurement unknown.")

        beamline_energy = self._energy_hwo.get_value()  # keV

        try:
            flux_at_beamline_energy = self._get_flux_t_current(
                energy_ev=beamline_energy * 1_000
            )
        except ValueError as ex:
            return DoseEstimationError(msg=str(ex))

        if flux_at_beamline_energy <= 0:
            return DoseEstimationError(msg="Flux model predicts value <= 0")

        # This is a relative error term for the flux measurements.
        flux_scale = flux_at_beamline_energy / flux
        try:
            user_flux = (
                self._get_flux_t_current(energy_ev=params.energy_kev * 1_000)
                / flux_scale
            )
        except ValueError as ex:
            return DoseEstimationError(msg=str(ex))

        beam_size_x, beam_size_y = HWR.beamline.beam.get_beam_size()  # mm

        user_flux_density = (user_flux * params.transmission_pct / 100) / (
            beam_size_x * beam_size_y * 1e6
        )
        wavelength = self._energy_hwo.calculate_wavelength(energy=params.energy_kev)
        # The 2000 constant comes from old code.
        dose_rate = user_flux_density / (2000 / wavelength / wavelength)
        estimated_dose_gy = dose_rate * params.exp_time_s * params.num_images
        max_images = (
            (params.dose_limit_mgy * 1_000_000) / dose_rate / params.exp_time_s
            if params.dose_limit_mgy
            else None
        )
        return DoseEstimationOk(
            dose_mgy=estimated_dose_gy / 1_000_000,
            max_images=max_images,
        )

    @property
    def experimental_goals(self) -> dict[str, ExperimentalGoal]:
        return self._config.experimental_goals
