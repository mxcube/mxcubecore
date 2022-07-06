#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages
from pathlib import Path


def get_version(fname):
    with open(fname) as f:
        content = f.readlines()

    ver = content[0].split("=")[-1].replace('"', "").replace(" ", "").strip()

    return ver


def get_requirements(fname):
    with open(fname) as f:
        content = f.readlines()

    requirements = [x.strip() for x in content]
    requirements = [x for x in requirements if not x.startswith('#')]

    return requirements

requirements = get_requirements(
    os.path.join(Path(os.path.abspath(__file__)).parent.as_posix(), "requirements.txt")
)
setup_requirements = []
tests_requirements = []
extras_requirements = {'gphl': ['f90nml', 'py4j']}
console_scripts = []
gui_scripts = []

entry_points = {
    'console_scripts': console_scripts,
    'gui_scripts': gui_scripts
}

version = get_version(
    os.path.join(Path(os.path.abspath(__file__)).parent.as_posix(), "mxcubecore/__version__.py")
)

setup(
    name='mxcubecore',
    version=version,
    author='The MXCuBE collaboration',
    author_email='mxcube@esrf.fr',
    description='MXCuBE core library',
    long_description='Core libraries for the MXCuBE application',
    url='http://github.com/mxcube/mxcubecore',
    packages=find_packages(),
    package_dir={},
    include_package_data=True,
    package_data={'mxcubecore': ['configuration/mockup/*'],
                  },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Lesser General Public License v3 (LGPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
    ],
    platforms='all',
    license='LGPL',
    entry_points=entry_points,
    install_requires=requirements,
    setup_requires=setup_requirements,
    tests_require=tests_requirements,
    extras_require=extras_requirements,
    python_requires='>=3.6',
)
