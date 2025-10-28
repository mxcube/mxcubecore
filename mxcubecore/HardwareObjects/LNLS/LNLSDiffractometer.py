#
#  Project name: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import logging
import random
import time

from gevent.event import AsyncResult

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.GenericDiffractometer import GenericDiffractometer


class LNLSDiffractometer(GenericDiffractometer):
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        GenericDiffractometer.__init__(self, name)

        # child object slots
        self.backlight = None
        self.backlightswitch = None
        self.beamstop_distance = None
        self.focus = None
        self.frontlight = None
        self.frontlightswitch = None
        self.phi = None
        self.phiy = None
        self.phiz = None
        self.sampx = None
        self.sampy = None

    def init(self):
        """
        Descript. :
        """
        # self.image_width = 100
        # self.image_height = 100

        GenericDiffractometer.init(self)
        # Bzoom: 1.86 um/pixel (or 0.00186 mm/pixel) at minimum zoom
        self.x_calib = 0.00186
        self.y_calib = 0.00186
        self.last_centred_position = [318, 238]

        self.pixels_per_mm_x = 1.0 / self.x_calib
        self.pixels_per_mm_y = 1.0 / self.y_calib
        self.beam_position = [318, 238]

        self.current_phase = GenericDiffractometer.PHASE_CENTRING

        self.cancel_centring_methods = {}
        self.current_motor_positions = {
            "phiy": 1.0,
            "sampx": 0.0,
            "sampy": -1.0,
            "zoom": 8.53,
            "focus": -0.42,
            "phiz": 1.1,
            "phi": 311.1,
            "kappa": 11,
            "kappa_phi": 22.0,
        }

        self.current_state_dict = {}
        self.centring_status = {"valid": False}
        self.centring_time = 0

        self.mount_mode = self.get_property("sample_mount_mode")
        if self.mount_mode is None:
            self.mount_mode = "manual"

        self.equipment_ready()

        self.connect(self.motor_hwobj_dict["phi"], "valueChanged", self.phi_motor_moved)
        self.connect(
            self.motor_hwobj_dict["phiy"], "valueChanged", self.phiy_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["phiz"], "valueChanged", self.phiz_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["kappa"], "valueChanged", self.kappa_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["kappa_phi"],
            "valueChanged",
            self.kappa_phi_motor_moved,
        )
        self.connect(
            self.motor_hwobj_dict["sampx"], "valueChanged", self.sampx_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["sampy"], "valueChanged", self.sampy_motor_moved
        )

    def manual_centring(self):
        """
        Descript. :
        """
        print("Iniciando centragem manual...")
        for click in range(3):
            print(f"Aguardando clique do usuário ({click + 1}/3)...")
            self.user_clicked_event = AsyncResult()
            x, y = self.user_clicked_event.get()
            print(f"Usuário clicou nas coordenadas: x={x}, y={y}")

            # go to beam
            print("Movendo para o feixe com as coordenadas clicadas.")
            res = self.move_to_beam(x, y)  # wait before continue
            print(f"Resultado do movimento para o feixe: {res}")

            if click < 2:
                print(
                    f"Executando rotação relativa do motor phi em 90 graus (click={click})..."
                )
                self.motor_hwobj_dict["phi"].set_value_relative(90)

        print(f"Salvando última posição centrada: x={x}, y={y}")
        self.last_centred_position[0] = x
        self.last_centred_position[1] = y

        print("Centragem manual finalizada.")
        return {}

    def automatic_centring(self):
        """Automatic centring procedure"""
        print("Iniciando centragem automática...")

        centred_pos_dir = self._get_random_centring_position()
        print(f"Posição centrada gerada automaticamente: {centred_pos_dir}")

        self.emit("newAutomaticCentringPoint", centred_pos_dir)
        print("Sinal 'newAutomaticCentringPoint' emitido.")

        return centred_pos_dir

    def _get_random_centring_position(self):
        """Get random centring result for current positions"""

        # Names of motors to vary during centring
        vary_actuator_names = ("sampx", "sampy", "phiy")

        # Range of random variation
        var_range = 0.08

        # absolute value limit for varied motors
        var_limit = 2.0

        result = self.current_motor_positions.copy()
        for tag in vary_actuator_names:
            val = result.get(tag)
            if val is not None:
                random_num = random.random()
                var = (random_num - 0.5) * var_range
                val += var
                if abs(val) > var_limit:
                    val *= 1 - var_range / var_limit
                result[tag] = val
        return result

    def is_ready(self) -> bool:
        """
        Descript. :
        """
        return True

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Descript. :
        """
        centred_pos_dir = self._get_random_centring_position()
        return centred_pos_dir

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        return self.last_centred_position[0], self.last_centred_position[1]

    def phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phi"] = pos
        self.emit("phiMotorMoved", pos)

    def phiy_motor_moved(self, pos):
        self.current_motor_positions["phiy"] = pos

    def phiz_motor_moved(self, pos):
        self.current_motor_positions["phiz"] = pos

    def sampx_motor_moved(self, pos):
        self.current_motor_positions["sampx"] = pos

    def sampy_motor_moved(self, pos):
        self.current_motor_positions["sampy"] = pos

    def kappa_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["kappa"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaMotorMoved", pos)

    def kappa_phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["kappa_phi"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaPhiMotorMoved", pos)

    def calculate_move_to_beam_pos(self, x, y):
        """
        Descript. : calculate motor positions to put sample on the beam.
        Returns: dict of motor positions
        """

        # Atualiza posição atual do feixe
        self.beam_position[0], self.beam_position[1] = (
            HWR.beamline.beam.get_beam_position_on_screen()
        )
        print(f"Posição atual do feixe na tela: {self.beam_position}")

        # Armazena clique do usuário
        self.last_centred_position[0] = x
        self.last_centred_position[1] = y
        print(f"Última posição clicada pelo usuário: x={x}, y={y}")

        # Obtém posições atuais dos motores
        omega_pos = self.motor_hwobj_dict["phi"].get_value()
        goniox_pos = self.motor_hwobj_dict["phiz"].get_value()
        sampx_pos = self.motor_hwobj_dict["sampx"].get_value()
        sampy_pos = self.motor_hwobj_dict["sampy"].get_value()
        print(
            f"Posições atuais dos motores: omega={omega_pos}, phiz={goniox_pos}, sampx={sampx_pos}, sampy={sampy_pos}"
        )

        # Cálculo da movimentação de goniox
        import math

        drx_goniox = abs(-x - y + 1152) / math.sqrt(2)
        dir_goniox = 1 if y <= (-x + 1152) else -1
        move_goniox = dir_goniox * drx_goniox / self.pixels_per_mm_x + goniox_pos
        print(f"Movimento calculado para phiz (goniox): {move_goniox:.4f}")

        # Cálculo da movimentação em Y
        dry_samp = abs(x - y - 128) / math.sqrt(2)
        dir_samp = 1 if y >= x - 128 else -1
        move_samp = dir_samp * dry_samp
        print(
            f"Movimento intermediário para centragem vertical (samp): {move_samp:.4f}"
        )

        move_sampy = move_samp / self.pixels_per_mm_y
        print(f"Conversão para mm em Y: move_sampy = {move_sampy:.4f}")

        move_sampy += sampy_pos
        print(f"Posição absoluta destino para sampy: {move_sampy:.4f}")

        # Criação do dicionário de destino
        centred_pos_dir = {"phiz": move_goniox, "sampy": move_sampy}
        print(f"Posições alvo calculadas para centragem: {centred_pos_dir}")

        return centred_pos_dir

    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """
        logging.getLogger("HWR").info("Moving to beam...")
        print(f"Initializing beam centering with beam at x={x}, y={y}...")

        centred_pos_dir = self.calculate_move_to_beam_pos(x, y)

        print("Moving to beam...")
        self.move_to_motors_positions(centred_pos_dir, wait=True)

        logging.getLogger("HWR").info("Move to beam has finished...")
        return centred_pos_dir

    def start_move_to_beam(self, coord_x=None, coord_y=None, omega=None):
        """
        Descript. :
        """
        self.last_centred_position[0] = coord_x
        self.last_centred_position[1] = coord_y
        self.centring_time = time.time()
        curr_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.centring_status = {
            "valid": True,
            "startTime": curr_time,
            "endTime": curr_time,
        }
        motors = self.get_positions()
        self.last_centred_position[0] = coord_x
        self.last_centred_position[1] = coord_y
        self.centring_status["motors"] = motors
        self.centring_status["valid"] = True
        self.centring_status["angleLimit"] = False
        self.emit_progress_message("")
        self.accept_centring()
        self.current_centring_method = None
        self.current_centring_procedure = None

    def re_emit_values(self):
        self.emit("zoomMotorPredefinedPositionChanged", None, None)
        omega_ref = [0, 238]
        self.emit("omegaReferenceChanged", omega_ref)

    def move_omega_relative(self, relative_angle):
        self.motor_hwobj_dict["phi"].set_value_relative(relative_angle, 5)

    def set_phase(self, phase, timeout=None):
        self.current_phase = str(phase)
        self.emit("minidiffPhaseChanged", (self.current_phase,))
