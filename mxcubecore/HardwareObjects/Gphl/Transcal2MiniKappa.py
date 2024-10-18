#! /usr/bin/env python
# encoding: utf-8
#
"""
License:

This file is part of MXCuBE.

MXCuBE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MXCuBE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.
"""

import ast
import os
from xml.etree import ElementTree as ET

import f90nml
import numpy as np

__copyright__ = """ Copyright © 2016 -  2023 MXCuBE Collaboration."""
__license__ = "LGPLv3+"
__author__ = "rhfogh"
__date__ = "12/06/2023"

minikappa_xml_template = """<object class="MiniKappaCorrection">
   <kappa>
      <direction>%(kappa_axis)s</direction>
      <position>%(kappa_position)s</position>
   </kappa>
   <phi>
      <direction>%(phi_axis)s</direction>
      <position>%(phi_position)s</position>
   </phi>
</object>"""

transcal_nml_template = """&SDCP_INSTRUMENT_LIST
TRANS_CALIBRATION_NAME='transcal_p14'
TRANS_HOME= %s, %s, %s
TRANS_CROSS_SEC_OF_SOC=%s, %s, %s
/"""


def get_recen_data(transcal_file, instrumentation_file, diffractcal_file=None, **kwds):
    """Read recentring data from GPhL files

    Args:
        transcal_file: transcal.nml  input file
        instrumentation_file: instrumentation.nml input file
        diffractcal_file: diffrqctcal,.nl ioptional input file

    Returns: dict
    """
    result = {}

    if not (os.path.isfile(transcal_file) and os.path.isfile(instrumentation_file)):
        return None

    transcal_data = f90nml.read(transcal_file)["sdcp_instrument_list"]
    home_position = transcal_data["trans_home"]
    cross_sec_of_soc = transcal_data["trans_cross_sec_of_soc"]
    result["cross_sec_of_soc"] = cross_sec_of_soc
    result["home"] = home_position

    instrumentation_data = f90nml.read(instrumentation_file)["sdcp_instrument_list"]
    result["gonio_centring_axes"] = instrumentation_data["gonio_centring_axis_dirs"]
    result["gonio_centring_axis_names"] = instrumentation_data[
        "gonio_centring_axis_names"
    ]

    try:
        diffractcal_data = f90nml.read(diffractcal_file)["sdcp_instrument_list"]
    except:
        diffractcal_data = instrumentation_data

    ll0 = diffractcal_data["gonio_axis_dirs"]
    result["omega_axis"] = ll0[:3]
    result["kappa_axis"] = ll0[3:6]
    result["phi_axis"] = ll0[6:]
    #
    return result


def make_minikappa_data(
    home,
    cross_sec_of_soc,
    gonio_centring_axes,
    gonio_centring_axis_names,
    omega_axis,
    kappa_axis,
    phi_axis,
):
    """

    Args:
        home (list):
        cross_sec_of_soc (list):
        gonio_centring_axes (list):
        gonio_centring_axis_names (list):
        omega_axis (list):
        kappa_axis (list):
        phi_axis (list):

    Returns:

    """

    # NB GonioCentringAxes are with motor directions in rows in instrumentation.nml
    # In recen and transcal files, they are with motor axes in *columns*
    # The distinction is a transpose, equivalent to changing multiplication order
    transform = np.matrix(gonio_centring_axes)
    transform.shape = (3, 3)
    omega = np.array(omega_axis)
    trans_1 = np.array(gonio_centring_axes[:3])
    if abs(omega.dot(trans_1)) < 0.99:
        raise ValueError(
            "First trans axis %s is not parallel to omega axis %s"
            % (omega_axis, gonio_centring_axes[:3])
        )

    # Transform kappa_axis, phi_axis and cross_sec_of_soc to goniostat
    # coordinate system
    # Home is *already* in the goniostat coordinate system
    cross_sec_of_soc = np.dot(transform, np.array(cross_sec_of_soc)).tolist()[0]
    kappa_axis = np.dot(transform, np.array(kappa_axis)).tolist()[0]
    phi_axis = np.dot(transform, np.array(phi_axis)).tolist()[0]

    # Shuffle axes to sampx, sampy, phiy order
    indices = list(
        gonio_centring_axis_names.index(tag) for tag in ("sampx", "sampy", "phiy")
    )
    kappa_axis = list(kappa_axis[idx] for idx in indices)
    phi_axis = list(phi_axis[idx] for idx in indices)
    cross_sec_of_soc = np.array(list(cross_sec_of_soc[idx] for idx in indices))
    home = np.array(list(home[idx] for idx in indices))
    # NB the signs of CSOC are set to get consistency with Gleb values
    kappa_position = (home - cross_sec_of_soc).tolist()
    phi_position = (home + cross_sec_of_soc).tolist()
    #
    return {
        "kappa_axis": kappa_axis,
        "phi_axis": phi_axis,
        "kappa_position": kappa_position,
        "phi_position": phi_position,
    }


def make_home_data(centring_axes, axis_names, kappadir, kappapos, phidir, phipos):
    """Convert in the oppoosite direction *from* minikappa configuration *to* transcal

    Args:
        centring_axes list(float): Goniostat centring axis coordinates, concatenated
        axis_names list(str): centring axis names, in instumentation.nml order
        kappadir: list(float): kappa axis direction, centring axis system
        kappapos list(float): kappa axis offset vector, centring axis system
        phidir list(float):  phi axis direction, centring axis system
        phipos list(float):  phi axis offset vector, centring axis system

    Returns:

    """
    # Get home and CSOC in goniostat (centring motor) coordinate system
    kappadir = np.array(kappadir)
    kappapos = np.array(kappapos)
    phidir = np.array(phidir)
    phipos = np.array(phipos)
    aval = kappadir.dot(phidir)
    bvec = phipos - kappapos
    kappahome = kappapos + (aval * bvec.dot(phidir) - bvec.dot(kappadir)) * kappadir / (
        aval * aval - 1
    )
    phihome = phipos - (aval * bvec.dot(kappadir) - bvec.dot(phidir)) * phidir / (
        aval * aval - 1
    )
    home_position = 0.5 * (kappahome + phihome)
    # # (http://confluence.globalphasing.com/display/SDCP/EMBL+MiniKappaCorrection)
    cross_sec_of_soc = 0.5 * (phihome - kappahome)

    # Reshuffle home and cross_sec_of_soc to lab vector order
    goniostat_order = ("sampx", "sampy", "phiy")
    indices = list(goniostat_order.index(tag) for tag in axis_names)
    home_position = list(home_position[ind] for ind in indices)
    cross_sec_of_soc = list(cross_sec_of_soc[ind] for ind in indices)

    # Transform cross_sec_of_soc to lab coordinate system
    transform = np.matrix(centring_axes)
    transform.shape = (3, 3)
    cross_sec_of_soc = np.dot(np.array(cross_sec_of_soc), transform).tolist()[0]
    return home_position, cross_sec_of_soc


def convert_to_gphl(instrumentation_file, minikappa_config, **kwds):

    if not os.path.isfile(instrumentation_file):
        raise ValueError("Instrumentation file not found: %s" % instrumentation_file)
    if not os.path.isfile(minikappa_config):
        raise ValueError("Minikappa config file not found: %s" % minikappa_config)

    instrumentation_data = f90nml.read(instrumentation_file)["sdcp_instrument_list"]
    centring_axes = instrumentation_data["gonio_centring_axis_dirs"]
    axis_names = instrumentation_data["gonio_centring_axis_names"]
    kappadir, kappapos, phidir, phipos = get_minikappa_data(minikappa_config)

    home_position, cross_sec_of_soc = make_home_data(
        centring_axes, axis_names, kappadir, kappapos, phidir, phipos
    )
    return home_position, cross_sec_of_soc


def get_minikappa_data(configfile):
    root = ET.fromstring(open(configfile).read())
    result = []
    for tag in ("kappa", "phi"):
        elem = root.find(tag)
        for field in ("direction", "position"):
            result.append(ast.literal_eval(elem.findtext(field)))
    return result


if __name__ == "__main__":

    from argparse import (
        ArgumentParser,
        RawTextHelpFormatter,
    )

    parser = ArgumentParser(
        prog="Transcal2MiniKappa.py",
        formatter_class=RawTextHelpFormatter,
        prefix_chars="--",
        description="""
Conversion between GPhL recentring data and MiniKappaCorrection recentring data

The source option ('gphl' or 'minikappa') determines the direction of conversion.
The default source is 'minikappa'

Starting from GPhL you need an up-to-date transcal.nml file, a matching
instrumentation.nml file, and preferably an up-to-date diffractcal.nml file.

Starting from the minikappa correction you need an instrumentation.nml file and
a minikappa-correction-xml file
        """,
    )

    default = "minikappa"
    parser.add_argument(
        "--source",
        choices=["minikappa", "gphl"],
        default=default,
        help="Type of input data to convert.\n",
    )

    parser.add_argument(
        "--instrumentation_file",
        metavar="instrumentation_file",
        help="instrumentation.nml file\n",
        required=True,
    )

    parser.add_argument(
        "--transcal_file", metavar="transcal_file", help="transcal.nml file\n"
    )

    parser.add_argument(
        "--diffractcal_file", metavar="diffractcal_file", help="diffractcal.nml file\n"
    )

    parser.add_argument(
        "--minikappa_config",
        metavar="minikappa_config",
        help="minikappa-correction.xmll file\n",
    )

    argsobj = parser.parse_args()
    options_dict = vars(argsobj)
    source = options_dict.pop("source", "minikappa")
    if source == "gphl":
        recen_data = get_recen_data(**options_dict)
        minikappa_data = make_minikappa_data(**recen_data)
        print(minikappa_xml_template % minikappa_data)
    else:
        home, csoc = convert_to_gphl(**options_dict)
        print(transcal_nml_template % tuple(home + csoc))
