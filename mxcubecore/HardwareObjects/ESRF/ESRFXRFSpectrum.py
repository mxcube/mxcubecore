# encoding: utf-8
#
#  Project: MXCuBE
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

"""ESRF XRF scan procedure"""
from unittest.mock import MagicMock
import logging
import os.path
from ast import literal_eval
from shutil import copyfile
import numpy

from mxcubecore.HardwareObjects.abstract.AbstractXRFSpectrum import AbstractXRFSpectrum

try:
    from PyMca import ConfigDict
    from PyMca import ClassMcaTheory
    from PyMca import QtMcaAdvancedFitReport
except ImportError:
    from PyMca5.PyMca import ConfigDict
    from PyMca5.PyMca import ClassMcaTheory
    from PyMca5.PyMca import QtMcaAdvancedFitReport

# Next line is a trick to avoid core dump in QtMcaAdvancedFitReport
QtMcaAdvancedFitReport.qt = MagicMock()


class ESRFXRFSpectrum(AbstractXRFSpectrum):
    """ESRF implementation of the XRF spectrum procedure"""

    def __init__(self, name):
        super().__init__(name)
        self.ctrl_hwobj = None
        self.cfgfile = None
        self.config = None
        self.mcafit = None
        self.default_erange = []
        self.cfg_energies = []

    def init(self):
        super().init()
        self.ctrl_hwobj = self.get_object_by_role("controller")
        self.cfgfile = self.get_property(
            "cfgfile", "/users/blissadm/local/beamline_configuration/misc/15keV.cfg"
        )
        self.config = ConfigDict.ConfigDict()
        self.mcafit = ClassMcaTheory.McaTheory(self.cfgfile)
        self.default_erange = literal_eval(
            self.get_property("default_energy_range", "[2.0, 15.0]")
        )
        self.cfg_energies = literal_eval(
            self.get_property("cfg_energies", "[7, 9, 12, 15]")
        )
        self.cfg_energies.reverse()

    def _do_xrf_spectrum(self):
        """Do the xrf spectrum - choose appropriate maximum attenuation.
           Save the data file.
        Returns:
            (bool): Procedure executed correcly (True) or error (False)
        """
        # protect the detector
        self.ctrl_hwobj.detcover.set_in(20)
        try:
            current_trs = self.ctrl_hwobj.find_max_attenuation(
                ctime=self.spectrum_info_dict["exposureTime"],
                fname=self.spectrum_info_dict["filename"],
                roi=self.default_erange,
            )
            self.spectrum_info_dict["beamTransmission"] = current_trs
        except Exception as exp:
            logging.getLogger("user_level_log").exception(str(exp))
            self.spectrum_command_failed()
            return False

        # put away the fluo detector
        self.ctrl_hwobj.diffractometer.fldet_out(timeout=0)
        return True

    # Next methods are for fitting the data with pymca

    def _get_cfgfile(self, energy):
        """PyMca configuration file to be used for the fitting"""
        cfgname = "15"
        for egy in self.cfg_energies:
            if energy <= egy:
                cfgname = str(egy)
        return os.path.join(self.cfg_path, f"{cfgname}keV.cfg")

    def mcafit_configuration(self, config=None):
        """Configure the fitting parameters. The procedure is time consuming.
           It is only executed if the last configuration file is not the same.
        Args:
            config(dict): Configuration dictionary, containing among others the
                          configuration file name.
        """
        change = False
        if not config or "file" not in config:
            cfgfile = self._get_cfgfile(self.spectrum_info_dict["energy"])
        else:
            cfgfile = config["file"]

        if self.cfgfile != cfgfile:
            self.cfgfile = cfgfile
            change = True
        self.config.read(self.cfgfile)
        if "concentrations" not in self.config:
            self.config["concentrations"] = {}
            change = True
        if "attenuators" not in self.config:
            self.config["attenuators"] = {"Matrix": [1, "Water", 1.0, 0.01, 45.0, 45.0]}
            change = True
        if "flux" in config:
            self.config["concentrations"]["flux"] = float(config["flux"])
            change = True
        if "time" in config:
            self.config["concentrations"]["time"] = float(config["time"])
            change = True

        if change:
            self.mcafit.configure(self.config)

    def spectrum_analyse(self):
        """Get the spectrum data. Do analysis and save fitted data."""
        config = {}
        data = self.ctrl_hwobj.mca.read_roi_data(0)
        calib = self.ctrl_hwobj.mca.calibration
        config["energy"] = self.sspectrum_info_dict["energy"]
        config["bsX"] = self.spectrum_info_dict["beamSizeHorizontal"]
        config["bsY"] = self.spectrum_info_dict["beamSizeVertical"]
        roi = self.ctrl_hwobj.mca.get_roi(0)
        config["min"] = roi["chmin"]
        config["max"] = roi["chmax"]
        config["legend"] = self.self.spectrum_info_dict["annotatedPymcaXfeSpectrum"]
        config["htmldir"] = self.spectrum_info_dict["htmldir"]
        config["file"] = self._get_cfgfile(config["energy"])

        self.mcafit_run(data, calib, config)

        # copy files to archive directory
        # data
        if self.spectrum_info_dict["scanFileFullPath"]:
            copyfile(
                self.spectrum_info_dict["filename"],
                self.spectrum_info_dict["scanFileFullPath"],
            )
        # png
        pngfile = self.spectrum_info_dict["filename"].replace(".raw", ".png")
        if self.spectrum_info_dict["jpegScanFileFullPath"]:
            if os.path.isfile(pngfile):
                copyfile(pngfile, self.spectrm_info_dict["jpegScanFileFullPath"])

    def mcafit_run(self, data, calib=None, config=None):
        """Execute the fitting. Write the fitted data files to archive directory.
        Args:
            data (list): The raw data.
            calib (list): The mca calibration.
            config (dict): The configuration dictionary.
        """
        if config:
            self.mcafit_configuration(config)
        try:
            if data[0].size == 2:
                xdata = numpy.array(data[:, 0]) * 1.0
                ydata = numpy.array(data[:, 1])
            else:
                xdata = data[0] * 1.0
                ydata = data[1]

            self.mcafit.setData(
                xdata,
                ydata,
                xmin=int(config["min"]),
                xmax=int(config["max"]),
                calibration=calib,
            )

            self.mcafit.estimate()

            fitresult = self.mcafit.startfit(digest=1)
            if fitresult:
                fitresult = {"fitresult": fitresult[0], "result": fitresult[1]}

                # write the csv file to archive directory
                csvname = self.spectrum_info_dict["fittedDataFileFullPath"]
                self._write_csv_file(fitresult, csvname)

                # write html report to archive directory
                outfile = os.path.basename(self.spectrum_info_dict["filename"]).split(
                    "."
                )[0]
                # outdir = os.path.dirname(
                #    self.spectrum_info_dict["annotatedPymcaXfeSpectrum"])

                _kw = {
                    "outdir": self.spectrum_info_dict["htmldir"],
                    "outfile": outfile,
                    "fitresult": fitresult,
                    "plotdict": {"logy": False},
                }

                report = QtMcaAdvancedFitReport.QtMcaAdvancedFitReport(**_kw)
                report.writeReport(text=report.getText())
        except Exception as exp:
            msg = f"XRFSpectrum: problem fitting {exp}"
            logging.getLogger("user_level_log").exception(msg)
            self.spectrumCommandFailed()
            return False

    def _write_csv_file(self, fitresult, fname=None):
        """Write data to a csv file.
        Args:
            fitresult(dict): Data as dictionary.
        Kwargs:
            fname (str): Filename to write to (full path).
        """
        fname = fname or self.spectrum_info_dict["fittedDataFileFullPath"]
        if os.path.exists(fname):
            os.remove(fname)

        # get the significant peaks
        peaks_dict = {}
        grp_len = len(fitresult["result"]["groups"])
        nglobal = len(fitresult["result"]["parameters"]) - grp_len
        parameters = fitresult["result"]["fittedpar"][:nglobal] + [0.0] * grp_len

        for grp in fitresult["result"]["parameters"][nglobal:]:
            idx = fitresult["result"]["parameters"].index(grp)
            parameters[idx] = fitresult["result"]["fittedpar"][idx]
            xmatrix = fitresult["result"]["xdata"]
            ymatrix = self.mcafit.mcatheory(parameters, xmatrix)
            ymatrix.shape = [len(ymatrix), 1]
            label = "y" + grp
            if self.mcafit.STRIP:
                peaks_dict[label] = ymatrix + self.mcafit.zz
            else:
                peaks_dict[label] = ymatrix
            peaks_dict[label].shape = (len(peaks_dict[label]),)
            parameters[idx] = 0.0

        delimiter = ","
        header = '"channel"%s"Energy"%s"counts"%s"fit"%s"continuum"%s"pileup"' % (
            delimiter,
            delimiter,
            delimiter,
            delimiter,
            delimiter,
        )

        # add the peaks labels
        for key in peaks_dict:
            header += delimiter + (f'"{key}"')
        # logging.getLogger("user_level_log").info("Writing %s" % fname)
        with open(fname, "w") as csv_fd:
            csv_fd.write(header)
            csv_fd.write("\n")
            for i in range(fitresult["result"]["xdata"].size):
                csv_fd.write(
                    "%.7g%s%.7g%s%.7g%s%.7g%s%.7g%s%.7g"
                    % (
                        fitresult["result"]["xdata"][i],
                        delimiter,
                        fitresult["result"]["energy"][i],
                        delimiter,
                        fitresult["result"]["ydata"][i],
                        delimiter,
                        fitresult["result"]["yfit"][i],
                        delimiter,
                        fitresult["result"]["continuum"][i],
                        delimiter,
                        fitresult["result"]["pileup"][i],
                    )
                )
                for val in peaks_dict.values():
                    csv_fd.write(f"{delimiter}{val[i]:.7g}")

                csv_fd.write("\n")
