#!/usr/bin/env python
# python ednaProcLauncher.py -path
# /data/staff/biomax/staff/jie/20161212_thau_2/processed4 -mode after
# -datacollectionID 14 -residues 200 -anomalous False -cell "0,0,0,0,0,0"

import logging
import os
import string
import subprocess
import sys
import tempfile
import time
import urllib

import httplib

# XDS.INP creation is now asynchronous in mxcube, so it may not be here yet
# when we're started
WAIT_XDS_TIMEOUT = 100
HPC_HOST = "b-picard07-clu0-fe-0.maxiv.lu.se"

INPUT_TEMPLATE = """<?xml version="1.0"?>
<XSDataEDNAprocInput>
  <input_file>
    <path>
      <value>{xdsInputFile}</value>
    </path>
  </input_file>
  <data_collection_id>
    <value>{dataCollectionId}</value>
  </data_collection_id>
  <output_file>
    <path>
      <value>{output_path}</value>
    </path>
  </output_file>
{nresFragment}
{spacegroupFragment}
{cellFragment}
</XSDataEDNAprocInput>
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
ednaProcDirectory = "$ednaProcDirectory"
inputFile = "$inputFile"

pluginName = "EDPluginControlEDNAprocv1_0"
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

baseName = "{hostname}_{date}-{time}".format(hostname=hostname,
				 	     date=dateString,
					     time=timeString)
baseDir = os.path.join(ednaProcDirectory, baseName)
if not os.path.exists(baseDir):
    os.makedirs(baseDir, 0o755)
EDVerbose.screen("EDNA plugin working directory: %s" % baseDir)

ednaLogName = "EDNA_proc_{0}-{1}.log".format(dateString, timeString)
EDVerbose.setLogFileName(os.path.join(ednaProcDirectory, ednaLogName))
EDVerbose.setVerboseOn()

edPlugin = EDFactoryPluginStatic.loadPlugin(pluginName)
edPlugin.setDataInput(open(inputFile).read())
edPlugin.setBaseDirectory(ednaProcDirectory)
edPlugin.setBaseName(baseName)

EDVerbose.screen("Start of execution of EDNA plugin %s" % pluginName)
os.chdir(baseDir)
edPlugin.executeSynchronous()
"""


class EdnaProcLauncher:
    def __init__(
        self, path, mode, datacollectionID, residues, anomalous, cell, spacegroup
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
        self.ednaProcPath = os.path.join(self.autoprocessingPath, "EDNA_proc")
        self.ednaOutputFileName = "EDNA_proc_ispyb.xml"

        if not os.path.exists(self.ednaProcPath):
            os.makedirs(self.ednaProcPath, 0o755)
        self.xdsInputFile = os.path.join(self.autoprocessingPath, "XDS.INP")

    def parse_input_file(self):
        # parse the input file to find the first image
        self.xdsAppeared = False
        self.waitXdsStart = time.time()
        logging.getLogger("HWR").info(
            "EDNA_proc launcher: waiting for XDS.INP file: %s" % self.xdsInputFile
        )
        while not self.xdsAppeared and (
            time.time() - self.waitXdsStart < WAIT_XDS_TIMEOUT
        ):
            time.sleep(1)
            if (
                os.path.exists(self.xdsInputFile)
                and os.stat(self.xdsInputFile).st_size > 0
            ):
                time.sleep(1)
                self.xdsAppeared = True
                logging.getLogger("HWR").info(
                    "EDNA_proc launcher: XDS.INP file is there, size=%s"
                    % os.stat(self.xdsInputFile).st_size
                )
        if not self.xdsAppeared:
            logging.getLogger("HWR").error(
                "XDS.INP file ({0}) failed to appear after {1} seconds".format(
                    self.xdsInputFile, WAIT_XDS_TIMEOUT
                )
            )
        self.ednaOutputFilePath = os.path.join(
            self.ednaProcPath, self.ednaOutputFileName
        )
        if os.path.exists(self.ednaOutputFilePath):
            self.ednaOutputFile = tempfile.NamedTemporaryFile(
                suffix=".xml",
                prefix="EDNA_proc_ispyb-",
                dir=self.ednaProcPath,
                delete=False,
            )

            self.ednaOutputFilePath = os.path.join(
                self.ednaProcPath, self.ednaOutputFile.name
            )
            self.ednaOutputFile.close()
        else:
            open(self.ednaOutputFilePath, "w").write("")
        os.chmod(self.ednaOutputFilePath, 0o755)

        # ignore null nres, which might happen for whatever reason
        if self.nres is not None and self.nres != 0:
            nresFragment = """  <nres>
            <value>{0}</value>
          </nres>""".format(self.nres)
        else:
            nresFragment = ""

        if self.spacegroup is not None:
            spacegroupFragment = """  <spacegroup>
            <value>{0}</value>
          </spacegroup>""".format(self.spacegroup)
        else:
            spacegroupFragment = ""

        if self.cell is not None:
            cellFragment = """  <unit_cell>
            <value>{0}</value>
          </unit_cell>""".format(self.cell)
        else:
            cellFragment = ""

        # the other parameters are not used right now
        self.inputXml = INPUT_TEMPLATE.format(
            xdsInputFile=self.xdsInputFile,
            dataCollectionId=self.dataCollectionId,
            output_path=self.ednaOutputFilePath,
            nresFragment=nresFragment,
            cellFragment=cellFragment,
            spacegroupFragment=spacegroupFragment,
        )

        # we now need a temp file in the data dir to write the data model to
        ednaInputFileName = "EDNA_proc_input.xml"
        ednaInputFilePath = os.path.join(self.ednaProcPath, ednaInputFileName)
        if os.path.exists(ednaInputFilePath):
            # Create unique file name
            ednaInputFile = tempfile.NamedTemporaryFile(
                suffix=".xml",
                prefix="EDNA_proc_input-",
                dir=self.ednaProcPath,
                delete=False,
            )
            ednaInputFilePath = os.path.join(self.ednaProcPath, ednaInputFile.name)
            ednaInputFile.file.write(self.inputXml)
            ednaInputFile.close()
        else:
            open(ednaInputFilePath, "w").write(self.inputXml)
        os.chmod(ednaInputFilePath, 0o755)

        directories = self.autoprocessingPath.split(os.path.sep)
        try:
            beamline = directories[3]
            proposal = directories[4]
        except Exception:
            beamline = "unknown"
            proposal = "unknown"

        template = string.Template(SCRIPT_TEMPLATE)
        self.script = template.substitute(
            beamline=beamline,
            proposal=proposal,
            ednaProcDirectory=self.ednaProcPath,
            dataCollectionId=self.dataCollectionId,
            inputFile=ednaInputFilePath,
        )

        # we also need some kind of script to run edna-plugin-launcher
        ednaScriptFileName = "EDNA_proc_launcher.sh"
        self.ednaScriptFilePath = os.path.join(self.ednaProcPath, ednaScriptFileName)
        if os.path.exists(self.ednaScriptFilePath):
            # Create unique file name
            ednaScriptFile = tempfile.NamedTemporaryFile(
                suffix=".sh",
                prefix="EDNA_proc_launcher-",
                dir=self.ednaProcPath,
                delete=False,
            )
            self.ednaScriptFilePath = os.path.join(
                self.ednaProcPath, ednaScriptFile.name
            )
            ednaScriptFile.file.write(self.script)
            ednaScriptFile.close()
        else:
            open(self.ednaScriptFilePath, "w").write(self.script)
        os.chmod(self.ednaScriptFilePath, 0o755)

    def execute(self):
        cmd = (
            "echo 'cd %s;source /mxn/groups/biomax/wmxsoft/scripts_mxcube/biomax_HPC.bash_profile;/mxn/groups/biomax/cmxsoft/edna-mx/scripts_maxiv/edna_sbatch.sh %s' | ssh -F /etc/ssh/.ssh -o UserKnownHostsFile=/etc/ssh/.ssh/known_host -i /etc/ssh/id_rsa_biomax-service %s;source /mxn/groups/biomax/wmxsoft/scripts_mxcube/biomax_HPC.bash_profile"
            % (self.ednaProcPath, self.ednaScriptFilePath, HPC_HOST)
        )

        # for test
        # cmd = "echo 'cd %s;/mxn/groups/biomax/cmxsoft/edna-mx/scripts_maxiv/edna_sbatch.sh %s' | ssh %s" % (autoPROCPath, ednaScriptFilePath, hpc_host)
        # print cmd
        logging.getLogger("HWR").info(
            "EDNA_proc launcher: command gonna be launched: %s" % cmd
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

    edna = EdnaProcLauncher(
        autoprocessingPath,
        mode,
        dataCollectionId,
        residues,
        anomalous,
        cell,
        spacegroup,
    )
    edna.parse_and_execute()
