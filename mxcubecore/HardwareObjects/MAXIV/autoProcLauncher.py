#!/usr/bin/env python
# called this way
# autoPROCLauncher.py -path
# /data/staff/biomax/staff/jie/2015_11_10/processed -mode after
# -datacollectionID 13 -residues 200 -anomalous False -cell "0,0,0,0,0,0"

import logging
import os
import shlex
import string
import subprocess
import sys
import tempfile
import time
import urllib

import httplib

inputTemplate = """<?xml version="1.0"?>
<XSDataInputControlAutoPROC>
  <dataCollectionId>
    <value>{dataCollectionId}</value>
  </dataCollectionId>
  <doAnomAndNonanom>
    <value>{doAnomAndNonanom}</value>
  </doAnomAndNonanom>
  <processDirectory>
    <path>
      <value>{autoPROCPath}</value>
    </path>
  </processDirectory>
</XSDataInputControlAutoPROC>
"""

SCRIPT_TEMPLATE = """#!/usr/bin/env python

import os
import sys
import time
import socket
import traceback

sys.path.insert(0, "/mxn/groups/biomax/cmxsoft/edna-mx/kernel/src")

from EDVerbose import EDVerbose
from EDFactoryPluginStatic import EDFactoryPluginStatic

beamline = "$beamline"
proposal = "$proposal"
dataCollectionId = $dataCollectionId
autoPROCDirectory = "$autoPROCDirectory"
inputFile = "$inputFile"

pluginName = "EDPluginControlAutoPROCv1_0"
os.environ["EDNA_SITE"] = "MAXIV_BIOMAX"
os.environ["ISPyB_user"]=""
os.environ["ISPyB_pass"]=""

EDVerbose.screen("Executing EDNA plugin %s" % pluginName)
EDVerbose.screen("EDNA_SITE %s" % os.environ["EDNA_SITE"])

hostname = socket.gethostname()
dateString  = time.strftime("%Y%m%d", time.localtime(time.time()))
timeString = time.strftime("%H%M%S", time.localtime(time.time()))
#strPluginBaseDir = os.path.join("/tmp", beamline, dateString)
#if not os.path.exists(strPluginBaseDir):
#    os.makedirs(strPluginBaseDir, 0o755)

#baseName = "{0}_autoPROC".format(timeString)
#baseDir = os.path.join(strPluginBaseDir, baseName)
baseName = "{hostname}_{date}-{time}".format(hostname=hostname,
                                             date=dateString,
                                             time=timeString)
baseDir = os.path.join(autoPROCDirectory, baseName)
if not os.path.exists(baseDir):
    os.makedirs(baseDir, 0o755)
EDVerbose.screen("EDNA plugin working directory: %s" % baseDir)

#linkName = "{hostname}_{date}-{time}".format(hostname=hostname,
#                                             date=dateString,
#                                             time=timeString)
#os.symlink(baseDir, os.path.join(autoPROCDirectory, linkName))

ednaLogName = "autoPROC_{0}-{1}.log".format(dateString, timeString)
EDVerbose.setLogFileName(os.path.join(autoPROCDirectory, ednaLogName))
EDVerbose.setVerboseOn()

edPlugin = EDFactoryPluginStatic.loadPlugin(pluginName)
edPlugin.setDataInput(open(inputFile).read())
#edPlugin.setBaseDirectory(strPluginBaseDir)
edPlugin.setBaseDirectory(autoPROCDirectory)
edPlugin.setBaseName(baseName)

EDVerbose.screen("Start of execution of EDNA plugin %s" % pluginName)
os.chdir(baseDir)
edPlugin.executeSynchronous()

"""
# XDS.INP creation is now asynchronous in mxcube, so it may not be here yet
# when we're started
# WAIT_XDS_TIMEOUT = 10

HPC_HOST = "b-picard07-clu0-fe-0.maxiv.lu.se"


class AutoProcLauncher:
    def __init__(
        self,
        path,
        mode,
        datacollectionID,
        residues=200,
        anomalous=False,
        cell="0,0,0,0,0,0",
        spacegroup=None,
    ):
        self.autoprocessingPath = path
        self.mode = mode
        self.dataCollectionId = datacollectionID
        self.nres = residues
        self.anomalous = anomalous
        self.cell = cell
        self.spacegroup = spacegroup
        self.log = logging.getLogger()
        self.log.setLevel(logging.DEBUG)
        self.xdsAppeared = False
        self.autoPROCPath = os.path.join(self.autoprocessingPath, "autoPROC")
        if not os.path.exists(self.autoPROCPath):
            os.makedirs(self.autoPROCPath, 0o755)
        self.xdsInputFile = os.path.join(self.autoprocessingPath, "XDS.INP")
        self.doAnomAndNonanom = True

    def parse_input_file(self):
        # the other parameters are not used right now
        self.inputXml = inputTemplate.format(
            dataCollectionId=self.dataCollectionId,
            doAnomAndNonanom=self.doAnomAndNonanom,
            autoPROCPath=self.autoPROCPath,
        )

        # we now need a temp file in the data dir to write the data model to
        ednaInputFileName = "autoPROC_input.xml"
        self.ednaInputFilePath = os.path.join(self.autoPROCPath, ednaInputFileName)
        if os.path.exists(self.ednaInputFilePath):
            # Create unique file name
            ednaInputFile = tempfile.NamedTemporaryFile(
                suffix=".xml",
                prefix="autoPROC_input-",
                dir=self.autoPROCPath,
                delete=False,
            )
            self.ednaInputFilePath = os.path.join(self.autoPROCPath, ednaInputFile.name)
            ednaInputFile.file.write(self.inputXml)
            ednaInputFile.close()
        else:
            open(self.ednaInputFilePath, "w").write(self.inputXml)
        os.chmod(self.ednaInputFilePath, 0o755)

        directories = self.autoprocessingPath.split(os.path.sep)
        try:
            beamline = directories[3]
            proposal = directories[4]
        except Exception:
            beamline = "unknown"
            proposal = "unknown"

        # to do restrict autoPROC only for academic users!?

        template = string.Template(SCRIPT_TEMPLATE)
        self.script = template.substitute(
            beamline=beamline,
            proposal=proposal,
            autoPROCDirectory=self.autoPROCPath,
            dataCollectionId=self.dataCollectionId,
            inputFile=self.ednaInputFilePath,
        )

        # we also need some kind of script to run edna-plugin-launcher
        ednaScriptFileName = "autoPROC_launcher.sh"
        self.ednaScriptFilePath = os.path.join(self.autoPROCPath, ednaScriptFileName)
        if os.path.exists(self.ednaScriptFilePath):
            # Create unique file name
            ednaScriptFile = tempfile.NamedTemporaryFile(
                suffix=".sh",
                prefix="autoPROC_launcher-",
                dir=self.autoPROCPath,
                delete=False,
            )
            self.ednaScriptFilePath = os.path.join(
                self.autoPROCPath, ednaScriptFile.name
            )
            ednaScriptFile.file.write(self.script)
            ednaScriptFile.close()
        else:
            open(self.ednaScriptFilePath, "w").write(self.script)
        os.chmod(self.ednaScriptFilePath, 0o755)

    def execute(self):

        cmd = (
            "echo 'cd %s;source /mxn/groups/biomax/wmxsoft/scripts_mxcube/biomax_HPC.bash_profile;/mxn/groups/biomax/cmxsoft/edna-mx/scripts_maxiv/edna_sbatch.sh %s' | ssh -F /etc/ssh/.ssh -o UserKnownHostsFile=/etc/ssh/.ssh/known_host -i /etc/ssh/id_rsa_biomax-service %s; source /mxn/groups/biomax/wmxsoft/scripts_mxcube/biomax_HPC.bash_profile"
            % (self.autoPROCPath, self.ednaScriptFilePath, HPC_HOST)
        )

        # for test
        # cmd = "echo 'cd %s;/mxn/groups/biomax/cmxsoft/edna-mx/scripts_maxiv/edna_sbatch.sh %s' | ssh %s" % (autoPROCPath, ednaScriptFilePath, hpc_host)
        # print cmd
        logging.getLogger("HWR").info(
            "Autoproc launcher: command gonna be launched: %s" % cmd
        )

        p = subprocess.Popen(
            cmd, shell=True
        )  # , stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        p.wait()

    def parse_and_execute(self):
        self.parse_input_file()
        self.execute()


if __name__ == "__main__":
    args = sys.argv[1:]

    if (len(args) % 2) != 0:
        logging.error(
            "the argument list is not well formed (odd number of args/options)"
        )
        sys.exit()

    # do the arg parsing by hand since neither getopt nor optparse support
    # single dash long options.
    options = dict()
    for x in range(0, len(args), 2):
        options[args[x]] = args[x + 1]

    autoprocessingPath = options["-path"]

    residues = float(options.get("-residues", 200))
    anomalous = options.get("-anomalous", False)
    spacegroup = options.get("-sg", None)
    cell = options.get("-cell", "0,0,0,0,0,0")
    dataCollectionId = options["-datacollectionID"]
    mode = options.get("-mode")

    autoProc = AutoProcLauncher(
        autoprocessingPath,
        mode,
        dataCollectionId,
        residues,
        anomalous,
        cell,
        spacegroup,
    )
    autoProc.parse_and_execute()
