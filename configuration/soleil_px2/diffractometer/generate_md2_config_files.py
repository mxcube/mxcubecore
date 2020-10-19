#!/usr/bin/env python2
"""Generate configuration files for MD2 motors. Available options are "exporter", "tango_events", "tango_polling" """

from string import Template
import os

continuous_motors = {
    "AlignmentX": {"direction": "1", "GUIstep": "0.1"},
    "AlignmentY": {"direction": "1", "GUIstep": "0.1"},
    "AlignmentZ": {"direction": "1", "GUIstep": "0.1"},
    "CentringX": {"direction": "1", "GUIstep": "0.05"},
    "CentringY": {"direction": "1", "GUIstep": "0.05"},
    "CentringTableVertical": {"direction": "1", "GUIstep": "0.05"},
    "CentringTableFocus": {"direction": "1", "GUIstep": "0.05"},
    "Omega": {"direction": "-1", "GUIstep": "45"},
    "Kappa": {"direction": "1", "GUIstep": "10"},
    "Phi": {"direction": "1", "GUIstep": "10"},
    "ApertureHorizontal": {"direction": "1", "GUIstep": "0.025"},
    "ApertureVertical": {"direction": "1", "GUIstep": "0.025"},
    "CapillaryHorizontal": {"direction": "1", "GUIstep": "0.05"},
    "CapillaryVertical": {"direction": "1", "GUIstep": "0.05"},
    "ScintillatorVertical": {"direction": "1", "GUIstep": "0.1"},
    "ScintillatorHorizontal": {"direction": "1", "GUIstep": "0.1"},
    "BeamstopX": {"direction": "1", "GUIstep": "0.1"},
    "BeamstopY": {"direction": "1", "GUIstep": "0.1"},
    "BeamstopZ": {"direction": "1", "GUIstep": "0.1"},
    "Zoom": {"direction": "1", "GUIstep": "500"},
}

# combined motors
# backlight: MicrodiffLight
# frontlight: MicrodiffLight
# zoom: MicrodiffZoom
# phase: MicrodiffPhase
# aperture: MicrodiffAperture
# capillary: MicrodiffCapillary
# scintillator: MicrodiffScintillator

light_motors = {
    "BacklightLevel": {"direction": "1"},
    "FrontlightLevel": {"direction": "1"},
    "BackLightFactor": {"direction": "1"},
    "FrontLightFactor": {"direction": "1"},
    "BacklightIsOn": {"positions": [True, False]},
    "FrontlightIsOn": {"positions": [True, False]},
}

organ_devices = ["Aperture", "Capillary", "Scintillator"]

discrete_motors = {
    "CoaxialCameraZoomValue": {"positions": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]},
    "CurrentPhase": {
        "positions": [
            "DataCollection",
            "BeamLocation",
            "Centring",
            "Transfer",
            "Unknown",
        ],
        "command": "startSetPhase",
    },
    "CurrentPhaseIndex": {"positions": [3, 2, 1, 4, 5]},
    "AperturePosition": {"positions": ["BEAM", "OFF", "PARK", "UNKNOWN"]},
    "CurrentApertureDiamgeterIndex": {"positions": [0, 1, 2, 3, 4, 5]},
    "CapillaryPosition": {"positions": ["BEAM", "OFF", "PARK", "UNKNOWN"]},
    "ScintillatorPosition": {
        "positions": ["SCINTILLATOR", "PHOTODIODE", "PARK", "UNKNOWN"]
    },
    "FastShutterIsOpen": {"positions": [True, False]},
    "CryoIsOut": {"positions": [True, False]},
    "FluoDetectorIsBack": {"positions": [True, False]},
}


def get_template(mode="exporter"):
    if mode == "exporter":
        template = open("exporter_template.txt").read()
    elif mode == "tango_events":
        template = open("tango_events_template.txt").read()
    elif mode == "tango_polling":
        template = open("tango_polling_template.txt").read()
    return Template(template)


def main():
    import optparse

    parser = optparse.OptionParser()

    parser.add_option(
        "-m",
        "--mode",
        default="exporter",
        type=str,
        help="Specify communication mode (default=%default)",
    )
    parser.add_option(
        "-e",
        "--exporter_address",
        default="172.19.10.119:9001",
        type=str,
        help="Exporter address",
    )
    parser.add_option(
        "-t", "--tangoname", default="i11-ma-cx1/ex/md2", type=str, help="Tango name"
    )
    parser.add_option(
        "-p",
        "--polling_interval",
        default=1000,
        type=float,
        help="Tango polling interval",
    )

    options, args = parser.parse_args()

    template = get_template(mode=options.mode)
    if options.mode == "exporter":
        config_dictionary = {
            "class": "MicrodiffMotor",
            "exporter_address": options.exporter_address,
        }
    elif options.mode == "tango_polling":
        config_dictionary = {
            "class": "MicrodiffMotor",
            "tangoname": options.tangoname,
            "polling_interval": options.polling_interval,
        }
    elif options.mode == "tango_events":
        config_dictionary = {"class": "MicrodiffMotor", "tangoname": options.tangoname}

    if not os.path.isdir(options.mode):
        os.mkdir(options.mode)

    for motor in continuous_motors:
        config_dictionary["actuator_name"] = motor
        config_dictionary["direction"] = continuous_motors[motor]["direction"]
        config_dictionary["GUIstep"] = continuous_motors[motor]["GUIstep"]
        config = template.substitute(config_dictionary)
        f = open("%s/%s.xml" % (options.mode, motor.lower()), "w")
        f.write(config)
        f.close()


if __name__ == "__main__":
    main()
