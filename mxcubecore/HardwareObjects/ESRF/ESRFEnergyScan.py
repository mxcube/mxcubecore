# encoding: utf-8
#
#  Project name: MXCuBE
#  https://github.com/mxcube.
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
Example xml_ configuration:

.. code-block:: xml

 <object class="ESRF.ESRFXRFSpectrum">
   <object href="/bliss" role="controller"/>
   <cfgfile>/users/blissadm/local/beamline_configuration/misc/15keV.cfg</cfgfile>
   <default_integration_time>3</default_integration_time>
   <default_energy_range>[2.0, 15]</default_energy_range>
   <cfg_energies>[15]</cfg_energies>
 </object>
"""

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


import logging
import subprocess
import time
from datetime import datetime as dt
from pathlib import Path
from shutil import copy2
from zoneinfo import ZoneInfo

import numpy as np
from gevent import event, spawn

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractEnergyScan import AbstractEnergyScan


class GetStaticParameters:
    def __init__(self, config_file, element, edge):
        self.element = element
        self.edge = edge
        self.pars_dict = {}
        self.pars_dict = self._read_from_file(config_file)

    def _read_from_file(self, config_file):
        with Path(config_file).open("r") as fp:
            array = []
            for line in fp:
                if not line.startswith("#") and self.element in line:
                    array = line.split()
                    break

            try:
                static_pars = {}
                static_pars["atomic_nb"] = int(array[0])
                static_pars["eroi_min"] = float(array[11]) / 1000.0
                static_pars["eroi_max"] = float(array[12]) / 1000.0

                if "K" in self.edge:
                    th_energy = float(array[3]) / 1000.0
                elif "1" in self.edge:
                    # L1
                    th_energy = float(array[6]) / 1000.0
                elif "2" in self.edge:
                    # L2
                    th_energy = float(array[7]) / 1000.0
                else:
                    # L or L3
                    th_energy = float(array[8]) / 1000.0

                # all the values are in keV
                static_pars["edgeEnergy"] = th_energy
                static_pars["startEnergy"] = th_energy - 0.05
                static_pars["endEnergy"] = th_energy + 0.05
                static_pars["findattEnergy"] = th_energy + 0.03
                static_pars["remoteEnergy"] = th_energy + 1
            except TypeError:
                return {}
            return static_pars
        return {}


class ESRFEnergyScan(AbstractEnergyScan):
    def __init__(self, name):
        super().__init__(name)
        self.ctrl = None

    def execute_command(self, command_name, *args, **kwargs):
        wait = kwargs.get("wait", True)
        cmd_obj = self.get_command_object(command_name)
        return cmd_obj(*args, wait=wait)

    def init(self):
        self.ctrl = self.get_object_by_role("controller")
        self.ready_event = event.Event()
        if HWR.beamline.lims is None:
            logging.getLogger("HWR").warning(
                "EnergyScan: you should specify the database hardware object"
            )

    def is_connected(self):
        return True

    def get_static_parameters(self, config_file: str, element: str, edge: str) -> dict:
        """Get the static parameters for form the config file.
        Args:
            config_file(str): File to read the configuration from (full path).
            element(str): Element acronym as in the periodic table of elements.
            edge(str): edge line (K, L1, L2, L3)
        """
        pars = GetStaticParameters(config_file, element, edge).pars_dict

        offset_kev = self.get_property("offset_keV")
        pars["startEnergy"] += offset_kev
        pars["endEnergy"] += offset_kev
        pars["element"] = element

        return pars

    def escan_prepare(self):
        """Set the nesessary equipment in position for the scan."""
        self.ctrl.detcover.set_in()
        self.ctrl.diffractometer.fldet_in()
        self.ctrl.diffractometer.set_phase("DataCollection")

    def escan_postscan(self):
        """Actions done after the scan finished."""
        self.ctrl.diffractometer.fldet_out()

    def escan_cleanup(self):
        """Cleanup actions."""
        self.close_fast_shutter()
        HWR.beamline.safety_shutter.close()
        self.emit("energyScanFailed", ())
        self.ready_event.set()

    def close_fast_shutter(self):
        self.ctrl.diffractometer.msclose()

    def open_fast_shutter(self):
        self.ctrl.diffractometer.msopen()

    def cancelEnergyScan(self, *args):
        """Called by queue_entry.py. To be removed"""
        self.escan_cleanup()

    def store_energy_scan(self):
        if HWR.beamline.lims is None:
            return
        try:
            int(self.energy_scan_parameters["sessionId"])
        except (TypeError, KeyError):
            return

        # remove unnecessary for ISPyB fields:
        self.energy_scan_parameters.pop("prefix")
        self.energy_scan_parameters.pop("eroi_min")
        self.energy_scan_parameters.pop("eroi_max")
        self.energy_scan_parameters.pop("findattEnergy")
        self.energy_scan_parameters.pop("edge")
        self.energy_scan_parameters.pop("directory")
        self.energy_scan_parameters.pop("atomic_nb")

        spawn(store_energy_scan_thread, HWR.beamline.lims, self.energy_scan_parameters)

    def do_chooch(
        self, elt: str, edge: str, directory: str, archive_directory: str, prefix: str
    ):
        """Execute peak and IP calculation with chooch.
        Args:
           elt(str): Element acrony as in the periodic table of elements.
           edge(str): Edge like (K, L1, L2, L3).
           directory(str): raw data directory (fill path).
           archive_director(str): archive data directory (fill path).
           prefix(str): File root prefix.
        """
        self.energy_scan_parameters["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")

        raw_data_file = Path(directory) / "data.raw"

        archive_prefix = f"{prefix}_{elt}_{edge}"
        raw_scan_file = Path(directory) / (archive_prefix + ".raw")
        efs_scan_file = raw_scan_file.with_suffix(".efs")
        raw_arch_file = Path(archive_directory) / (archive_prefix + "1" + ".raw")

        i = 0
        while Path(raw_arch_file).is_file():
            i += 1
            raw_arch_file = Path(archive_directory) / (archive_prefix + str(i) + ".raw")

        png_scan_file = raw_scan_file.with_suffix(".png")
        png_arch_file = raw_arch_file.with_suffix(".png")

        if not Path(archive_directory).exists():
            Path(archive_directory).mkdir(parents=True)

        try:
            with Path(raw_scan_file).open("w") as fp:
                scan_data = []
                with Path(raw_data_file).open("r") as raw_file:
                    for line in raw_file.readlines()[2:]:
                        try:
                            x, y = line.split("\t")
                        except (AttributeError, ValueError):
                            x, y = line.split()
                        x = float(x.strip())
                        y = float(y.strip())
                        scan_data.append((x, y))
                        fp.write("%f,%f\r\n" % (x, y))
        except IOError:
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return ()

        # create the gallery directory
        g_dir = Path(directory).parent / "gallery"
        if not Path(g_dir).exists():
            Path(g_dir).mkdir(parents=True)

        copy2(raw_scan_file, raw_arch_file)
        copy2(raw_scan_file, g_dir / raw_arch_file.name)
        self.energy_scan_parameters["scanFileFullPath"] = raw_arch_file

        # while waiting for chooch to work...
        subprocess.call(
            [
                "/cvmfs/sb.esrf.fr/bin/chooch",
                "-e",
                elt,
                "-a",
                edge,
                "-o",
                efs_scan_file,
                "-g",
                png_scan_file,
                raw_data_file,
            ]
        )
        time.sleep(5)
        with Path(efs_scan_file).open("r") as fp:
            for _ in range(3):
                next(fp)
            nparr = np.array([list(map(float, line.split())) for line in fp])
        fpp_peak = nparr[:, 1].max()
        idx = np.where(nparr[:, 1] == fpp_peak)
        pk = nparr[:, 0][idx][0] / 1000.0
        fp_peak = nparr[:, 2][idx][0]
        fpp_infl = nparr[:, 2].min()
        idx = np.where(nparr[:, 2] == fpp_infl)
        ip = nparr[:, 0][idx][0] / 1000.0
        fp_infl = nparr[:, 1][idx][0]
        # get the threshold from the theoretical edge [keV]
        th_t = self.get_property("theoritical_edge_threshold", 0.03)
        rm = pk + th_t

        th_edge = float(self.energy_scan_parameters["edgeEnergy"])

        msg = f"Chooch results: pk = {pk}, ip = {ip}. rm = {rm}.\n"
        msg += f"Theoretical edge: {th_edge}."
        logging.getLogger("HWR").info(msg)

        # +- shift from the theoretical edge [eV]
        edge_shift = 50
        calc_shift = (th_edge - pk) * 1000
        if abs(calc_shift) > edge_shift:
            rm = th_edge + th_t
            comm = "below" if calc_shift > edge_shift else "above"
            msg = f"Calculated peak {pk} is more than {edge_shift} eV {comm} "
            msg += f"the theoretical value {th_edge}. "
            self.energy_scan_parameters["comments"] = msg
            msg += "Check your scan and choose the energies manually"
            logging.getLogger("user_level_log").info(msg)
            pk = 0
            ip = 0

        efs_arch_file = raw_arch_file.with_suffix(".efs")
        if Path(efs_scan_file).is_file():
            copy2(efs_scan_file, efs_arch_file)
            copy2(efs_scan_file, g_dir / efs_arch_file.name)
        else:
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return ()

        self.energy_scan_parameters["filename"] = raw_arch_file.name
        self.energy_scan_parameters["peakEnergy"] = pk
        self.energy_scan_parameters["inflectionEnergy"] = ip
        self.energy_scan_parameters["remoteEnergy"] = rm
        self.energy_scan_parameters["peakFPrime"] = fp_peak
        self.energy_scan_parameters["peakFDoublePrime"] = fpp_peak
        self.energy_scan_parameters["inflectionFPrime"] = fp_infl
        self.energy_scan_parameters["inflectionFDoublePrime"] = fpp_infl

        logging.getLogger("HWR").info("Saving png")
        # prepare to save png files
        title = "%10s  %6s  %6s\n%10s  %6.2f  %6.2f\n%10s  %6.2f  %6.2f" % (
            "energy",
            "f'",
            "f''",
            pk,
            fp_peak,
            fpp_peak,
            ip,
            fp_infl,
            fpp_infl,
        )
        if Path(png_scan_file).is_file():
            copy2(png_scan_file, png_arch_file)
            copy2(png_scan_file, g_dir / png_arch_file.name)
        else:
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return ()

        self.energy_scan_parameters["jpegChoochFileFullPath"] = str(png_arch_file)
        self.store_energy_scan()

        self.emit(
            "chooch_finished",
            (
                pk,
                fpp_peak,
                fp_peak,
                ip,
                fpp_infl,
                fp_infl,
                rm,
                title,
            ),
        )
        return (
            pk,
            fpp_peak,
            fp_peak,
            ip,
            fpp_infl,
            fp_infl,
            rm,
            [],
            [],
            [],
            title,
        )

    def energy_scan_hook(self, energy_scan_parameters: dict):
        """
        Execute actions, required before running the raw scan(like changing
        undulator gaps, move to a given energy... These are in general
        beamline specific actions.
        """
        if self.energy_scan_parameters["findattEnergy"]:
            HWR.beamline.energy.set_value(energy_scan_parameters["findattEnergy"])

    def set_mca_roi(self, eroi_min, eroi_max):
        self.energy_scan_parameters["fluorescenceDetector"] = "KETEK_AXAS-A"
        # check if roi in eV or keV
        if eroi_min > 1000:
            eroi_min /= 1000.0
            eroi_max /= 1000.0
        self.ctrl.mca.set_roi(
            eroi_min,
            eroi_max,
            channel=1,
            element=self.energy_scan_parameters["element"],
            atomic_nb=self.energy_scan_parameters["atomic_nb"],
        )

    def choose_attenuation(self):
        """Choose the appropriate attenuation to execute the scan"""
        eroi_min = self.energy_scan_parameters["eroi_min"]
        eroi_max = self.energy_scan_parameters["eroi_max"]
        self.ctrl.detcover.set_in()
        mcafile = Path(self.energy_scan_parameters["directory"]) / "mca.raw"
        self.ctrl.find_max_attenuation(
            ctime=2, roi=[eroi_min, eroi_max], datafile=mcafile
        )
        self.energy_scan_parameters["transmissionFactor"] = (
            HWR.beamline.transmission.get_value()
        )

    def execute_energy_scan(self, energy_scan_parameters: dict):
        """
        Execute the raw scan sequence. Here is where you pass whatever
        parameters you need to run the raw scan (e.g start/end energy,
        counting time, energy step...).
        """
        start_en = energy_scan_parameters["startEnergy"]
        end_en = energy_scan_parameters["endEnergy"]
        dd = dt.now(tz=ZoneInfo("Europe/Paris"))
        fname = "%s/%s_%s_%s_%s.scan" % (
            energy_scan_parameters["directory"],
            energy_scan_parameters["prefix"],
            dt.datetime.strftime(dd, "%d"),
            dt.datetime.strftime(dd, "%b"),
            dt.datetime.strftime(dd, "%Y"),
        )
        self.ctrl.energy_scan.do_energy_scan(start_en, end_en, datafile=fname)
        self.energy_scan_parameters["exposureTime"] = (
            self.ctrl.energy_scan.exposure_time
        )


def store_energy_scan_thread(db_conn, scan_info):
    scan_info = dict(scan_info)
    blsample_id = scan_info["blSampleId"]
    scan_info.pop("blSampleId")

    try:
        db_status = db_conn.store_energy_scan(scan_info)
        if blsample_id is not None:
            try:
                escan_id = int(db_status["energyScanId"])
            except (NameError, KeyError):
                pass
            else:
                asso = {"blSampleId": blsample_id, "energyScanId": escan_id}
                db_conn.associate_bl_sample_and_energy_scan(asso)
    except Exception:
        logging.getLogger("HWR").exception("Could not store energy")
