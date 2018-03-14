import logging
import numpy
import os.path

from XRFSpectrum import *

try:
    from PyMca import ConfigDict
    from PyMca import ClassMcaTheory
except ImportError:
    from PyMca5.PyMca import ConfigDict
    from PyMca5.PyMca import ClassMcaTheory


class ID29XRFSpectrum(XRFSpectrum):
    def __init__(self, *args, **kwargs):
        XRFSpectrum.__init__(self, *args, **kwargs)
        self.mca_hwobj = self.getObjectByRole('mca')
        self.ctrl_hwobj = self.getObjectByRole('controller')
        self.fname = "/users/blissadm/local/beamline_configuration/misc/9keV.cfg"
        self.config = ConfigDict.ConfigDict()
        self.mcafit = ClassMcaTheory.McaTheory(self.fname)

    def preset_mca(self, ctime, fname=None):
        self.mca_hwobj.set_roi(2, 15, channel=1)
        self.mca_hwobj.set_presets(erange=1, ctime=ctime, fname=fname)

    def choose_attenuation(self, ctime, fname=None):
        res = True
        if not fname:
            # fname = self.spectrumInfo['filename'].replace('.dat', '.raw')
            fname = self.spectrumInfo['filename']

        self.preset_mca(ctime, fname)

        self.ctrl_hwobj.detcover.set_in()
        try:
            tt = self.ctrl_hwobj.find_max_attenuation(ctime=ctime,
                                                      fname=fname,
                                                      roi=[2., 15.])
            self.spectrumInfo["beamTransmission"] = tt
        except Exception as e:
            logging.getLogger('user_level_log').exception(str(e))
            res = False

        return res

    def _findAttenuation(self, ct):
        return self.choose_attenuation(ct)

    """
    Next methods are for fitting the data with pymca
    """
    """
    The configuration is time consuming. It is only executed if the last
    configuration file is not the same.
    """
    def mcafit_configuration(self, config={}):
        change = False
        if 'file' not in config:
            fname = XRFSpectrum._get_cfgfile(self, self.spectrumInfo["energy"])
        else:
            fname = config['file']

        if self.fname != fname:
            self.fname = fname
            change = True

        self.config.read(self.fname)

        if 'concentrations' not in self.config:
            self.config['concentrations'] = {}
            change = True
        if 'attenuators' not in self.config:
            self.config['attenuators'] = {'Matrix':
                                          [1, 'Water', 1.0, 0.01, 45.0, 45.0]}
            change = True
        if 'flux' in config:
            self.config['concentrations']['flux'] = float(config['flux'])
            change = True
        if 'time' in config:
            self.config['concentrations']['time'] = float(config['time'])
            change = True

        if change:
            self.mcafit.configure(self.config)

    def set_data(self, data, calib=None, config={}):
        if config:
            self.mcafit_configuration(config)
        try:
            if data[0].size == 2:
                x = numpy.array(data[:, 0]) * 1.0
                y = numpy.array(data[:, 1])
            else:
                x = data[0] * 1.0
                y = data[1]

            xmin = float(config["min"])
            xmax = float(config["max"])

            # calib = numpy.ravel(calib).tolist()
            self.mcafit.setData(x, y, xmin=xmin, xmax=xmax)

            self.mcafit.estimate()
            # fitresult  = self._fit()

            fitresult = self.mcafit.startfit(digest=1)
            if fitresult:
                fitresult = {'fitresult': fitresult[0], 'result': fitresult[1]}

                # write the csv file to pyarch
                csvname = self.spectrumInfo['fittedDataFileFullPath']
                self._write_csv_file(fitresult, csvname)

                # write html report to pyarch
                outfile = self.spectrumInfo['filename']
                outdir = os.path.dirname(self.spectrumInfo['annotatedPymcaXfeSpectrum'])

                kw = {'outdir': outdir, 'outfile': outfile,
                      'fitresult': fitresult, 'plotdict': {'logy': False}}
                report = QtMcaAdvancedFitReport.QtMcaAdvancedFitReport(**kw)
                text = report.getText()
                report.writeReport(text=text)
        except:
            logging.getLogger().exception('XRFSpectrum: problem fitting %s %s %s' % (str(data), str(calib), str(config)))
            raise

    def _write_csv_file(self, fitresult, fname=None):
        if not fname:
            fname = self.spectrumInfo['fittedDataFileFullPath']
        if os.path.exists(fname):
            os.remove(fname)
        delimiter = ","
        header = '"channel"%s"Energy"%s"counts"%s"fit"%s"continuum"%s"pileup"' % (delimiter, delimiter, delimiter, delimiter, delimiter)
        with open(fname, 'w') as csv_fd:
            csv_fd.write(header)
            csv_fd.write("\n")
            for i in range(fitresult['result']['xdata'].size):
                csv_fd.write("%.7g%s%.7g%s%.7g%s%.7g%s%.7g%s%.7g" %
                             (fitresult['result']['xdata'][i],
                              delimiter,
                              fitresult['result']['energy'][i],
                              delimiter,
                              fitresult['result']['ydata'][i],
                              delimiter,
                              fitresult['result']['yfit'][i],
                              delimiter,
                              fitresult['result']['continuum'][i],
                              delimiter,
                              fitresult['result']['pileup'][i]))
                csv_fd.write("\n")
