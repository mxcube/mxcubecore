#!/usr/bin/env python

"""A simple client for MetadataManager and MetaExperiment
"""

import os
import sys
import logging
import PyTango.client

class MetadataManagerClient(object):

    metadataManager = None
    metaExperiment = None

    """
    A client for the MetadataManager and MetaExperiment tango Devices

    Attributes:
        name: name of the tango device. Example: 'id21/metadata/ingest'
    """
    def __init__(self, metadataManagerName, metaExperimentName):
        """
        Return a MetadataManagerClient object whose metadataManagerName is *metadataManagerName*
        and metaExperimentName is *metaExperimentName*
        """
        self.dataRoot = None
        self.proposal = None
        self.sample = None
        self.datasetName = None

        if metadataManagerName:
            self.metadataManagerName = metadataManagerName
        if metaExperimentName:
            self.metaExperimentName = metaExperimentName

        print('MetadataManager: %s' % metadataManagerName)
        print('MetaExperiment: %s' % metaExperimentName)

        """ Tango Devices instances """
        try:
            MetadataManagerClient.metadataManager = PyTango.client.Device(self.metadataManagerName)
            MetadataManagerClient.metaExperiment = PyTango.client.Device(self.metaExperimentName)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

    def printStatus(self):
        print('DataRoot: %s' % MetadataManagerClient.metaExperiment.dataRoot)
        print('Proposal: %s' % MetadataManagerClient.metaExperiment.proposal)
        print('Sample: %s' % MetadataManagerClient.metaExperiment.sample)
        print('Dataset: %s' % MetadataManagerClient.metadataManager.scanName)



    def __setDataRoot(self, dataRoot):
        try:
            MetadataManagerClient.metaExperiment.dataRoot = dataRoot
            self.dataRoot = dataRoot
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

    ''' Set proposal should be done before stting the data root '''
    def __setProposal(self, proposal):
        try:
            MetadataManagerClient.metaExperiment.proposal = proposal
            self.proposal = proposal
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

    def __setSample(self, sample):
        try:
            MetadataManagerClient.metaExperiment.sample = sample
            self.sample = sample
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

    def __setDataset(self, datasetName):
        try:
            MetadataManagerClient.metadataManager.scanName = datasetName
            self.datasetName = datasetName
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

    def start(self, dataRoot, proposal, sampleName, datasetName):
        """ Starts a new dataset """
        if MetadataManagerClient.metaExperiment:
            try:
                """ setting proposal """
                self.__setProposal(proposal)

                """ setting dataRoot """
                self.__setDataRoot(dataRoot)

                """ setting sample """
                self.__setSample(sampleName)

                """ setting dataset """
                self.__setDataset(datasetName)

                """ setting datasetName """
                if (str(MetadataManagerClient.metaExperiment.state()) == 'ON'):
                    if (str(MetadataManagerClient.metadataManager.state()) == 'ON'):
                        MetadataManagerClient.metadataManager.StartScan()

            except:
                print "Unexpected error:", sys.exc_info()[0]
                raise

    def end(self):
        try:
            MetadataManagerClient.metadataManager.endScan()
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

if __name__ == '__main__':
    metadataManagerName = 'id30a1/metadata/ingest'
    metaExperimentName = 'id30a1/metadata/experiment'
    client = MetadataManagerClient(metadataManagerName, metaExperimentName)

    client.start('/tmp/metadata', 'mx415', 'sample2', 'dataset3')
    client.printStatus()
    client.end()

