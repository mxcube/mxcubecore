[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Test and build](https://github.com/mxcube/mxcubecore/actions/workflows/tests.yml/badge.svg)](https://github.com/mxcube/mxcubecore/actions/workflows/tests.yml)
![PyPI](https://img.shields.io/pypi/v/mxcubecore)

# Backend of MXCuBE
mxcubecore is the back-end level of [MXCuBE Qt](https://github.com/mxcube/mxcube/) and [MXCuBE Web](https://github.com/mxcube/mxcube3/)  allowing to access the beamline control system and instrumentation. It acts as a container of single python objects (called hardware objects).

Please read the [contributing guidlines](https://github.com/mxcube/mxcubecore/blob/master/CONTRIBUTING.md/) before submiting your code to the repository.


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

# Installation

Installation of the mxubecore module is commonly done as a depdency of either [MXCuBE Web](https://github.com/mxcube/mxcube3/) or [MXCuBE Qt](https://github.com/mxcube/mxcube/).

Standalone installation of the moudle can be done via poetry `poetry install` or for development purpouses (creating a symlink to the current folder) by using pip: `pip install -e .`. Don't forget the trailing "." (period).

mxcubecore depends on python-ldap that in turn depends on the openldap system library. It can be installed through conda by installing the openldap depdency: `conda install openldap` or on systems using apt-get: `sudo apt-get install -y libldap2-dev libsasl2-dev slapd ldap-utils tox lcov valgrind`. See [python-ldap](https://www.python-ldap.org/en/python-ldap-3.4.3/installing.html#debian) for more information.
