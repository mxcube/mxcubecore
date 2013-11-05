from Sample import  *

class Container(Component):
    """
    Entity class holding state of any any hierarchical sample container
    """
    
    def __init__(self,type,container, address, scannable):
        super(Container, self).__init__(container, address, scannable)
        self.type = type
        self.components = []     
    
    
    #########################           PUBLIC           #########################
    
    def getType(self):
        """
        Returns a desctiption of the type of container
        Known types:
        -    Puck
        -    Vial
        -    Plate
        -    Well
        -    SC3
        -    PlateSupport
        -    GRob        
        :rtype: str
        """        
        return self.type

    def getComponents(self):
        """
        Returns the list of components of this container
        :rtype: list 
        """        
        return self.components
    
    def getNumberOfComponents(self):
        return len(self.components)

    def getSampleList(self):
        """
        Returns the list of all Sample objects under of this container (recursivelly)
        :rtype: list 
        """        
        samples=[]
        for c in self.getComponents():
            if isinstance(c,Sample):
                samples.append(c)
            else:
                samples.extend(c.getSampleList())
        return samples

    def getPresentSamples(self):
        """
        Returns the list of all Sample objects under of this container (recursivelly) tagged as present
        :rtype: list 
        """        
        ret = []
        for sample in self.getSampleList():
            if sample.isPresent():
                ret.append(sample)

    def isEmpty(self):
        """
        Returns true if there is no sample present sample under this container
        :rtype: bool 
        """        
        for s in self.getSampleList():
            if s.isPresent():
                return False
        return True

    def getComponentByAddress(self, address):
        """
        Returns a component through its slot address or None if address is invalid
        :rtype: Component 
        """        
        for c in self.getComponents():
            if c.getAddress() == address:
                return c            
            if isinstance(c,Container):
                aux=c.getComponentByAddress(address)
                if aux is not None:
                    return aux
        return None

    def hasComponentAddress(self, address):
        """
        Returns if has a component with a given address
        :rtype: bool 
        """        
        return self.getComponentByAddress(address) is not None

    def getComponentById(self, id):
        """
        Returns a component through its id or None if id is invalid
        :rtype: Component 
        """        
        for c in self.getComponents():
            if c.getID() == id:
                return c            
            if  isinstance(c,Container):
                aux=c.getComponentById(id)
                if aux is not None:
                    return aux
        return None


    def hasComponentId(self, id):
        """
        Returns if has a component with a given ID
        :rtype: bool 
        """        
        return self.getComponentById(id) is not None
    
    def getSelectedSample(self):
        for s in self.getSampleList():
            if s.isSelected():
                return s
        return None
        
    def getSelectedComponent(self):
        for c in self.getComponents():
            if c.isSelected():
                return c
        return None            

    def clearInfo(self):
        Component._resetDirty(self)
        for c in self.getComponents():
            c.clearInfo()  	
    
    #########################           PROTECTED           #########################
    
    def _addComponent(self, c):
        self.components.append(c)

    def _removeComponent(self, c):
        self.components.remove(c)

    def _clearComponents(self):
        self.components = []     

    def _resetDirty(self):
        Component._resetDirty(self)
        for c in self.getComponents():
            c._resetDirty()  

    def _setSelectedSample(self,sample):
        for s in self.getSampleList():
            if s==sample:
                s._setSelected(True)
            else:
                s._setSelected(False)
    
    def _setSelectedComponent(self, component):
        if component is None:
          for c in self.getComponents():
            c._setSelected(False)
        else:
          component._setSelected(True)
    
                
    def _setSelected(self, selected):
        if not selected:
            for c in self.getComponents():
                c._setSelected(False)        
        Component._setSelected(self, selected)
        
