#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.
#
#
# Job submission to the ALBA cluster is managed by the slurm_client
#  The USER / SCRATCH keyword sets if the files are copied first to local disk on the cluster (SCRATCH)
#    or if the file I/O during the characterization job is done directly on the directorires of the user (USER)
#


"""
[Name] XalocCluster

[Description]
HwObj providing access to the ALBA cluster.

[Signals]
- None
"""

from __future__ import print_function

import os
import time
import logging

from mxcubecore.BaseHardwareObjects import HardwareObject
from slurm_client import EDNAJob, Manager, Account
from slurm_client.utils import create_edna_yml


__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"
__author__ = "Jordi Andreu"


class XalocCluster(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.logger = logging.getLogger("HWR.XalocCluster")
        self.account = None
        self.manager = None
        self.use_env_scripts_root = True
        self._scripts_root = None
        self.pipelines = {}
        self._jobs = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        user = self.get_property("user")
        cla = self.get_property("cla")

        self._scripts_root = self.get_property("pipelines_scripts_root")

        if self._scripts_root:
            self.use_env_scripts_root = False

        for name in ['strategy', 'ednaproc', 'autoproc', 'xia2']:
            if self.get_property("{}_pipeline".format(name)):
                _pipeline = eval(self.get_property("{}_pipeline".format(name)))
                if _pipeline:
                    self.pipelines[name] = _pipeline
                    self.logger.debug("Adding {0} pipeline {1}".format(name, _pipeline))

        self.account = Account(user=user, cla=cla, scripts_root=self._scripts_root)
        self.manager = Manager([self.account])
        self.logger.debug("cluster user: {0}".format(self.account.user))
        self.logger.debug("cluster CLA: {0}".format(self.account.cla))
        try: self.logger.debug("scripts root: {0}".format( self.account.scripts_root ) )
        except: pass

    def run(self, job):
        self.manager.submit(job)

    def wait_done(self, job):
        state = self.manager.get_job_state(job)
        self.logger.debug("Job state is %s" % state)

        while state in ["RUNNING", "PENDING"]:
            self.logger.debug("Job / is %s" % state)
            time.sleep(0.5)
            state = self.manager.get_job_state(job)

        self.logger.debug(" job finished with state: \"%s\"" % state)
        return state

    def create_strategy_job(self, collect_id, input_file, output_dir):

        plugin_name = self.pipelines['strategy']['plugin']
        slurm_script = os.path.join(self._scripts_root,
                                    self.pipelines['strategy']['script'])

        _yml_file = create_edna_yml(str(collect_id),
                                    plugin_name,
                                    input_file,
                                    slurm_script,
                                    workarea='SCRATCH',
                                    benchmark=False,
                                    dest=output_dir,
                                    use_scripts_root=self.use_env_scripts_root,
                                    xds=None,
                                    configdef=None)
        return EDNAJob(_yml_file)

    def create_autoproc_job(self, collect_id, input_file, output_dir):

        plugin_name = self.pipelines['autoproc']['plugin']
        slurm_script = os.path.join(self._scripts_root,
                                    self.pipelines['autoproc']['script'])
        configdef = os.path.join(self._scripts_root,
                                 self.pipelines['autoproc']['configdef'])

        self.logger.debug("configDef is %s" % configdef)

        _yml_file = create_edna_yml(str(collect_id),
                                    plugin_name,
                                    input_file,
                                    slurm_script,
                                    workarea='SCRATCH',
                                    benchmark=False,
                                    dest=output_dir,
                                    use_scripts_root=self.use_env_scripts_root,
                                    xds=None,
                                    configdef=configdef)
        return EDNAJob(_yml_file)

    def create_xia2_job(self, collect_id, input_file, output_dir):

        plugin_name = self.pipelines['xia2']['plugin']
        slurm_script = os.path.join(self._scripts_root,
                                    self.pipelines['xia2']['script'])

        _yml_file = create_edna_yml(str(collect_id),
                                    plugin_name,
                                    input_file,
                                    slurm_script,
                                    workarea='SCRATCH',
                                    benchmark=False,
                                    dest=output_dir,
                                    use_scripts_root=self.use_env_scripts_root,
                                    xds=None,
                                    configdef=None)
        return EDNAJob(_yml_file)

    def create_ednaproc_job(self, collect_id, input_file, output_dir):

        plugin_name = self.pipelines['ednaproc']['plugin']
        slurm_script = os.path.join(self._scripts_root,
                                    self.pipelines['ednaproc']['script'])

        _yml_file = create_edna_yml(str(collect_id),
                                    plugin_name,
                                    input_file,
                                    slurm_script,
                                    workarea='SCRATCH',
                                    benchmark=False,
                                    dest=output_dir,
                                    use_scripts_root=self.use_env_scripts_root,
                                    xds=None,
                                    configdef=None)
        return EDNAJob(_yml_file)
