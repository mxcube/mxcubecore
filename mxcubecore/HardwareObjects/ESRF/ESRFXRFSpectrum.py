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
from warnings import warn
import numpy

from mxcubecore.HardwareObjects.abstract.AbstractXRFSpectrum import AbstractXRFSpectrum

from PyMca5.PyMca import ConfigDict
from PyMca5.PyMca import ClassMcaTheory
from PyMca5.PyMca import QtMcaAdvancedFitReport

# Next line is a trick to avoid core dump in QtMcaAdvancedFitReport
QtMcaAdvancedFitReport.qt = MagicMock()


class ESRFXRFSpectrum(AbstractXRFSpectrum):
    """ESRF implementation of the XRF spectrum procedure"""

    def __init__(self, name):
        super().__init__(name)
        self.cfgfile = None
        self.config = None
        self.ctrl_hwobj = None
        self.mcafit = None
        self.default_erange = None
        self.cfg_energies = []

    def init(self):
        super().init()
        self.ctrl_hwobj = self.get_object_by_role("controller")
        self.cfgfile = self.get_property(
            "cfgfile", "/users/blissadm/local/beamline_configuration/misc/15keV.cfg"
        )
        self.config = ConfigDict.ConfigDict()
        self.mcafit = ClassMcaTheory.McaTheory(self.cfgfile)
        self.default_integration_time = self.get_property(
            "default_integration_time", 3.5
        )
        self.default_erange = literal_eval(
            self.get_property("default_energy_range", "[2.0, 15.0]")
        )
        self.cfg_energies = literal_eval(
            self.get_property("cfg_energies", "[7, 9, 12, 15]")
        )

    def _doSpectrum(self, ctime, filename):
        warn(
            "_doSpectrum is deprecated. use _execute_xrf_spectrum",
            DeprecationWarning,
        )
        return self._execute_xrf_spectrum(ctime, filename)

    def _execute_xrf_spectrum(self, integration_time=None, filename=None):
        """Local XRF spectrum sequence.
        Args:
            integration_time (float): MCA integration time [s].
            filename (str): Data file (full path).
        Returns:
            (bool): Procedure executed correcly (True) or error (False)
        """
        filename = filename or self.spectrum_info_dict["filename"]
        integration_time = integration_time or self.default_integration_time

        # protect the detector
        self.ctrl_hwobj.detcover.set_in(20)
        try:
            current_transm = self.ctrl_hwobj.find_max_attenuation(
                ctime=float(integration_time),
                datafile=filename,
                roi=self.default_erange,
            )
            self.spectrum_info_dict["beamTransmission"] = current_transm
        except Exception as exp:
            logging.getLogger("user_level_log").exception(str(exp))
            self.spectrum_command_failed()
            return False

        # put away the fluo detector
        self.ctrl_hwobj.diffractometer.fldet_out()
        return True

    # Next methods are for fitting the data with pymca

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

    def spectrum_analyse(self, data=None, calib=None, config=None):
        """Execute the fitting. Write the fitted data files to pyarch.
        Args:
            data (list): The raw data.
            calib (list): The mca calibration.
            config (dict): The configuration dictionary.
        """
        # check if we need this!!!
        if not config:
            config = {
                "energy": self.spectrum_info_dict["energy"],
                "att": self.spectrum_info_dict["beamTransmission"],
                "bsX": self.spectrum_info_dict["beamSizeHorizontal"],
                "bsY": self.spectrum_info_dict["beamSizeVertical"],
                "legend": self.spectrum_info_dict["annotatedPymcaXfeSpectrum"],
                "htmldir": os.path.split(
                    self.spectrum_info_dict["annotatedPymcaXfeSpectrum"]
                )[0],
            }

        self.mcafit_configuration(config)
        calib = calib or self.ctrl_hwobj.mca.calibration

        # the spectra is read by the find_max_attenuation procedure.
        # We only need the date not to read it again
        data = data or self.ctrl_hwobj.mca.data

        try:
            if data[0].size == 2:
                xdata = numpy.array(data[:, 0]) * 1.0
                ydata = numpy.array(data[:, 1])
            else:
                xdata = data[0] * 1.0
                ydata = data[1]

            xmin = self.config["min"]
            xmax = self.config["max"]
            self.mcafit.setData(xdata, ydata, xmin=xmin, xmax=xmax, calibration=calib)

            self.mcafit.estimate()

            fitresult = self.mcafit.startfit(digest=1)
            if fitresult:
                fitresult = {"fitresult": fitresult[0], "result": fitresult[1]}

                # write the csv file to pyarch
                csvname = self.spectrum_info_dict["fittedDataFileFullPath"]
                self._write_csv_file(fitresult, csvname)

                # write html report to pyarch
                fname = os.path.basename(self.spectrum_info_dict["filename"])
                outfile = fname.split(".")[0]
                outdir = os.path.dirname(
                    self.spectrum_info_dict["annotatedPymcaXfeSpectrum"]
                )

                _kw = {
                    "outdir": outdir,
                    "outfile": outfile,
                    "fitresult": fitresult,
                    "plotdict": {"logy": False},
                }

                report = QtMcaAdvancedFitReport.QtMcaAdvancedFitReport(**_kw)
                text = report.getText()
                report.writeReport(text=text)
                return True
            return False
        except Exception as exp:
            msg = f"XRFSpectrum: problem fitting {exp}\nPlease check the raw "
            msg += f"data file {self.spectrum_info_dict['scanFileFullPath']}"
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
        pars_len = len(fitresult["result"]["parameters"])
        grp_len = len(fitresult["result"]["groups"])
        nglobal = pars_len - grp_len
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
        header = f'"channel"{delimiter}"Energy"{delimiter}"counts"{delimiter}'
        header += f'"fit"{delimiter}"continuum"{delimiter}"pileup"'

        # add the peaks label
        for key in peaks_dict:
            header += delimiter + f'"{key}"'
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
                for key in peaks_dict:
                    csv_fd.write(f"{delimiter}{peaks_dict[key][i]:.7g}")

                csv_fd.write("\n")

    def _get_cfgfile(self, energy):
        """Get the correct configuration file"""
        self.cfg_energies.sort()

        for egy in self.cfg_energies:
            if egy > energy:
                return os.path.join(self.cfg_path, f"{str(egy)}keV.cfg")
        return self.cfgfile
