"""SpecMotorWSpecPositions

template:
  <device class = "SpecMotorWSpecPositions">
    <username>friendly label for user</username>
    <specname>motor mnemonic in Spec</specname>
    <specversion>host:version</specversion>
    <channel type="spec" name="positions">global associative array in Spec with positions defined</channel>
    <command type="spec" name="setNewPosition">macro in Spec to set new positions from an associative array</command>
    <!-- <GUIstep>default step when moving motor from the GUI</GUIstep>
         <delta>tolerance allowed between real motor position and defined position</delta> -->
  </device>
"""
import logging

import SpecMotor

class SpecMotorWSpecPositions(SpecMotor.SpecMotor):
    def __init__(self, *args):
        SpecMotor.SpecMotor.__init__(self, *args)
    
        self.predefinedPositions          = {}
        self.predefinedPositionsNamesList = []
 

    def init(self):
        chanPositionsArray = self.getChannelObject('positions')
        chanPositionsArray.connectSignal('update', self.positionsArrayChanged)
        self.delta = self.getProperty('delta') or 0
               

    def disconnected(self):
        self.predefinedPositions = {}
        self.predefinedPositionsNamesList = []
        self.emit('newPredefinedPositions', (self.predefinedPositionsNamesList, ))

    
    def positionsArrayChanged(self, positionsArray):
        self.predefinedPositions = positionsArray
        
        for pos in self.predefinedPositions:
               self.predefinedPositions[pos] = float(self.predefinedPositions[pos])

        self.sortPredefinedPositionsList()
        self.emit('newPredefinedPositions', (self.predefinedPositionsNamesList, ))
       
        
    def sortPredefinedPositionsList(self):
        self.predefinedPositionsNamesList = list(self.predefinedPositions.keys())
        self.predefinedPositionsNamesList.sort(lambda x, y: int(round(self.predefinedPositions[x] - self.predefinedPositions[y])))


    def motorPositionChanged(self, channelValue):
        SpecMotor.SpecMotor.motorPositionChanged.__func__(self, channelValue)
        
        pos = float(channelValue)

        for positionName in self.predefinedPositions:
            if self.predefinedPositions[positionName] >= pos-self.delta and self.predefinedPositions[positionName] <= pos+self.delta:
                self.emit('predefinedPositionChanged', (positionName, pos, ))
                break


    def getPredefinedPositionsList(self):
        return self.predefinedPositionsNamesList


    def moveToPosition(self, positionName):
        try:
            self.move(self.predefinedPositions[positionName])
        except:
            logging.getLogger("HWR").exception('Cannot move motor %s: invalid position name.', str(self.userName()))


    def getCurrentPositionName(self):
        if self.isReady() and self.getState() == self.READY:
            for positionName in self.predefinedPositions:
                if self.predefinedPositions[positionName] >= self.getPosition()-self.delta and self.predefinedPositions[positionName] <= self.getPosition()+self.delta:
                   return positionName


    def setNewPredefinedPosition(self, positionName, positionOffset):
        try:
            self.executeCommand('setNewPosition', positionName, positionOffset)
        except AttributeError:
            logging.getLogger("HWR").exception('Cannot set new predefined position')













