from .Component import Component
from .Sample import Sample


class Container(Component):
    """
    Entity class holding state of any any hierarchical sample container
    """

    def __init__(self, type, container, address, scannable):
        super(Container, self).__init__(container, address, scannable)
        self.type = type
        self.components = []

    #########################           PUBLIC           #########################

    def get_type(self):
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

    def get_components(self):
        """
        Returns the list of components of this container
        :rtype: list
        """
        return self.components

    def get_number_of_components(self):
        return len(self.components)

    def get_sample_list(self):
        """
        Returns the list of all Sample objects under of this container (recursivelly)
        :rtype: list
        """
        samples = []
        for c in self.get_components():
            if isinstance(c, Sample):
                samples.append(c)
            else:
                samples.extend(c.get_sample_list())
        return samples

    def get_basket_list(self):
        basket_list = []
        for basket in self.components:
            if isinstance(basket, Basket):
                basket_list.append(basket)
        return basket_list

    def get_present_samples(self):
        """
        Returns the list of all Sample objects under of this container (recursivelly) tagged as present
        :rtype: list
        """
        ret = []
        for sample in self.get_sample_list():
            if sample.is_present():
                ret.append(sample)

    def is_empty(self):
        """
        Returns true if there is no sample present sample under this container
        :rtype: bool
        """
        for s in self.get_sample_list():
            if s.is_present():
                return False
        return True

    def get_component_by_address(self, address):
        """
        Returns a component through its slot address or None if address is invalid
        :rtype: Component
        """
        for c in self.get_components():
            if c.get_address() == address:
                return c
            if isinstance(c, Container):
                aux = c.get_component_by_address(address)
                if aux is not None:
                    return aux
        return None

    def has_component_address(self, address):
        """
        Returns if has a component with a given address
        :rtype: bool
        """
        return self.get_component_by_address(address) is not None

    def get_component_by_id(self, id):
        """
        Returns a component through its id or None if id is invalid
        :rtype: Component
        """
        for c in self.get_components():
            if c.get_id() == id:
                return c
            if isinstance(c, Container):
                aux = c.get_component_by_id(id)
                if aux is not None:
                    return aux
        return None

    def has_component_id(self, id):
        """
        Returns if has a component with a given ID
        :rtype: bool
        """
        return self.get_component_by_id(id) is not None

    def get_selected_sample(self):
        for s in self.get_sample_list():
            if s.is_selected():
                return s
        return None

    def get_selected_component(self):
        for c in self.get_components():
            if c.is_selected():
                return c
        return None

    def clear_info(self):
        Component._reset_dirty(self)
        for c in self.get_components():
            c.clear_info()

    #########################           PROTECTED           #########################

    def _add_component(self, c):
        self.components.append(c)

    def _remove_component(self, c):
        self.components.remove(c)

    def _clear_components(self):
        self.components = []

    def _reset_dirty(self):
        Component._reset_dirty(self)
        for c in self.get_components():
            c._reset_dirty()

    def _set_selected_sample(self, sample):
        for s in self.get_sample_list():
            if s == sample:
                s._set_selected(True)
            else:
                s._set_selected(False)

    def _set_selected_component(self, component):
        if component is None:
            for c in self.get_components():
                c._set_selected(False)
        else:
            component._set_selected(True)

    def _set_selected(self, selected):
        if not selected:
            for c in self.get_components():
                c._set_selected(False)
        Component._set_selected(self, selected)


class Basket(Container):
    __TYPE__ = "Puck"

    def __init__(self, container, number, samples_num=10, name="Puck"):
        super(Basket, self).__init__(
            self.__TYPE__, container, Basket.get_basket_address(number), True
        )

        self._name = name
        self.samples_num = samples_num
        for i in range(samples_num):
            slot = Pin(self, number, i + 1)
            self._add_component(slot)

    @staticmethod
    def get_basket_address(basket_number):
        return str(basket_number)

    def get_number_of_samples(self):
        return self.samples_num

    def clear_info(self):
        # self.get_container()._reset_basket_info(self.get_index()+1)
        self.get_container()._trigger_info_changed_event()


class Pin(Sample):
    STD_HOLDERLENGTH = 22.0

    def __init__(self, basket, basket_no, sample_no):
        super(Pin, self).__init__(
            basket, Pin.get_sample_address(basket_no, sample_no), False
        )
        self._set_holder_length(Pin.STD_HOLDERLENGTH)

    def get_basket_no(self):
        return self.get_container().get_index() + 1

    def get_vial_no(self):
        return self.get_index() + 1

    @staticmethod
    def get_sample_address(basket_number, sample_number):
        return "%s:%02d"  % (basket_number, sample_number)
