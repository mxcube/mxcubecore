[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Test and build](https://github.com/mxcube/mxcubecore/actions/workflows/tests.yml/badge.svg)](https://github.com/mxcube/mxcubecore/actions/workflows/tests.yml)
![PyPI](https://img.shields.io/pypi/v/mxcubecore)


# Backend of MXCuBE

`mxcubecore` is the back-end library for
[MXCuBE Qt](https://github.com/mxcube/mxcubeqt/)
and [MXCuBE Web](https://github.com/mxcube/mxcubeweb/).
It allows access to the beamline control system and instrumentation.
It acts as a container of single Python objects (called "hardware objects").

Please read the
[contributing guidelines](https://mxcubecore.readthedocs.io/en/stable/dev/contributing.html)
before submitting your code to the repository.

## License

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


## Installation

Installation of the `mxcubecore` module is commonly done as a dependency of either
[MXCuBE Web](https://github.com/mxcube/mxcubeweb/)
or [MXCuBE Qt](https://github.com/mxcube/mxcubeqt/).

Standalone installation of the `mxcubecore` for development purposes can be done
via Poetry with `poetry install`
or via pip with `python -m pip install --editable .` (don't forget the trailing dot `.`).

`mxcubecore` depends on `python-ldap` that in turn depends on the `openldap` system library.
It can be installed in a conda environment: `conda install openldap`
or on systems using the apt package manager (Debian and derivatives, including Ubuntu):
`sudo apt-get install -y libldap2-dev libsasl2-dev`.
See [python-ldap](https://www.python-ldap.org/en/python-ldap-3.4.3/installing.html#debian)
for more information.

See [Developer documentation](https://mxcubecore.readthedocs.io/)
for more information on working with mxcubecore.
