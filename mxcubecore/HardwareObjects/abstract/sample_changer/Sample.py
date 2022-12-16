import sys
from .Component import Component

try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen


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
        self._has_been_loaded = False
        self._leaf = True

    #########################           PUBLIC           #########################

    def is_loaded(self):
        """
        Returns if the sample is currently loaded for data collection
        :rtype: bool
        """
        return self.loaded

    def has_been_loaded(self):
        """
        Returns if the sample has already beenloaded for data collection
        :rtype: bool
        """
        return self._has_been_loaded

    def get_properties(self):
        """
        Returns a dictionary with sample changer specific sample properties
        :rtype: dictionary
        """
        return self.properties

    def has_property(self, name):
        """
        Returns true if a property is defined
        :rtype: bool
        """
        return name in self.properties

    def get_property(self, name):
        """
        Returns a given property or None if not defined
        :rtype: object
        """
        if not self.has_property(name):
            return None

        return self.properties[name]

    def fetch_image(self):
        try:
            if self.has_property(self.__IMAGE_URL_PROPERTY__):
                img_url = self.get_property(self.__IMAGE_URL_PROPERTY__)
                if len(img_url) == 0:
                    return None

                f = urlopen(img_url)
                img = f.read()
                return img
        except Exception:
            print((sys.exc_info()[1]))

    def clear_info(self):
        Component.clear_info(self)
        changed = False
        if self.loaded:
            self.loaded = False
            changed = True
        if self._has_been_loaded:
            self._has_been_loaded = False
            changed = True
        if changed:
            self._set_dirty()

    # Common properties
    def get_holder_length(self):
        return self.get_property(self.__HOLDER_LENGTH_PROPERTY__)

    def _set_holder_length(self, value):
        self._set_property(self.__HOLDER_LENGTH_PROPERTY__, value)

    def _set_image_x(self, value):
        self._set_property(self.__IMAGE_X_PROPERTY__, value)

    def get_image_x(self):
        return self.get_property(self.__IMAGE_X_PROPERTY__)

    def _set_image_y(self, value):
        self._set_property(self.__IMAGE_Y_PROPERTY__, value)

    def get_image_y(self):
        return self.get_property(self.__IMAGE_Y_PROPERTY__)

    def _set_image_url(self, value):
        if (value is not None) and (value.startswith("http://")):
            value = "https://" + value[7]
        self._set_property(self.__IMAGE_URL_PROPERTY__, value)

    def get_image_url(self):
        return self.get_property(self.__IMAGE_URL_PROPERTY__)

    def _set_info_url(self, value):
        self._set_property(self.__INFO_URL_PROPERTY__, value)

    def get_info_url(self):
        return self.get_property(self.__INFO_URL_PROPERTY__)

    #########################           PROTECTED           #########################

    def _set_loaded(self, loaded, has_been_loaded=None):
        changed = False
        if self.loaded != loaded:
            self.loaded = loaded
            changed = True
        if has_been_loaded is None:
            if loaded:
                has_been_loaded = True
        if self._has_been_loaded != has_been_loaded:
            self._has_been_loaded = has_been_loaded
            changed = True
        if changed:
            self._set_dirty()

    def _set_property(self, name, value):
        if (not self.has_property(name)) or (self.get_property(name) != value):
            self._set_dirty()
        self.properties[name] = value

    def _reset_property(self, name, value):
        if self.has_property(name):
            self.properties.pop(name)
            self._set_dirty()
