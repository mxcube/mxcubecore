from qt import *
from HardwareRepository import HardwareRepository
from .dispatcher import *

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

        dispatcher.connect(self.hardwareObjectLoaded, 'hardwareObjectLoaded', HardwareRepository())
        dispatcher.connect(self.hardwareObjectDiscarded, 'hardwareObjectDiscarded', HardwareRepository())
        

    def expanded(self, item):
        item.setPixmap(0, QPixmap(self.folderOpened))


    def collapsed(self, item):
        item.setPixmap(0, QPixmap(self.folderClosed))

        
    def hardwareObjectClicked(self, item):
        _instance = HardwareRepository()

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
        _instance = HardwareRepository()

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
