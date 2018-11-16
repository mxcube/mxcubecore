class Component(object):
    """
    Entity class representing any a sample or sample container
    """

    def __init__(self, container, address, scannable):
        self.container = container
        self.address = address
        self.scannable = scannable
        self.id = None
        self.present = False
        self.selected = False
        self.scanned = False
        self.dirty = False
        self._leaf = False
        self._name = ""

    #########################           PUBLIC           #########################

    def getName(self):
        return self._name

    def getID(self):
        """
        Returns an unique ID of an element - typically scanned from the real object
        Can be None if sample is unknown or not present
        :rtype: str
        """
        return self.id

    def getAddress(self):
        """
        Returns an unique identifier of the slot of the element ()
        Can never be None - even if the component is not present 
        :rtype: str
        """
        return self.address

    def getCoords(self):
        coords_list = [self.getIndex() + 1]
        x = self.getContainer()
        while x:
            idx = x.getIndex()
            if idx is not None:
                coords_list.append(idx + 1)
            x = x.getContainer()
        coords_list.reverse()
        return tuple(coords_list)

    def getIndex(self):
        """
        Returns the index of the object within the parent's component list,
        :rtype: int
        """
        try:
            container = self.getContainer()
            if container is not None:
                components = container.getComponents()
                for i in range(len(components)):
                    if components[i] is self:
                        return i
        except:
            return -1

    def isLeaf(self):
        return self._leaf

    def isPresent(self):
        """
        Returns true if the element is known to be currently present 
        :rtype: bool
        """
        return self.present

    def isSelected(self):
        """
        Returns if the element is currently selected
        :rtype: bool
        """
        return self.selected

    def isScanned(self):
        """
        Returns if the element has been scanned for ID (for scannable components) 
        :rtype: bool
        """
        if self.isScannable() == False:
            return False
        return self.scanned

    def isScannable(self):
        """
        Returns if the element can be scanned for ID
        :rtype: bool
        """
        return self.scannable

    def assertIsScannable(self):
        if not self.isScannable():
            raise "Element is not scannable"

    def getContainer(self):
        """
        Returns the parent of this element
        :rtype: Container
        """
        return self.container

    def getSiblings(self):
        """
        Returns the parent of this element
        :rtype: Container
        """
        ret = []
        if self.getContainer() is not None:
            for c in self.getContainer().getComponents():
                if c != self:
                    ret.append(c)
        return ret

    def clearInfo(self):
        """
        Clears all sample info (also in components if object is a container)
        """
        changed = False
        if self.id != None:
            self.id = None
            changed = True
        if self.present:
            self.present = False
            changed = True
        if self.scanned:
            self.scanned = False
            changed = True
        if changed:
            self._setDirty()

    #########################           PROTECTED           #########################
    def _setInfo(self, present=False, id=None, scanned=False):
        changed = False
        if self.id != id:
            self.id = id
            changed = True
        if self.id:
            present = True
        if self.present != present:
            self.present = present
            changed = True
        if self.isScannable() == False:
            scanned = False
        if self.scanned != scanned:
            self.scanned = scanned
            changed = True
        if changed:
            self._setDirty()

    def _setSelected(self, selected):
        if selected:
            for c in self.getSiblings():
                c._setSelected(False)
            if self.getContainer() is not None:
                self.getContainer()._setSelected(True)
        self.selected = selected

    def _isDirty(self):
        return self.dirty

    def _setDirty(self):
        self.dirty = True
        container = self.getContainer()
        if container is not None:
            container._setDirty()

    def _resetDirty(self):
        self.dirty = False
