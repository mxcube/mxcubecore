import abc
from mx3core.TaskUtils import task


class AbstractMCA(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.mca = None
        self.calib_cf = []

    @task
    def read_raw_data(self, chmin, chmax):
        """Read the raw data from chmin to chmax

        Keyword Args:
            chmin (int): channel number, defaults to 0
            chmax (int): channel number, defaults to 4095

        Returns:
            list. Raw data.
        """
        pass

    @task
    def read_roi_data(self):
        """Read the data for the predefined ROI

        Returns:
            list. Raw data for the predefined ROI channels.
        """
        pass

    @abc.abstractmethod
    @task
    def read_data(self, chmin, chmax, calib):
        """Read the data

        Keyword Args:
            chmin (float): channel number or energy [keV]
            chmax (float): channel number or energy [keV]
            calib (bool): use calibration, defaults to False

        Returns:
            numpy.array. x - channels or energy (if calib=True), y - data.
        """
        pass

    @task
    def set_calibration(self, fname=None, calib_cf=[0, 1, 0]):
        """Set the energy calibration. Give a filename or a list of calibration factors.

        Kwargs:
            fname (str): optional filename with the calibration factors
            calib_cf (list): optional list of calibration factors

        Returns:
            list. Calibration factors.

        Raises:
            IOError, ValueError
        """
        pass

    @abc.abstractmethod
    @task
    def get_calibration(self):
        """Get the calibration factors list

        Returns:
            list. Calibration factors.
        """
        pass

    @task
    def set_roi(self, emin, emax, **kwargs):
        """Configure a ROI

        Args:
            emin (float): energy [keV] or channel number
            emax (float): energy [keV] or channel number

        Keyword Args:
            element (str): element name as in periodic table
            atomic_nb (int): element atomic number
            channel (int): output connector channel number (1-8)

        Returns:
            None

        Raises:
            KeyError
        """
        pass

    @abc.abstractmethod
    @task
    def get_roi(self, **kwargs):
        """Get ROI settings

        Keyword Args:
            channel (int): output connector channel number (1-8)

        Returns:
            dict. ROI dictionary.
        """
        pass

    @task
    def clear_roi(self, **kwargs):
        """Clear ROI settings

         Keyword Args:
            channel (int): optional output connector channel number (1-8)

         Returns:
            None
        """
        pass

    @task
    def get_times(self):
        """Return a dictionary with the preset and elapsed real time [s],
        elapsed live time (if possible) [s] and the dead time [%].

        Returns:
            dict. Times dictionary.

        Raises:
            RuntimeError
        """
        pass

    @task
    def get_presets(self, **kwargs):
        """Get the preset parameters

        Keyword Args:
            ctime (float): Real time
            erange (int): energy range
            fname (str): filename where the data are stored
            ...

        Returns:
            dict.

        Raises:
            RuntimeError
        """
        pass

    @task
    def set_presets(self, **kwargs):
        """Set presets parameters

        Keyword Args:
           ctime (float): real time [s]
           erange (int): the energy range
           fname (str): file name (full path) to save the raw data

        Returns:
           None
        """
        pass

    @abc.abstractmethod
    @task
    def start_acq(self, cnt_time=None):
        """Start new acquisition. If cnt_time is not specified, counts for preset real time.

        Keyword Args:
            cnt_time (float, optional): count time [s]; 0 means to count indefinitely.

        Returns:
            None
        """
        pass

    @abc.abstractmethod
    @task
    def stop_acq(self):
        """Stop the running acquisition"""
        pass

    @task
    def clear_spectrum(self):
        """Clear the acquired spectrum"""
        pass
