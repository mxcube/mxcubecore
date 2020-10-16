#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.


import os
import copy
import logging
import gevent
import time

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.BaseHardwareObjects import Device
from gevent import Timeout
import numpy


# import DeviceProxy function and DevState:
from PyTango import DevState
from PyTango import DeviceProxy

last_centred_position = [200, 200]


class Centring(Device):
    """
    Description:     This class controls the operation of Tango Motor
    """

    def __init__(self, *args):
        """
        Description:
        """
        HardwareObject.__init__(self, *args)
        self.proxyMotor = None  # Hardware object to change motor attributes
        self.motor_name = None  # Tango name of DeviceServer controlling the motor

    def init(self):
        self.gonioAxes = []

        # self.gonioAxes = []
        # for axis in self['gonioAxes']:
        #  self.gonioAxes.append({'type':axis.type,'direction':eval(axis.direction),\
        #                   'motor_name':axis.motorname,'motor_HO':
        # HardwareRepository.get_hardware_repository().get_hardware_object(axis.motorHO)
        # })

        print("Centring Init")
        print("-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")

    def initCentringProcedure(self):

        print("initCentringProcedure(self)")
        """
        Descript. : call before starting rotate-click sequence
        """
        self.centringDataTensor = []
        self.centringDataMatrix = []
        self.motorConstraints = []

        # self.centeingPoints = [Point(0.0,0.0), Point(0.0,0.0), Point(0.0,0.0)]  # array of 3 points, initial values - zeroes
        # print( "self.centeingPoints[0] = (", self.centeingPoints[0].x, ", ", self.centeingPoints[0].y, ")")
        # print( "self.centeingPoints[1] = (", self.centeingPoints[1].x, ", ", self.centeingPoints[1].y, ")")
        # print( "self.centeingPoints[2] = (", self.centeingPoints[2].x, ", ", self.centeingPoints[2].y, ")")

        print("Centring initCentringProcedure")
        print("-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")

    def appendCentringDataPoint(self, camera_coordinates):
        """
        Descript. : call after each click and send click points - but relative in mm
        """
        # self.centringDataTensor.append(self.factor_matrix())
        self.centringDataMatrix.append(
            self.camera_coordinates_to_vector(camera_coordinates)
        )

        ll = len(self.centringDataMatrix)
        print(("len(self.centringDataMatrix) = ", ll))

        print(("self.centringDataMatrix = ", self.centringDataMatrix[ll - 1]))

        print("appendCentringDataPoint(self)")
        print("-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")

    #    def setCentringDataPoint(self, i, camera_coordinates):
    #        print("camera_coordinates['X'] = ",  camera_coordinates['X'])
    #        print("camera_coordinates['Y'] = ",  camera_coordinates['Y'])
    #        #self.centeingPoints[i] =  point(camera_coordinates['X'], camera_coordinates['Y']])
    #        print("appendCentringDataPoint(self)")
    #        print( '-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+')

    def centeredPosition(self, return_by_name=False):
        """
        Descript. : call after appending the last click.
        Return    : {motorHO:position} dictionary.

        M=numpy.zeros(shape=(self.translationAxesCount,self.translationAxesCount))
        V=numpy.zeros(shape=(self.translationAxesCount))

        for l in range(0,self.translationAxesCount):
           for i in range (0,len(self.centringDataMatrix)):
              for k in range(0,len(self.cameraAxes)):
                 V[l] += self.centringDataTensor[i][l][k]*self.centringDataMatrix[i][k]
           for m in range(0,self.translationAxesCount):
              for i in range (0,len(self.centringDataMatrix)):
                 for k in range(0,len(self.cameraAxes)):
                    M[l][m] += self.centringDataTensor[i][l][k]*self.centringDataTensor[i][m][k]
        tau_cntrd = numpy.dot(numpy.linalg.pinv(M,rcond=1e-6),V)

        tau_cntrd = self.apply_constraints(M,tau_cntrd)
        """
        # return self.vector_to_centred_positions( - tau_cntrd +
        # self.translation_datum(), return_by_name)
        print("centeredPosition(self)")
        print("-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")

        return self.vector_to_centred_positions(123, 456)

    def vector_to_centred_positions(self, vector, return_by_name=False):
        dic = {}
        index = 0
        # for axis in self.gonioAxes:
        #  if axis['type'] == "translation":
        #     if return_by_name:
        #         dic[axis['motor_name']]=vector[index]
        #     else:
        #         dic[axis['motor_HO']]=vector[index]
        #     index += 1

        print("vector_to_centred_positions(self)")
        print("-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+")

        return dic

    def camera_coordinates_to_vector(self, camera_coordinates_dictionary):
        vector = []

        vector.append(camera_coordinates_dictionary["X"])
        vector.append(camera_coordinates_dictionary["Y"])

        return vector
