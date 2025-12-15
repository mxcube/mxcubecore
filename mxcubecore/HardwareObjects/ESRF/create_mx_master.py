from datetime import datetime
from silx.io.dictdump import dicttonx

try:
    from HardwareRepository import HardwareRepository as HWR
except ModuleNotFoundError:
    pass


class CreateH5Master:
    """Class to create HDF5 master file for dectris filewriter"""

    def __init__(self):
        self.file_template = None
        self._metadata = {}
        self.detector = {}
        self.detector_specific = {}
        self.beam = {}
        self.sample = {}
        self.sample_goniometer = {}
        self.sample_transformations = {}
        self.geometry = {}
        self.data = {}
        self.entry = {}
        self._pixel_size = ()
        self.read_only = None

    def init(self):
        """Initialise the static data, from the detector config"""
        # self._pixel_size = HWR.beamline.detector.get_pixel_size()
        self._pixel_size = (0.075, 0.075)
        self._metadata["description"] = "EIGER2 Si 9M".encode()
        self._metadata["detector_number"] = "E-18-0133, ESRF ID23".encode()
        self._metadata["sensor_material"] = "Si".encode()
        self._metadata["sensor_thickness"] = 0.00045
        self._metadata["detector_readout_time"] = 1e-7
        self.read_only = True
        # self._metadata["width"] = HWR.beamline.detector.get_width()
        # self._metadata["height"] = HWR.beamline.detector.get_height()
        self._metadata["width"] = 3108
        self._metadata["height"] = 3262

    def dynamic_values(self, start, osc_range, exptime, number_of_images):
        """Update the data structure with the specific data collection values
        Args:
            start (float): Oscillation start
            osc_range (float): Range for 1 image
            exptime (float): Exposure time for 1 image
            number_of_images (int): Number of images.
        """
        # beam_x, beam_y = HWR.beamline.detector.get_beam_position()
        beam_x = 1712.77
        beam_y = 2034.59
        # distance = HWR.beamline.detector.distance.get_value()/ 1000.0
        distance = 0.14104
        # data_collection_date = datetime.now().astimezone().isoformat()
        # 2023-02-23T16:33:53.537684+01:00
        self.detector.update(
            {
                "beam_center_x": beam_x,
                "beam_center_y": beam_y,
                "count_time": exptime,
                "frame_time": exptime + self._metadata["detector_readout_time"],
                "distance": distance,
                "nimages": number_of_images,
            }
        )
        if not self.read_only:
            self.detector_specific.update(
                {
                    "photon_energy": HWR.beamline.energy.get_value() * 1000,
                    "data_collection_date": datetime.now().astimezone().isoformat(),
                    "nimages": number_of_images,
                }
            )
            # self.beam["incident_wavelength"] = HWR.beamline.energy.get_wavelength()
            self.beam["incident_wavelength"] = 0.873128

        self.geometry.update(
            {
                "translation": {
                    "distances": [0.126571944, 0.152385525, -distance],
                }
            },
        )

        omega = []
        omega_end = []
        for img in range(number_of_images):
            omega.append(start + img * osc_range)
            omega_end.append(start + (img + 1) * osc_range)
        osc_range_total = number_of_images * osc_range
        self.sample_goniometer.update(
            {
                "omega": omega,
                "omega_end": omega_end,
                "omega_range_average": osc_range,
                "omega_range_total": osc_range_total,
            }
        )

        self.sample_transformations.update(
            {
                "omega": omega,
                "omega_end": omega_end,
                "omega_range_average": osc_range,
                "omega_range_total": osc_range_total,
                "translation": [0] * number_of_images,
            }
        )

        nfiles = int(number_of_images / 100)
        n_images_left = number_of_images % 100
        if n_images_left:
            nfiles += 1
        fname = "mesh-M_collect_test_0_1_"
        for i in range(1, nfiles + 1):
            self.data[f">data_{i:06d}"] = f"{fname}data_{i:06d}.h5::/entry/data/data"
        self.data["@signal"] = f"data_{i:06d}"

    def static_values(self):
        """Prepare the data structure, to be done at the begining of
        the datam collection
        """
        self.detector_specific = {
            "@NX_class": "NXcollection",
            "frame_count_time@units": "s",
            "frame_period@units": "s",
            "photon_energy@units": "eV",
            ## "compression": self.get_channel_object("compression_type").get_value(),
            "compression": "bslz4",
            "trigget_mode": "exts",
            "x_pixels_in_detector": self._metadata["width"],
            "y_pixels_in_detector": self._metadata["height"],
        }

        if self.read_only:
            self.detector_specific.update({"photon_energy": 14200})

        self.geometry = {
            "@NX_class": "NXgeometry",
            "orientation": {
                "@NX_class": "NXorientation",
                "value": [-1, 0, 0, 0, -1, 0],
            },
            "translation": {
                "@NX_class": "NXtranslation",
                "distances@units": "m",
            },
        }

        self.beam = {
            "@NX_class": "NXbeam",
            "incident_wavelength@units": "angstrom",
        }

        if self.read_only:
            ## self.detector_specific["photon_energy"] = HWR.beamline.energy.get_value()
            ## self.beam["incident_wavelength"] = HWR.beamline.energy.get_wavelength()
            self.detector_specific["photon_energy"] = 14200
            self.beam["incident_wavelength"] = 0.8731281579802835

        self.module = {
            "@NX_class": "NXdetector_module",
            "data_size": [self._metadata["width"], self._metadata["height"]],
            "fast_pixel_direction@depends_on": "/entry/instrument/detector/transformations/translation",
            "fast_pixel_direction@units": "m",
            "fast_pixel_direction": self._pixel_size[0] / 10000.0,
            "slow_pixel_direction@depends_on": "/entry/instrument/detector/transformations/translation",
            "slow_pixel_direction@units": "m",
            "slow_pixel_direction": self._pixel_size[0] / 10000.0,
        }
        self.detector = {
            "@NX_class": "NXdetector",
            "beam_center_x@units": "pixel",
            "beam_center_y@units": "pixel",
            "count_time@units": "s",
            "detector_readout_time@units": "s",
            "distance@units": "m",
            "frame_time@units": "s",
            "sensor_thickness@units": "m",
            "threshold_energy@units": "eV",
            "x_pixel_size": self._pixel_size[0] / 1000.0,
            "x_pixel_size@units": "m",
            "y_pixel_size": self._pixel_size[1] / 1000.0,
            "y_pixel_size@units": "m",
            "description": self._metadata["description"],
            "detector_number": self._metadata["detector_number"],
            "detector_readout_time": self._metadata["detector_readout_time"],
            "bit_depth_image": 32,
            "bit_depth_readout": 16,
            "countrate_correction_applied": 1,
            "sensor_material": self._metadata["sensor_material"],
            "sensor_thickness": self._metadata["sensor_thickness"],
            "threshold_energy": self.detector_specific["photon_energy"],
            "type": "HPC",
            "virtual_pixel_correction_applied": 1,
            "detectorSpecific": self.detector_specific,
            "geometry": self.geometry,
            "goniometer": {"@NX_class": "NXtransformations"},
            "module": self.module,
        }

        self.sample_goniometer = {
            "@NX_class": "NXtransformations",
            "omega@units": "degree",
            "omega_end@units": "degree",
            "omega_range_average@units": "degree",
            "omega_range_total@units": "degree",
        }

        self.sample_transformations = {
            "@NX_class": "NXtransformations",
            "omega@depends_on": "/entry/sample/transformations/translation",
            "omega@transformation_type": "rotation",
            "omega@units": "degree",
            "omega@offset": [0.0, 0.0, 0.0],
            "omega@vector": [-1.0, 0.0, 0.0],
            "omega_end@units": "degree",
            "omega_range_average@units": "degree",
            "omega_range_total@units": "degree",
            "translation@transformation_type": "translation",
            "translation@units": "m",
            "translation@depends_on": ".",
            "translation@offset": [0.0, 0.0, 0.0],
            "translation@vector": [0.0, 0.0, 0.0],
        }

        self.sample = {
            "@NX_class": "NXsample",
            "depends_on": "/entry/sample/transformations/omega",
            "beam": self.beam,
            "goniometer": self.sample_goniometer,
            "transformations": self.sample_transformations,
        }

        self.data = {"@NX_class": "NXdata"}

        self.entry = {
            "@default": "entry",
            "entry": {
                "@NX_class": "NXentry",
                "@default": "data",
                "data": self.data,
                "definition": "NXmx".encode(),
                "definition@version": "1.4",
                "instrument": {
                    "@NX_class": "NXinstrument",
                    "beam": self.beam,
                    "detector": self.detector,
                },
                "sample": self.sample,
            },
        }

    def write_master_file(self, fdir=None, fname=None):
        """Write the master file.
        Args:
            fdir (str): Directory to write te file.
            fname (str): file name.
        """
        fdir = fdir or "/home/esrf/beteva/hdf5_dectris.git/data"
        fname = fname or "ref-insu-insu_2_1_"
        nfiles = 1

        for i in range(1, nfiles + 1):
            self.data[f">data_{i:06d}"] = f"{fname}data_{i:06d}.h5::/entry/data/data"
        self.data["@signal"] = f"data_{i:06d}"
        dicttonx(self.entry, f"{fdir}/{fname}master_new.h5", mode="w")
