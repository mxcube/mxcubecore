#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages

requirements = ['setuptools']

setup_requirements = []

TESTING = any(x in sys.argv for x in ['test', 'pytest'])
if TESTING:
    setup_requirements += ['pytest-runner']

tests_requirements = ['pytest', 'pytest-cov']

extras_requirements = {}

console_scripts = []

entry_points = { 'console_scripts': console_scripts }


setup(
    name='mxcubecore',
    # The version is updated with bumpversion
    version='0.0.0',
    #author='',
    #author_email='',
    description='MXCuBE core, beamline control and insrumentation',
    long_description='MXCuBE core, beamline control and insrumentation',
    url='core, beamline control and insrumentation',
    packages=find_packages(),
    package_dir={},
    include_package_data=True,
    package_data={'configuration': ['configuration/mockup/*.xml',
                                    'configuration/mockup/*.jpg',
                                    'configuration/mockup/qt/*.xml',
                                    'configuration/mockup/qt/*.yml']
                  },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
    ],
    platforms='all',
    license='GPL-3.0+',
    entry_points=entry_points,
    install_requires=requirements,
    setup_requires=setup_requirements,
    tests_require=tests_requirements,
    extras_require=extras_requirements,
    python_requires='>=2.7',
   )
