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

    def get_name(self):
        return self._name

    def get_id(self):
        """
        Returns an unique ID of an element - typically scanned from the real object
        Can be None if sample is unknown or not present
        :rtype: str
        """
        return self.id

    def get_address(self):
        """
        Returns an unique identifier of the slot of the element ()
        Can never be None - even if the component is not present
        :rtype: str
        """
        return self.address

    def get_coords(self):
        coords_list = [self.get_index() + 1]
        x = self.get_container()
        while x:
            idx = x.get_index()
            if idx is not None:
                coords_list.append(idx + 1)
            x = x.get_container()
        coords_list.reverse()
        return tuple(coords_list)

    def get_index(self):
        """
        Returns the index of the object within the parent's component list,
        :rtype: int
        """
        try:
            container = self.get_container()
            if container is not None:
                components = container.get_components()
                for i in range(len(components)):
                    if components[i] is self:
                        return i
        except Exception:
            return -1

    def is_leaf(self):
        return self._leaf

    def is_present(self):
        """
        Returns true if the element is known to be currently present
        :rtype: bool
        """
        return self.present

    def is_selected(self):
        """
        Returns if the element is currently selected
        :rtype: bool
        """
        return self.selected

    def is_scanned(self):
        """
        Returns if the element has been scanned for ID (for scannable components)
        :rtype: bool
        """
        if self.is_scannable() == False:
            return False
        return self.scanned

    def is_scannable(self):
        """
        Returns if the element can be scanned for ID
        :rtype: bool
        """
        return self.scannable

    def assert_is_scannable(self):
        if not self.is_scannable():
            raise "Element is not scannable"

    def get_container(self):
        """
        Returns the parent of this element
        :rtype: Container
        """
        return self.container

    def get_siblings(self):
        """
        Returns the parent of this element
        :rtype: Container
        """
        ret = []
        if self.get_container() is not None:
            for c in self.get_container().get_components():
                if c != self:
                    ret.append(c)
        return ret

    def clear_info(self):
        """
        Clears all sample info (also in components if object is a container)
        """
        changed = False
        if self.id is not None:
            self.id = None
            changed = True
        if self.present:
            self.present = False
            changed = True
        if self.scanned:
            self.scanned = False
            changed = True
        if changed:
            self._set_dirty()

    #########################           PROTECTED           #########################
    def _set_info(self, present=False, id=None, scanned=False):
        changed = False
        if self.id != id:
            self.id = id
            changed = True
        if self.id:
            present = True
        if self.present != present:
            self.present = present
            changed = True
        if self.is_scannable() == False:
            scanned = False
        if self.scanned != scanned:
            self.scanned = scanned
            changed = True
        if changed:
            self._set_dirty()

    def _set_selected(self, selected):
        if selected:
            for c in self.get_siblings():
                c._set_selected(False)
            if self.get_container() is not None:
                self.get_container()._set_selected(True)
        self.selected = selected

    def _is_dirty(self):
        return self.dirty

    def _set_dirty(self):
        self.dirty = True
        container = self.get_container()
        if container is not None:
            container._set_dirty()

    def _reset_dirty(self):
        self.dirty = False
