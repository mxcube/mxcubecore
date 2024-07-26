#!/usr/bin/env python

import os
import sys
import time
import socket
import traceback

sys.path.insert(0, "/mxn/groups/biomax/cmxsoft/edna-mx/kernel/src")

from EDVerbose import EDVerbose
from EDFactoryPluginStatic import EDFactoryPluginStatic

beamline = "unknown"
proposal = "unknown"
dataCollectionId = 100
autoPROCDirectory = "/home/data/autoPROC"
inputFile = "/home/data/autoPROC/autoPROC_input.xml"

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

#!/usr/bin/env python

import os
import sys
import time
import socket
import traceback

sys.path.insert(0, "/mxn/groups/biomax/cmxsoft/edna-mx/kernel/src")

from EDVerbose import EDVerbose
from EDFactoryPluginStatic import EDFactoryPluginStatic

beamline = "unknown"
proposal = "unknown"
dataCollectionId = 100
autoPROCDirectory = "/home/data/autoPROC"
inputFile = "/home/data/autoPROC/autoPROC_input.xml"

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

#!/usr/bin/env python

import os
import sys
import time
import socket
import traceback

sys.path.insert(0, "/mxn/groups/biomax/cmxsoft/edna-mx/kernel/src")

from EDVerbose import EDVerbose
from EDFactoryPluginStatic import EDFactoryPluginStatic

beamline = "unknown"
proposal = "unknown"
dataCollectionId = 100
autoPROCDirectory = "/home/data/autoPROC"
inputFile = "/home/data/autoPROC/autoPROC_input.xml"

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

