from Component import *
import sys


class Sample(Component):
    """
    Entity class holding state of an individual sample or sample slot (an empty sample location).
    """

    # Common properties
    __HOLDER_LENGTH_PROPERTY__ = "Length"
    __IMAGE_URL_PROPERTY__ = "Image"
    __IMAGE_X_PROPERTY__ = "X"
    __IMAGE_Y_PROPERTY__ = "Y"
    __INFO_URL_PROPERTY__ = "Info"

    def __init__(self, container, address, scannable):
        super(Sample, self).__init__(container, address, scannable)
        self.properties = {}
        self.loaded = False
        self.has_been_loaded = False
        self._leaf = True

    # ########################    PUBLIC    #########################

    def isLoaded(self):
        """
        Returns if the sample is currently loaded for data collection
        :rtype: bool
        """
        return self.loaded

    def hasBeenLoaded(self):
        """
        Returns if the sample has already beenloaded for data collection
        :rtype: bool
        """
        return self.has_been_loaded

    def getProperties(self):
        """
        Returns a dictionary with sample changer specific sample properties
        :rtype: dictionary
        """
        return self.properties

    def hasProperty(self, name):
        """
        Returns true if a property is defined
        :rtype: bool
        """
        return name in self.properties

    def getProperty(self, name):
        """
        Returns a given property or None if not defined
        :rtype: object
        """
        if not self.hasProperty(name):
            return None

        return self.properties[name]

    def fetchImage(self):
        try:
            if self.hasProperty(self.__IMAGE_URL_PROPERTY__):
                img_url = self.getProperty(self.__IMAGE_URL_PROPERTY__)
                if len(img_url) == 0:
                    return None
                import urllib

                f = urllib.urlopen(img_url)
                img = f.read()
                return img
        except BaseException:
            print(sys.exc_info()[1])

    def clearInfo(self):
        Component.clearInfo(self)
        changed = False
        if self.loaded:
            self.loaded = False
            changed = True
        if self.has_been_loaded:
            self.has_been_loaded = False
            changed = True
        if changed:
            self._setDirty()

    # Common properties
    def getHolderLength(self):
        return self.getProperty(self.__HOLDER_LENGTH_PROPERTY__)

    def _setHolderLength(self, value):
        self._setProperty(self.__HOLDER_LENGTH_PROPERTY__, value)

    def _setImageX(self, value):
        self._setProperty(self.__IMAGE_X_PROPERTY__, value)

    def getImageX(self):
        return self.getProperty(self.__IMAGE_X_PROPERTY__)

    def _setImageY(self, value):
        self._setProperty(self.__IMAGE_Y_PROPERTY__, value)

    def getImageY(self):
        return self.getProperty(self.__IMAGE_Y_PROPERTY__)

    def _setImageURL(self, value):
        if (value is not None) and (value.startswith("http://")):
            value = "https://" + value[7]
        self._setProperty(self.__IMAGE_URL_PROPERTY__, value)

    def getImageURL(self):
        return self.getProperty(self.__IMAGE_URL_PROPERTY__)

    def _setInfoURL(self, value):
        self._setProperty(self.__INFO_URL_PROPERTY__, value)

    def getInfoURL(self):
        return self.getProperty(self.__INFO_URL_PROPERTY__)

    # ########################    PROTECTED    #########################

    def _setLoaded(self, loaded, has_been_loaded=None):
        changed = False
        if self.loaded != loaded:
            self.loaded = loaded
            changed = True
        if has_been_loaded is None:
            if loaded:
                has_been_loaded = True
        if self.has_been_loaded != has_been_loaded:
            self.has_been_loaded = has_been_loaded
            changed = True
        if changed:
            self._setDirty()

    def _setProperty(self, name, value):
        if (not self.hasProperty(name)) or (self.getProperty(name) != value):
            self._setDirty()
        self.properties[name] = value

    def _resetProperty(self, name, value):
        if self.hasProperty(name):
            self.properties.pop(name)
            self._setDirty()
