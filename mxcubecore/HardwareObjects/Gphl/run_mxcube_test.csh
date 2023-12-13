#!/bin/csh

# Script for running MXCuBE Qt in mock mode for GPhL workflows

# Requires HOME, BASE_PATH, and MINICONDA envs to be set
# BASE_PATH is (for rhfogh): /usr/local/bin:/usr/bin:/bin:/usr/bin/X11
# MINICONDA is the directory containing the minoconda envs/ directory
# NB you do *not* need to activate teh conda environment before running

setenv GPHL_TEST_INPUT $1

# Parameters to edit for setup:
# Directory containing mxcubeqt and mxcubecore
set MXCUBE_ROOT="${HOME}/pycharm"
# Name of conda environment to use
set CONDA_ENV="mxcubeqt5"
# Beamline-specific configuration directory. Keep to default
set BL_CONFIG="embl_hh_p14"

setenv PYTHONPATH "${MXCUBE_ROOT}/mxcubeqt:${MXCUBE_ROOT}/mxcubecore"
setenv PATH "${MINICONDA}/envs/${CONDA_ENV}/bin:${BASE_PATH}"

set CONFIG_PATH="${MXCUBE_ROOT}/mxcubecore/mxcubecore/configuration"
set MXCUBE_CORE_CONFIG_PATH="${CONFIG_PATH}/mockup/gphl:${CONFIG_PATH}/mockup/qt:${CONFIG_PATH}/mockup"
# Variable locations
set MXCUBE_CORE_CONFIG_PATH="${MXCUBE_CORE_CONFIG_PATH}:${CONFIG_PATH}/$BL_CONFIG"

printenv PATH
printenv PYTHONPATH
which python

# run command
python ${MXCUBE_ROOT}/mxcubeqt/mxcubeqt/__main__.py --pyqt5 --mockupMode \
 --coreConfigPath "${MXCUBE_CORE_CONFIG_PATH}"
