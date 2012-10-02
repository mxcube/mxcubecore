"""Gives access to the Hardware Objects contained in the Hardware Repository database

The Hardware Repository database is a set of XML files describing devices, equipments
and procedures on a beamline. Each XML file represent a Hardware Object.
The Hardware Repository module provides access to these Hardware Objects, and manages
connections to the Control Software (Spec or Taco Device Servers).
""" 

__author__ = 'Matias Guijarro'
__version__ = 1.3

import logging
import weakref
import types
import sys
import os
import stat
import time
import sets

try:
  from SpecClient_gevent import SpecEventsDispatcher
  from SpecClient_gevent import SpecConnectionsManager
  from SpecClient_gevent import SpecWaitObject
  from SpecClient_gevent import SpecClientError
except ImportError:
  from SpecClient import SpecEventsDispatcher
  from SpecClient import SpecConnectionsManager
  from SpecClient import SpecWaitObject
  from SpecClient import SpecClientError
  
import HardwareObjectFileParser
import BaseHardwareObjects

_instance = None
_hwrserver = None


def addHardwareObjectsDirs(hoDirs):
    if type(hoDirs) == types.ListType:
        newHoDirs = filter(os.path.isdir, map(os.path.abspath, hoDirs))

        for newHoDir in newHoDirs:
            if not newHoDir in sys.path:
                #print 'inserted in sys.path = %s' % newHoDir
                sys.path.insert(0, newHoDir)
                    

default_local_ho_dir = os.environ.get('CUSTOM_HARDWARE_OBJECTS_PATH', '').split(os.path.pathsep)
addHardwareObjectsDirs(default_local_ho_dir)

def setHardwareRepositoryServer(hwrserver):
    global _hwrserver
    _hwrserver = hwrserver
    

def HardwareRepository(hwrserver = None):
    """Return the Singleton instance of the Hardware Repository."""
    global _instance        

    if qApp.startingUp():
        raise RuntimeError, "A QApplication object must be created before Hardware Repository can be used"

    if _instance is None:
        if _hwrserver is None:
            setHardwareRepositoryServer(hwrserver)
        
        _instance = __HardwareRepositoryClient(_hwrserver)

    return _instance


class _weak_callable:
    def __init__(self,obj,func):
        self._obj = obj
        self._meth = func

    def __call__(self,*args,**kws):
        if self._obj is not None:
            return self._meth(self._obj,*args,**kws)
        else:
            return self._meth(*args,**kws)

    def __getattr__(self,attr):
        if attr == 'im_self':
            return self._obj
        if attr == 'im_func':
            return self._meth
        raise AttributeError, attr


class WeakMethod:
    """ Wraps a function or, more importantly, a bound method, in
    a way that allows a bound method's object to be GC'd, while
    providing the same interface as a normal weak reference. """
    def __init__(self,fn):
        try:
            self._obj = weakref.ref(fn.im_self)
            self._meth = fn.im_func
        except AttributeError:
            # It's not a bound method.
            self._obj = None
            self._meth = fn

    def __call__(self):
        if self._dead(): return None
        
        if self._obj is not None:
            return _weak_callable(self._obj(),self._meth)
        else:
            return _weak_callable(self._obj, self._meth)
        
    def _dead(self):
        return self._obj is not None and self._obj() is None

    
class __HardwareRepositoryClient:
    """Hardware Repository class
    
    Warning -- should not be instanciated directly ; call the module's level HardwareRepository() function instead
    """
    def __init__(self, serverAddress):
        """Constructor"""
        self.serverAddress = serverAddress
        self.requiredHardwareObjects = {}
        self.xml_source={}
        
    def connect(self):
        self.invalidHardwareObjects = sets.Set()
        self.hardwareObjects = weakref.WeakValueDictionary()
        mngr = SpecConnectionsManager.SpecConnectionsManager() #pollingThread = False)

        self.server = mngr.getConnection(self.serverAddress)
        
        SpecWaitObject.waitConnection(self.server, timeout = 3) 	 

        # in case of update of a Hardware Object, we discard it => bricks will receive a signal and can reload it
        self.server.registerChannel("update", self.discardHardwareObject, dispatchMode=SpecEventsDispatcher.FIREEVENT)
        

    def require(self, mnemonicsList):
        """Download a list of Hardware Objects in one go"""
        self.requiredHardwareObjects = {}
        
        try:
            t0=time.time()
            mnemonics = ",".join([repr(mne) for mne in mnemonicsList])
            if len(mnemonics) > 0:
                self.requiredHardwareObjects = SpecWaitObject.waitReply(self.server, 'send_msg_cmd_with_return' , ('xml_getall(%s)' % mnemonics, ), timeout = 3)
                logging.getLogger("HWR").debug("Getting all the hardware objects took %s ms." % ((time.time()-t0)*1000))
        except SpecClientError.SpecClientTimeoutError:
            logging.getLogger('HWR').error("Timeout loading Hardware Objects")
        except:
            logging.getLogger('HWR').exception("Could not execute 'require' on Hardware Repository server")

                
    def loadHardwareObject(self, hoName):               
        """Load a Hardware Object
        
        Parameters :
          hoName -- string name of the Hardware Object to load, for example '/motors/m0'

        Return :
          the loaded Hardware Object, or None if it fails
        """
        if self.server.isSpecConnected():
            try:
                #t0=time.time()
                if hoName in self.requiredHardwareObjects:
                    replyDict = self.requiredHardwareObjects[hoName]
                    #del self.requiredHardwareObjects[hoName]
                else:
                    replyDict = SpecWaitObject.waitReply(self.server, 'send_msg_chan_read', ('xml_get("%s")' % hoName, ), timeout = 3)
            except:
                logging.getLogger('HWR').exception('Could not load Hardware Object "%s"', hoName)
            else:
                #print 'loading %s took %s ms' % (hoName, 1000*(time.time()-t0))
                try:
                  xmldata = replyDict['xmldata']
                  mtime = int(replyDict['mtime'])
                except KeyError:
                  logging.getLogger("HWR").error("Cannot load Hardware Object %s: file does not exist.", hoName)
                  return

                #print xmldata
                if len(xmldata) > 0:
                    try:
                        #t0 = time.time()
                        ho = self.parseXML(xmldata, hoName)
                        #print 'parsing %s took %s ms' % (hoName, (time.time()-t0)*1000)
                    except:
                        logging.getLogger("HWR").exception("Cannot parse XML file for Hardware Object %s", hoName)
                    else:
                        if ho is not None:
                            self.xml_source[hoName]=xmldata
                            dispatcher.send('hardwareObjectLoaded', hoName, self)

                            def hardwareObjectDeleted(name=ho.name()):
                                logging.getLogger("HWR").debug("%s Hardware Object has been deleted from Hardware Repository", name)
                                del self.hardwareObjects[name]

                            ho.resolveReferences()

                            try:
                                def addChannelsAndCommands(node):
                                  #import pdb; pdb.set_trace()
                                  if isinstance(node, BaseHardwareObjects.CommandContainer):
                                     node._addChannelsAndCommands()
                                  for child_node in node:
                                    addChannelsAndCommands(child_node)
                                addChannelsAndCommands(ho) 
                            except:
                                logging.getLogger('HWR').exception("Error while adding commands and/or channels to Hardware Object %s", hoName)

                            try:
                                ho._init()
                                ho.init()
                            except:
                                logging.getLogger('HWR').exception('Cannot initialize Hardware Object "%s"', hoName)

                                self.invalidHardwareObjects.add(ho.name())

                                return None
                            else:
                                if ho.name() in self.invalidHardwareObjects:
                                    self.invalidHardwareObjects.remove(ho.name())

                                self.hardwareObjects[ho.name()] = ho

                            return ho
                        else:
                            logging.getLogger("HWR").error("Failed to load Hardware Object %s", hoName)
                else:
                    logging.getLogger('HWR').error('Cannot load Hardware Object "%s" : file not found.', hoName)   
        else:
            logging.getLogger('HWR').error('Cannot load Hardware Object "%s" : not connected to server.', hoName)

   
    def discardHardwareObject(self, hoName):
        """Remove a Hardware Object from the Hardware Repository

        Parameters :
          hoName -- the name of the Hardware Object to remove
          
        Emitted signals :
          hardwareObjectDiscarded (<object name>) -- emitted when the object has been removed
        """
        try:
            del self.hardwareObjects[hoName]
        except KeyError:
            pass
        try:    
            self.invalidHardwareObjects.remove(hoName)
        except:
            pass
        try:
            del self.requiredHardwareObjects[hoName]
        except KeyError:
            pass

        self.emit(PYSIGNAL('hardwareObjectDiscarded'), (hoName, ))
            
        
    def parseXML(self, XMLString, hoName):
        """Load a Hardware Object from its XML string representation

        Parameters :
          XMLString -- the XML string
          hoName -- the name of the Hardware Object to load (i.e. '/motors/m0')

        Return :
          the Hardware Object, or None if it fails
        """
	try:
            ho = HardwareObjectFileParser.parseString(XMLString, hoName)
        except:
            logging.getLogger('HWR').exception('Cannot parse Hardware Repository file %s', hoName)
        else:
            return ho
            

    def update(self, name, updatesList):
        if self.server is not None and self.server.isSpecConnected():
            self.server.send_msg_cmd_with_return('xml_multiwrite("%s", "%s")' % (name, str(updatesList)))
        else:
            logging.getLogger('HWR').error('Cannot update Hardware Object %s : not connected to server', name)
                  

    def rewrite_xml(self, name, xml):
        if self.server is not None and self.server.isSpecConnected():    
            self.server.send_msg_cmd_with_return('xml_writefile("%s", %s)' % (name, repr(xml)))
            self.xml_source[name]=xml
        else:
            logging.getLogger('HWR').error('Cannot update Hardware Object %s : not connected to server', name)
            
    
    def __getitem__(self, item):
        if item == 'equipments':
            return self.getEquipments()
        elif item == 'procedures':
            return self.getProcedures()
        elif item == 'devices':
            return self.getDevices()
        else:
            return self.getHardwareObject(item)

        raise KeyError
    

    def getHardwareRepositoryFiles(self, startdir = '/'):
        try:
            completeFilesList = SpecWaitObject.waitReply(self.server, 'send_msg_chan_read', ('readDirectory()', ), timeout = 3)
        except:
            logging.getLogger('HWR').error('Cannot retrieve Hardware Repository files list')
        else:
            if '__error__' in completeFilesList:
                logging.getLogger('HWR').error('Error while doing Hardware Repository files list')
                return
            else:
                for name, filename in completeFilesList.iteritems():
                    if name.startswith(startdir):
                        yield (name, filename)
                        
    
    def getEquipments(self):
        """Return the list of the currently loaded Equipments Hardware Objects"""
        list = []

        for hoName in self.hardwareObjects:
            if self.isEquipment(hoName):
                list.append(self.hardwareObjects[hoName])

        return list

    
    def getProcedures(self):
        """Return the list of the currently loaded Procedures Hardware Objects"""
        list = []

        for hoName in self.hardwareObjects:
            if self.isProcedure(hoName):
                list.append(self.hardwareObjects[hoName])

        return list
        

    def getDevices(self):
        """Return the list of the currently loaded Devices Hardware Objects"""
        list = []

        for hoName in self.hardwareObjects:
            if self.isDevice(hoName):
                list.append(self.hardwareObjects[hoName])

        return list

    
    def getHardwareObject(self, objectName):
        """Return a Hardware Object given its name

        If the object is not in the Hardware Repository, try to load it.

        Parameters :
          objectName -- the name of the Hardware Object

        Return :
          the required Hardware Object
        """
        try:
            if objectName:
                if objectName in self.invalidHardwareObjects:
                    return None
            
                try:
                    ho = self.hardwareObjects[objectName]
                except KeyError:
                    ho = self.loadHardwareObject(objectName)
                
                return ho
        except TypeError, err:
            logging.getLogger("HWR").exception("could not get Hardware Object %s", objectName)
        

    def getEquipment(self, equipmentName):
        """Return an Equipment given its name (see getHardwareObject())"""
        return self.getHardwareObject(equipmentName)
        

    def getDevice(self, deviceName):
        """Return a Device given its name (see getHardwareObject())"""
        return self.getHardwareObject(deviceName)


    def getProcedure(self, procedureName):
        """Return a Procedure given its name (see getHardwareObject())"""
        return self.getHardwareObject(procedureName)
        
    
    def getConnection(self, connectionName):
        """Return the Connection object for a Spec connection, given its name

        Parameters :
          connectionName -- a Spec version name ('host:port' string)

        Return :
          the corresponding SpecConnection object
        """
        connectionsManager = SpecConnectionsManager.SpecConnectionsManager()

        return connectionsManager.getConnection(connectionName)
    

    def isDevice(self, name):
        """Check if a Hardware Object is a Device

        Parameters :
          name -- name of the Hardware Object to test

        Return :
          True if the Hardware Object is a Device, False otherwise
        """
        try:
            return isinstance(self.hardwareObjects[name], BaseHardwareObjects.Device)
        except:
            return False
        

    def isProcedure(self, name):
        """Check if a Hardware Object is a Procedure

        Parameters :
          name -- name of the Hardware Object to test

        Return :
          True if the Hardware Object is a Procedure, False otherwise
        """
        try:
            return isinstance(self.hardwareObjects[name], BaseHardwareObjects.Procedure)
        except:
            return False


    def isEquipment(self, name):
        """Check if a Hardware Object is an Equipment

        Parameters :
          name -- name of the Hardware Object to test

        Return :
          True if the Hardware Object is an Equipment, False otherwise
        """
        try:
            return isinstance(self.hardwareObjects[name], BaseHardwareObjects.Equipment)
        except:
            return False
        

    def hasHardwareObject(self, name):
        """Check if the Hardware Repository contains an object

        Parameters :
          name -- name of the Hardware Object

        Return :
          True if the Hardware Object is loaded in the Hardware Repository, False otherwise
        """
        return name in self.hardwareObjects
       

    def getInfo(self, name):
        """Return a dictionary with information about the specified Hardware Object

        Parameters :
          name -- name of the Hardware Object

        Return :
          a dictionary containing information about the Hardware Object
        """
        try:
            ho = self.hardwareObjects[name]
        except KeyError:
            return {}
        else:
            ho_class = ho.__class__.__name__
            
            d = { "class": ho_class,
                  "python module": sys.modules[ho.__module__].__file__ }

            if hasattr(ho, "isReady"):
                d["is ready ?"] = str(ho.isReady())

            if hasattr(ho, "getCommands"):
                # hardware object is a command container
                d["commands"] = {}
                
                for cmd in ho.getCommands():
                    if cmd.__class__.__name__ == "SpecCommand":
                        d["commands"][cmd.userName()] = { "type": "spec",
                                                          "version": "%s:%s" % (cmd.connection.host, cmd.connection.port or cmd.connection.scanname),
                                                          "connected ?": cmd.isSpecConnected() and "yes" or "no",
                                                          "macro or function": str(cmd.command) }
                    elif cmd.__class__.__name__ == "TacoCommand":
                        dd = { "type": "taco",
                               "device": cmd.deviceName }
                        
                        try:
                            dd["imported ?"] = cmd.device.imported and "yes" or "no"
                        except:
                            dd["imported ?"] = "no, invalid Taco device"
                        
                        dd["device method"] = str(cmd.command)
                        
                        d["commands"][cmd.userName()] = dd
                    elif cmd.__class__.__name__ == "TangoCommand":
                        d["commands"][cmd.userName()] = { "type": "tango",
                                                          "device": cmd.deviceName,
                                                          "imported ?": cmd.device is not None and "yes" or "no, invalid Tango device",
                                                          "device method": str(cmd.command) }

                d["channels"] = {}
                
                for chan in ho.getChannels():
                    if chan.__class__.__name__ == "SpecChannel":
                        d["channels"][chan.userName()] = { "type": "spec",
                                                          "version": "%s:%s" % (chan.connection.host, chan.connection.port or chan.connection.scanname),
                                                          "connected ?": chan.isSpecConnected() and "yes" or "no",
                                                          "variable": str(chan.varName) }
                    elif chan.__class__.__name__ == "TangoChannel":
                        d["channels"][chan.userName()] = { "type": "tango",
                                                          "device": chan.deviceName,
                                                          "imported ?": chan.device is not None and "yes" or "no, invalid Tango device or attribute name",
                                                          "attribute": str(chan.attributeName) }

            if "SpecMotorA" in [klass.__name__ for klass in ho.__class__.__bases__]:
                d["spec version"] = ho.specVersion
                d["motor mnemonic"] = ho.specName
                try:
                    d["connected ?"] = ho.connection.isSpecConnected() and "yes" or "no"
                except:
                    d["connected ?"] = "no"


            if isinstance(ho, BaseHardwareObjects.DeviceContainer):
                d["children"] = {}
                
                for ho in ho.getDevices():
                    d["children"][ho.name()] = self.getInfo(ho.name())
                    
            return d
        
    
    def endPolling(self):
        """Stop all pollers

        Warning : should not be used directly (finalization purposes only)
        """
        return


    def close(self):
        """'close' the Hardware Repository

        Discards all Hardware Objects
        """
        self.endPolling()

        self.hardwareObjects = weakref.WeakValueDictionary()


    def timerEvent(self, t_ev):
        try:
            global _timers
        
            func_ref = _timers[t_ev.timerId()]
            func = func_ref()

            if func is None:
                self.killTimer(t_ev.timerId())
                del _timers[t_ev.timerId()]
            else:
                try:
                    func()
                except:
                    logging.getLogger("HWR").exception("an error occured while calling timer function")
        except:
            logging.getLogger("HWR").exception("an error occured inside the timerEvent")
                                             

class HardwareRepositoryBrowser(QVBox):
    folderClosed = ["16 16 9 1",
                    "g c #808080",
                    "b c #c0c000",
                    "e c #c0c0c0",
                    "# c #000000",
                    "c c #ffff00",
                    ". c None",
                    "a c #585858",
                    "f c #a0a0a4",
                    "d c #ffffff",
                    "..###...........",
                    ".#abc##.........",
                    ".#daabc#####....",
                    ".#ddeaabbccc#...",
                    ".#dedeeabbbba...",
                    ".#edeeeeaaaab#..",
                    ".#deeeeeeefe#ba.",
                    ".#eeeeeeefef#ba.",
                    ".#eeeeeefeff#ba.",
                    ".#eeeeefefff#ba.",
                    ".##geefeffff#ba.",
                    "...##gefffff#ba.",
                    ".....##fffff#ba.",
                    ".......##fff#b##",
                    ".........##f#b##",
                    "...........####."]
    

    folderOpened = ["16 16 11 1",
                    "# c #000000",
                    "g c #c0c0c0",
                    "e c #303030",
                    "a c #ffa858",
                    "b c #808080",
                    "d c #a0a0a4",
                    "f c #585858",
                    "c c #ffdca8",
                    "h c #dcdcdc",
                    "i c #ffffff",
                    ". c None",
                    "....###.........",
                    "....#ab##.......",
                    "....#acab####...",
                    "###.#acccccca#..",
                    "#ddefaaaccccca#.",
                    "#bdddbaaaacccab#",
                    ".eddddbbaaaacab#",
                    ".#bddggdbbaaaab#",
                    "..edgdggggbbaab#",
                    "..#bgggghghdaab#",
                    "...ebhggghicfab#",
                    "....#edhhiiidab#",
                    "......#egiiicfb#",
                    "........#egiibb#",
                    "..........#egib#",
                    "............#ee#"]

    
    def __init__(self, parent):
        QVBox.__init__(self, parent)
        
        self.treeNodes = {}
        self.root = None
        self.itemStates= {}

        self.hardwareObjectsTree = QListView(self)
        self.setMargin(3)
        self.setSpacing(5)
        
        self.connect(self.hardwareObjectsTree, SIGNAL('expanded( QListViewItem * )'), self.expanded)
        self.connect(self.hardwareObjectsTree, SIGNAL('collapsed( QListViewItem * )'), self.collapsed)
        self.connect(self.hardwareObjectsTree, SIGNAL('clicked( QListViewItem * )'), self.hardwareObjectClicked)
   
        self.hardwareObjectsTree.addColumn('Hardware Objects')
        self.hardwareObjectsTree.addColumn('Type')
        self.hardwareObjectsTree.addColumn('name', QListView.Manual)
        self.hardwareObjectsTree.addColumn('file', QListView.Manual)
        self.hardwareObjectsTree.hideColumn(2)
        self.hardwareObjectsTree.hideColumn(3)
        
        self.fill()

        QObject.connect(_instance, PYSIGNAL('hardwareObjectLoaded'), self.hardwareObjectLoaded)
        QObject.connect(_instance, PYSIGNAL('hardwareObjectDiscarded'), self.hardwareObjectDiscarded)
        

    def expanded(self, item):
        item.setPixmap(0, QPixmap(self.folderOpened))


    def collapsed(self, item):
        item.setPixmap(0, QPixmap(self.folderClosed))

        
    def hardwareObjectClicked(self, item):
        try:
            #item could be None
            name = str(item.text(2))
        except:
            return
        else:
            if len(name) == 0:
                return
        
        if item.isOn() and not self.itemStates[name]:
            _instance.loadHardwareObject(name)
        elif not item.isOn() and self.itemStates[name]:
            _instance.discardHardwareObject(name)

        self.itemStates[name] = item.isOn()
        

    def hardwareObjectLoaded(self, name):
        child = self.hardwareObjectsTree.firstChild()
        
        while child:
            if str(child.text(2)) == name:
                child.setOn(True)
                self.itemStates[name] = True
                break

            child = child.firstChild() or child.nextSibling() or child.parent().nextSibling()
      

    def hardwareObjectDiscarded(self, name):
        child = self.hardwareObjectsTree.firstChild()
        
        while child:
            if str(child.text(2)) == name:
                child.setOn(False)
                self.itemStates[name] = False
                break

            child = child.firstChild() or child.nextSibling() or child.parent().nextSibling()
        

    def fill(self):
        #
        # fill Hardware Objects tree
        #
        self.treeNodes = {}
        self.itemStates = {}

        self.hardwareObjectsTree.clear()
        self.root = QListViewItem(self.hardwareObjectsTree, 'Hardware Repository')

        if _instance is not None:
            filesgen = _instance.getHardwareRepositoryFiles()
            
            for name, file in filesgen:
                #
                # every name begins with '/'
                #
                dirnames = name.split('/')[1:]
                objectName = dirnames.pop()

                parent = self.root
                for dir in dirnames:
                    if dir in self.treeNodes:
                        parent = self.treeNodes[dir]
                    else:
                        newNode =  QListViewItem(parent, dir)
                        self.treeNodes[dir] = newNode
                        newNode.setPixmap(0, QPixmap(self.folderClosed))
                        parent = newNode

                newLeaf = QCheckListItem(parent, objectName, QCheckListItem.CheckBox)
                newLeaf.setText(2, name)
                    
                if _instance.hasHardwareObject(name):
                    newLeaf.setOn(True)
                    self.itemStates[name] = True

                    if _instance.isDevice(name):
                        newLeaf.setText(1, 'Device')
                    elif _instance.isEquipment(name):
                        newLeaf.setText(1, 'Equipment')
                    elif _instance.isProcedure(name):
                        newLeaf.setText(1, 'Procedure')
                else:
                    self.itemStates[name] = False
                        
            self.root.setOpen(True)
            self.hardwareObjectsTree.sort()
        else:
            logging.getLogger('HWR').error('Cannot get Hardware Repository files : not connected to server.')
