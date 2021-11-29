import logging
import os.path
import numpy

from mxcubecore.HardwareObjects.XRFSpectrum import XRFSpectrum

try:
    from PyMca import ConfigDict
    from PyMca import ClassMcaTheory
    from PyMca import QtMcaAdvancedFitReport
except ImportError:
    from PyMca5.PyMca import ConfigDict
    from PyMca5.PyMca import ClassMcaTheory
    from PyMca5.PyMca import QtMcaAdvancedFitReport

"""
Next two lines is a trick to avoid core dump in QtMcaAdvancedFitReport
"""
from unittest.mock import MagicMock
QtMcaAdvancedFitReport.qt = MagicMock()


class ID29XRFSpectrum(XRFSpectrum):
    def __init__(self, *args, **kwargs):
        XRFSpectrum.__init__(self, *args, **kwargs)
        self.mca_hwobj = self.get_object_by_role("mca")
        self.ctrl_hwobj = self.get_object_by_role("controller")
        self.beamsize = self.get_object_by_role("beamsize")
        self.fname = self.get_property("cfgfile")
        self.config = ConfigDict.ConfigDict()
        self.mcafit = ClassMcaTheory.McaTheory(self.fname)
        self.default_integration_time = self.get_property("default_integration_time", 3.5)

    def preset_mca(self, ctime=None, fname=None):
        try:
            ctime = float(ctime)
        except (TypeError, ValueError):
            ctime = self.default_integration_time
    
        self.mca_hwobj.set_roi(2, 15, channel=1)
        self.mca_hwobj.set_presets(erange=1, ctime=ctime, fname=str(fname))
        self.ctrl_hwobj.mca.set_roi(2, 15, channel=1)
        self.ctrl_hwobj.mca.set_presets(erange=1, ctime=ctime, fname=str(fname))

    def _doSpectrum(self, ctime, filename, wait=True):
        try:
            ctime = float(ctime)
        except (TypeError, ValueError):
            ctime = self.default_integration_time
        print(f"_doSpectrum ctime {ctime}")
        self.choose_attenuation(ctime, filename)

    def choose_attenuation(self, ctime=None, fname=None):
        """Choose appropriate maximum attenuation.
        Args:
            ctime (float): count time [s]
        Kwargs:
            fname (str): Filename to save the MCA data (full path)
        Returns:
            (bool): Procedure executed correcly (True) or error (False)
        """
        try:
            ctime = float(ctime)
        except (TypeError, ValueError):
            ctime = self.default_integration_time
        print(f"ctime {ctime}")

        res = True
        if not fname:
            fname = self.spectrumInfo["filename"]
        fname = str(fname)

        self.preset_mca(ctime, fname)

        self.ctrl_hwobj.detcover.set_in(20)
        try:
            _transm = self.ctrl_hwobj.find_max_attenuation(
                ctime=ctime, fname=fname, roi=[2.0, 15.0]
            )
            self.spectrumInfo["beamTransmission"] = _transm
        except Exception as exp:
            logging.getLogger("user_level_log").exception(str(exp))
            res = False

        self.ctrl_hwobj.diffractometer.fldet_out()
        return res

    def _findAttenuation(self, ctime=None):
        try:
            ctime = float(ctime)
        except (TypeError, ValueError):
            ctime = self.default_integration_time
        return self.choose_attenuation(ctime)

    """
    Next methods are for fitting the data with pymca
    """

    def mcafit_configuration(self, config=None):
        """Configure the fitting parameters. The procedure is time consuming.
           It is only executed if the last configuration file is not the same.
        Args:
            config(dict): Configuration dictionary, containing among others the
                          configuration file name.
        """
        change = False
        if not config or "file" not in config:
            fname = XRFSpectrum._get_cfgfile(self, self.spectrumInfo["energy"])
        else:
            fname = config["file"]

        if self.fname != fname:
            self.fname = fname
            change = True
        self.config.read(self.fname)
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

    def set_data(self, data, calib=None, config=None):
        """Execute the fitting. Write the fitted data files to pyarch.
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

            # xmin and xmax hard coded while waiting for configuration file
            # to be corrected.
            # xmin = 292
            # xmax = 4000

            xmin = int(config["min"])
            xmax = int(config["max"])
            self.mcafit.setData(xdata, ydata, xmin=xmin, xmax=xmax, calibration=calib)

            self.mcafit.estimate()
            # fitresult  = self._fit()

            fitresult = self.mcafit.startfit(digest=1)
            if fitresult:
                fitresult = {"fitresult": fitresult[0], "result": fitresult[1]}

                # write the csv file to pyarch
                csvname = self.spectrumInfo["fittedDataFileFullPath"]
                self._write_csv_file(fitresult, csvname)

                # write html report to pyarch
                fname = os.path.basename(self.spectrumInfo["filename"])
                outfile = fname.split(".")[0]
                outdir = os.path.dirname(self.spectrumInfo["annotatedPymcaXfeSpectrum"])

                _kw = {
                    "outdir": outdir,
                    "outfile": outfile,
                    "fitresult": fitresult,
                    "plotdict": {"logy": False},
                }

                report = QtMcaAdvancedFitReport.QtMcaAdvancedFitReport(**_kw)
                text = report.getText()
                report.writeReport(text=text)
        except Exception as exp:
            logging.getLogger().exception("XRFSpectrum: problem fitting %s" % str(exp))
            raise

    def _write_csv_file(self, fitresult, fname=None):
        """Write data to a csv file.
        Args:
            fitresult(dict): Data as dictionary.
        Kwargs:
            fname (str): Filename to write to (full path).
        """
        if not fname:
            fname = self.spectrumInfo["fittedDataFileFullPath"]
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
        header = '"channel"%s"Energy"%s"counts"%s"fit"%s"continuum"%s"pileup"' % (
            delimiter,
            delimiter,
            delimiter,
            delimiter,
            delimiter,
        )

        # add the peaks labels
        for key in peaks_dict:
            header += delimiter + ('"%s"' % key)
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
                    csv_fd.write("%s%.7g" % (delimiter, peaks_dict[key][i]))

                csv_fd.write("\n")
