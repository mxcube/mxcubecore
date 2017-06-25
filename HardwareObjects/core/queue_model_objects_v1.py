"""
This module contain objects that combined make up the data model.
Any object that inherhits from TaskNode can be added to and handled by
the QueueModel.
"""
import copy
import os
import logging
import queue_model_enumerables_v1 as queue_model_enumerables

class TaskNode(object):
    """
    Objects that inherit TaskNode can be added to and handled by
    the QueueModel object.
    """

    def __init__(self):
        object.__init__(self)

        self._children = []
        self._name = str()
        self._number = 0
        self._executed = False
        self._running = False
        self._parent = None
        self._names = {}
        self._enabled = True
        self._node_id = None
        self._requires_centring = True

    def is_enabled(self):
        """
        :returns: True if enabled and False if disabled
        """
        return self._enabled

    def set_enabled(self, state):
        """
        Sets the enabled state, True represents enabled (executable)
        and false disabled (not executable).

        :param state: The state, True or False
        :type state: bool
        """
        self._enabled = state

    def get_children(self):
        """
        :returns: The children of this node.
        :rtype: List of TaskNode objects.
        """
        return self._children

    def get_parent(self):
        """
        :returns: The parent of this node.
        :rtype: TaskNode
        """
        return self._parent

    def set_name(self, name):
        """
        Sets the name.

        :param name: The new name.
        :type name: str

        :returns: none
        """
        if self.get_parent():
            self._set_name(str(name))
        else:
            self._name = str(name)

    def set_number(self, number):
        """
        Sets the number of this node. The number can be used
        to give the task a unique number when for instance,
        the name is not unique for this node.

        :param number: number
        :type number: int
        """
        self._number = int(number)

        if self.get_parent():
            # Bumb the run number for nodes with this name
            if self.get_parent()._names[self._name] < number:
                self.get_parent()._names[self._name] = number

    def _set_name(self, name):
        if name in self.get_parent()._names:
            if self.get_parent()._names[name] < self._number:
                self.get_parent()._names[name] = self._number
            else:
                self.get_parent()._names[name] += 1
        else:
            self.get_parent()._names[name] = self._number

        self._name = name

    def get_name(self):
        return '%s - %i' % (self._name, self._number)

    def get_next_number_for_name(self, name):
        num = self._names.get(name)

        if num:
            num += 1
        else:
            num = 1

        return num

    def get_full_name(self):
        name_list = [self.get_name()]
        parent = self._parent

        while(parent):
            name_list.append(parent.get_name())
            parent = parent._parent

        return name_list

    def get_display_name(self):
        return self.get_name()

    def get_path_template(self):
        return None

    def get_files_to_be_written(self):
        return []

    def get_centred_positions(self):
        return []

    def set_centred_positions(self, cp):
        pass

    def is_executed(self):
        return self._executed

    def set_executed(self, executed):
        self._executed = executed

    def is_running(self):
        # IK maybe replace is_executed and is_running with state?
        return self._running

    def set_running(self, running):
        self._running = running

    def requires_centring(self):
        return self._requires_centring

    def set_requires_centring(self, state):
        self._requires_centring = state

    def get_root(self):
        parent = self._parent
        root = self

        if parent:
            while(parent):
                root = parent
                parent = parent._parent

        return root

    def copy(self):
        new_node = copy.deepcopy(self)
        return new_node

    def __repr__(self):
        s = '<%s object at %s>' % (
             self.__class__.__name__,
             hex(id(self)))

        return s

    def set_snapshot(self, snapshot):
        pass


class RootNode(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)
        self._name = 'root'
        self._total_node_count = 0


class TaskGroup(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)
        self.lims_group_id = None
        self.interleave_num_images = None

    def set_name_from_task(self, task):
        if isinstance(task, DataCollection):
            self._name = "Standard"

class Sample(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)

        self.code = str()
        self.lims_code = str()
        self.holder_length = 22.0
        self.lims_id = -1
        self.name = str()
        self.lims_sample_location = -1
        self.lims_container_location = -1
        self.free_pin_mode = False
        self.loc_str = str()
        self.diffraction_plan = None

        # A pair <basket_number, sample_number>
        self.location = (None, None)
        #self.location_plate = (None, None, None)
        self.lims_location = (None, None)

        # Crystal information
        self.crystals = [Crystal()]
        self.processing_parameters = ProcessingParameters()
        self.processing_parameters.num_residues = 200
        self.processing_parameters.process_data = True
        self.processing_parameters.anomalous = False
        self.processing_parameters.pdb_code = None
        self.processing_parameters.pdb_file = str()

        self.energy_scan_result = EnergyScanResult()

    def __str__(self):
        s = '<%s object at %s>' % (
            self.__class__.__name__,
            hex(id(self)))
        return s

    def _print(self):
        print ("sample: %s" % self.loc_str)

    def has_lims_data(self):
        if self.lims_id > -1:
            return True
        else:
            return False

    def get_name(self):
        return self._name

    def get_display_name(self):
        name = self.name
        acronym = self.crystals[0].protein_acronym

        if self.name is not '' and acronym is not '':
            display_name = acronym + '-' + name
        else:
            display_name = self.get_name()

        if self.lims_code:
            display_name += " (%s)" % self.lims_code            

        return display_name

    def init_from_sc_sample(self, sc_sample):
        self.loc_str = ":".join(map(str,sc_sample[-1]))
        self.location = sc_sample[-1]
        self.set_name(self.loc_str)
        if sc_sample[3] != "":
            self.set_name(sc_sample[3])
        else:
            self.set_name(self.loc_str)


    def init_from_plate_sample(self, plate_sample):
        """
        location : col, row, index
        """
        self.loc_str = "%s:%s:%s" %(chr(65 + int(plate_sample[1])),
                                    str(plate_sample[2]),
                                    str(plate_sample[3]))
        self.location = (int(plate_sample[1]), int(plate_sample[2]), int(plate_sample[3]))
        self.location_plate = plate_sample[5]
        self.set_name(self.loc_str)

    def init_from_lims_object(self, lims_sample):
        if hasattr(lims_sample, 'cellA'):
            self.crystals[0].cell_a = lims_sample.cellA
            self.processing_parameters.cell_a = lims_sample.cellA

        if hasattr(lims_sample, 'cellAlpha'):
            self.crystals[0].cell_alpha = lims_sample.cellAlpha
            self.processing_parameters.cell_alpha = lims_sample.cellAlpha

        if hasattr(lims_sample, 'cellB'):
            self.crystals[0].cell_b = lims_sample.cellB
            self.processing_parameters.cell_b = lims_sample.cellB

        if hasattr(lims_sample, 'cellBeta'):
            self.crystals[0].cell_beta = lims_sample.cellBeta
            self.processing_parameters.cell_beta = lims_sample.cellBeta

        if hasattr(lims_sample, 'cellC'):
            self.crystals[0].cell_c = lims_sample.cellC
            self.processing_parameters.cell_c = lims_sample.cellC

        if hasattr(lims_sample, 'cellGamma'):
            self.crystals[0].cell_gamma = lims_sample.cellGamma
            self.processing_parameters.cell_gamma = lims_sample.cellGamma

        if hasattr(lims_sample, 'proteinAcronym'):
            self.crystals[0].protein_acronym = lims_sample.proteinAcronym
            self.processing_parameters.protein_acronym = lims_sample.proteinAcronym

        if hasattr(lims_sample, 'crystalSpaceGroup'):
            self.crystals[0].space_group = lims_sample.crystalSpaceGroup
            self.processing_parameters.space_group = lims_sample.crystalSpaceGroup

        if hasattr(lims_sample, 'code'):
            self.lims_code = lims_sample.code
            logging.getLogger("lism_code:%s" %self.lims_code)
        else:
            logging.getLogger("No code found from LIMS for this sample")

        if hasattr(lims_sample, 'holderLength'):
            self.holder_length = lims_sample.holderLength

        if hasattr(lims_sample, 'sampleId'):
            self.lims_id = lims_sample.sampleId

        if hasattr(lims_sample, 'sampleName'):
            self.name = str(lims_sample.sampleName)

        if hasattr(lims_sample, 'containerSampleChangerLocation') and\
                hasattr(lims_sample, 'sampleLocation'):

            if lims_sample.containerSampleChangerLocation and \
                    lims_sample.sampleLocation:

                self.lims_sample_location = int(lims_sample.sampleLocation)
                self.lims_container_location = \
                    int(lims_sample.containerSampleChangerLocation)

                l = (int(lims_sample.containerSampleChangerLocation),
                     int(lims_sample.sampleLocation))

                self.lims_location = l
                self.location = l

                self.loc_str = str(str(self.lims_location[0]) +\
                                   ':' + str(self.lims_location[1]))

        if hasattr(lims_sample, 'diffractionPlan'):
            self.diffraction_plan = lims_sample.diffractionPlan

        name = ''

        if self.crystals[0].protein_acronym:
            name += self.crystals[0].protein_acronym

        if self.name:
            name += '-' + self.name

        self.set_name(name)

    def get_processing_parameters(self):
        processing_params = ProcessingParameters()
        processing_params.space_group = self.crystals[0].space_group
        processing_params.cell_a = self.crystals[0].cell_a
        processing_params.cell_alpha = self.crystals[0].cell_alpha
        processing_params.cell_b = self.crystals[0].cell_b
        processing_params.cell_beta = self.crystals[0].cell_beta
        processing_params.cell_c = self.crystals[0].cell_c
        processing_params.cell_gamma = self.crystals[0].cell_gamma
        processing_params.protein_acronym = self.crystals[0].protein_acronym

        return processing_params


class Basket(TaskNode):
    """
    Class represents a basket in the tree. It has not task assigned.
    It represents a parent for samples with the same basket id.
    """
    def __init__(self):
        TaskNode.__init__(self)
        self.name = str()
        self.location = None
        self.free_pin_mode = False
        self.sample_list = []

    @property
    def is_present(self):
        return self.get_is_present()

    def init_from_sc_basket(self, sc_basket, name="Puck"):
        self._basket_object = sc_basket[1] #self.is_present = sc_basket[2]

        if name == 'Row' or self._basket_object is None:
            self.location = sc_basket[0]
            if name == "Row":
                self.name = "%s %s" % (name, chr(65 + self.location))
            else:
                self.name = "%s %d" % (name, self.location)
        else:
            self.location = self._basket_object.getCoords()
            if len(self.location) == 2:
                self.name = "Cell %d, puck %d" % self.location
            elif len(self.location) == 1:
                self.name = "%s %s" % (name, self.location[0])
            else:
                self.name = "%s %s" % (name, self.location)

    def get_name(self):
        return self.name

    def get_location(self):
        return self.location 

    def get_is_present(self):
        return self._basket_object.present

    def clear_sample_list(self):
        self.sample_list = []

    def add_sample(self, sample):
        self.sample_list.append(sample) 

    def get_sample_list(self):
        return self.sample_list


class DataCollection(TaskNode):
    """
    Adds the child node <child>. Raises the exception TypeError
    if child is not of type TaskNode.

    Moves the child (reparents it) if it already has a parent.

    :param parent: Parent TaskNode object.
    :type parent: TaskNode

    :param acquisition_list: List of Acquisition objects.
    :type acquisition_list: list

    :crystal: Crystal object
    :type crystal: Crystal

    :param processing_paremeters: Parameters used by autoproessing software.
    :type processing_parameters: ProcessingParameters

    :returns: None
    :rtype: None
    """
    def __init__(self, acquisition_list=None, crystal=None,
                 processing_parameters=None, name=''):
        TaskNode.__init__(self)

        if not acquisition_list:
            acquisition_list = [Acquisition()]

        if not crystal:
            crystal = Crystal()

        if not processing_parameters:
            processing_parameters = ProcessingParameters()

        self.acquisitions = acquisition_list
        self.crystal = crystal
        self.processing_parameters = processing_parameters
        self.set_name(name)

        self.previous_acquisition = None
        self.experiment_type = queue_model_enumerables.EXPERIMENT_TYPE.NATIVE
        self.html_report = str()
        self.id = int()
        self.lims_group_id = None
        self.run_processing_after = None
        self.run_processing_parallel = None
        self.grid = None

        self.parallel_processing_result = None        

    def as_dict(self):

        acq = self.acquisitions[0]
        path_template = acq.path_template
        parameters = acq.acquisition_parameters

        return {'prefix': path_template.get_prefix(),
                'run_number': path_template.run_number,
                'first_image': parameters.first_image,
                'num_images': parameters.num_images,
                'osc_start': parameters.osc_start,
                'osc_range': parameters.osc_range,
                'kappa': parameters.kappa,
                'kappa_phi': parameters.kappa_phi,
                'overlap': parameters.overlap,
                'exp_time': parameters.exp_time,
                'num_passes': parameters.num_passes,
                'path': path_template.directory,
                'centred_position': parameters.centred_position,
                'energy': parameters.energy,
                'resolution': parameters.resolution,
                'transmission': parameters.transmission,
                'detector_mode': parameters.detector_mode,
                'shutterless': parameters.shutterless,
                'inverse_beam': parameters.inverse_beam,
                'sample': str(self.crystal),
                'acquisitions': str(self.acquisitions),
                'acq_parameters': str(parameters),
                'snapshot': parameters.centred_position.snapshot_image}

    def set_experiment_type(self, exp_type):
        self.experiment_type = exp_type

    def is_helical(self):
        return self.experiment_type == \
            queue_model_enumerables.EXPERIMENT_TYPE.HELICAL

    def is_mesh(self):
        return self.experiment_type == \
            queue_model_enumerables.EXPERIMENT_TYPE.MESH

    def get_name(self):
        return '%s_%i' % (self.acquisitions[0].path_template.get_prefix(),
                          self.acquisitions[0].path_template.run_number)

    def is_collected(self):
        return self.is_executed()

    def set_collected(self, collected):
        return self.set_executed(collected)

    def get_path_template(self):
        return self.acquisitions[0].path_template

    def get_files_to_be_written(self):
        path_template = self.acquisitions[0].path_template
        file_locations = path_template.get_files_to_be_written()

        return file_locations

    def get_centred_positions(self):
        centred_pos = []
        for pos in self.acquisitions:
             centred_pos.append(pos.acquisition_parameters.centred_position)
        return centred_pos

        #return [self.acquisitions[0].acquisition_parameters.centred_position]

    def set_centred_positions(self, cp):
        self.acquisitions[0].acquisition_parameters.centred_position = cp

    def __str__(self):
        s = '<%s object at %s>' % (
            self.__class__.__name__,
            hex(id(self)))
        return s

    def copy(self):
        new_node = copy.deepcopy(self)
        cpos = self.acquisitions[0].acquisition_parameters.\
               centred_position

        if cpos:
            snapshot_image = self.acquisitions[0].acquisition_parameters.\
                             centred_position.snapshot_image

            if snapshot_image:
                #snapshot_image_copy = snapshot_image.copy()
                acq_parameters = new_node.acquisitions[0].acquisition_parameters
                acq_parameters.centred_position.snapshot_image = None

        return new_node

    def get_point_index(self):
        """
        Descript. : Returns point index associated to the data collection
        Args.     :
        Return    : index (integer)
        """
        cp = self.get_centred_positions()
        return cp[0].get_index()

    def get_helical_point_index(self):
        """
        Descript. : Return indexes of points associated to the helical line
        Args.     :
        Return    : index (integer), index (integer)
        """ 
        cp = self.get_centred_positions()
        return cp[0].get_index(), cp[1].get_index()

    def set_grid_id(self, grid_id):
        """
        Descript. : Sets grid id associated to the data collection
        Args.     : grid_id (integer)
        Return    : 
        """
        self.grid_id = grid_id

    def get_display_name(self):
        """
        Descript. : Returns display name depending from collection type
        Args.     :
        Return    : display_name (string)
        """
        if self.is_helical():
            start_index, end_index = self.get_helical_point_index()
            if not None in (start_index, end_index):
                display_name = "%s (Line %d:%d)" %(self.get_name(), start_index, end_index)
            else:
                display_name = self.get_name()
        elif self.is_mesh():
            #display_name = "%s (%s)" %(self.get_name(), self.grid_id)
            col, row = self.grid.get_col_row_num()
            display_name = "%s (Mesh %d: %d x %d)" %(self.get_name(),
                                                     self.grid.index + 1,
                                                     col,
                                                     row)
        else:
            index = self.get_point_index()
            if index:
                index = str(index)
            else:
                index = "not defined"
            display_name = "%s (Point %s)" %(self.get_name(), index)
        return display_name

    def get_parallel_processing_result(self):
        return self.parallel_processing_result

    def set_snapshot(self, snapshot):
        self.acquisitions[0].acquisition_parameters.\
             centred_position.snapshot_image = snapshot

class ProcessingParameters():
    def __init__(self):
        self.space_group = 0
        self.cell_a = 0
        self.cell_alpha = 0
        self.cell_b = 0
        self.cell_beta = 0
        self.cell_c = 0
        self.cell_gamma = 0
        self.protein_acronym = ""
        self.num_residues = 200
        self.process_data = True
        self.anomalous = False
        self.pdb_code = None
        self.pdb_file = str()

    def get_cell_str(self):
        return ",".join(map(str, (self.cell_a, self.cell_b,
                                  self.cell_c, self.cell_alpha,
                                  self.cell_beta, self.cell_gamma)))


class Characterisation(TaskNode):
    def __init__(self, ref_data_collection=None,
                 characterisation_parameters=None, name=''):
        TaskNode.__init__(self)

        if not characterisation_parameters:
            characterisation_parameters = CharacterisationParameters()

        if not ref_data_collection:
            ref_data_collection = DataCollection()

        self.reference_image_collection = ref_data_collection
        self.characterisation_parameters = characterisation_parameters
        self.set_name(name)

        self.html_report = None
        self.run_characterisation = True
        self.characterisation_software = None

    def get_name(self):
        return '%s_%i' % (self._name, self._number)

    def get_path_template(self):
        return self.reference_image_collection.acquisitions[0].\
               path_template

    def get_files_to_be_written(self):
        path_template = self.reference_image_collection.acquisitions[0].\
                        path_template

        file_locations = path_template.get_files_to_be_written()

        return file_locations

    def get_centred_positions(self):
        return [self.reference_image_collection.acquisitions[0].\
                acquisition_parameters.centred_position]

    def set_centred_positions(self, cp):
        self.reference_image_collection.acquisitions[0].\
            acquisition_parameters.centred_position = cp

    def copy(self):
        new_node = copy.deepcopy(self)
        new_node.reference_image_collection = self.reference_image_collection.copy()

        return new_node

    def get_point_index(self):
        """
        Descript. : Returns point index associated to the data collection
        Args.     :
        Return    : index (integer)
        """
        cp = self.get_centred_positions()
        return cp[0].get_index()

    def get_display_name(self):
        """
        Descript. : Returns display name of the collection
        Args.     :
        Return    : display_name (string)
        """
        index = self.get_point_index()
        if index:
            index = str(index)
        else:
            index = "not defined"
        display_name = "%s (Point - %s)" %(self.get_name(), index)
        return display_name

    def set_snapshot(self, snapshot):
        self.reference_image_collection.acquisitions[0].\
            acquisition_parameters.centred_position.snaphot_image = snapshot

class CharacterisationParameters(object):
    def __init__(self):
        # Setting num_ref_images to EDNA_NUM_REF_IMAGES.NONE
        # will disable characterisation.
        self.path_template = PathTemplate()
        self.experiment_type = 0

        # Optimisation parameters
        self.use_aimed_resolution = bool()
        self.aimed_resolution = float()
        self.use_aimed_multiplicity = bool()
        self.aimed_multiplicity = int()
        self.aimed_i_sigma = float()
        self.aimed_completness = float()
        self.strategy_complexity = int()
        self.induce_burn = bool()
        self.use_permitted_rotation = bool()
        self.permitted_phi_start = float()
        self.permitted_phi_end = float()
        self.low_res_pass_strat = bool()

        # Crystal
        self.max_crystal_vdim = float()
        self.min_crystal_vdim = float()
        self.max_crystal_vphi = float()
        self.min_crystal_vphi = float()
        self.space_group = ""

        # Characterisation type
        self.use_min_dose = bool()
        self.use_min_time = bool()
        self.min_dose = float()
        self.min_time = float()
        self.account_rad_damage = bool()
        self.auto_res = bool()
        self.opt_sad = bool()
        self.sad_res = float()
        self.determine_rad_params = bool()
        self.burn_osc_start = float()
        self.burn_osc_interval = int()

        # Radiation damage model
        self.rad_suscept = float()
        self.beta = float()
        self.gamma = float()

    def as_dict(self):
        return {"experiment_type": self.experiment_type,
                "use_aimed_resolution": self.use_aimed_resolution,
                "use_aimed_multiplicity": self.use_aimed_multiplicity,
                "aimed_multiplicity": self.aimed_multiplicity,
                "aimed_i_sigma": self.aimed_i_sigma,
                "aimed_completness": self.aimed_completness,
                "strategy_complexity": self.strategy_complexity,
                "induce_burn": self.induce_burn,
                "use_permitted_rotation": self.use_permitted_rotation,
                "permitted_phi_start": self.permitted_phi_start,
                "permitted_phi_end": self.permitted_phi_end,
                "low_res_pass_strat": self.low_res_pass_strat,
                "max_crystal_vdim": self.max_crystal_vdim,
                "min_crystal_vdim": self.min_crystal_vdim,
                "max_crystal_vphi": self.max_crystal_vphi,
                "min_crystal_vphi": self.min_crystal_vphi,
                "space_group": self.space_group,
                "use_min_dose": self.use_min_dose,
                "use_min_time": self.use_min_time,
                "min_dose": self.min_dose,
                "min_time": self.min_time,
                "account_rad_damage": self.account_rad_damage,
                "auto_res": self.auto_res,
                "opt_sad": self.opt_sad,
                "sad_res": self.sad_res,
                "determine_rad_params": self.determine_rad_params,
                "burn_osc_start": self.burn_osc_start,
                "burn_osc_interval": self.burn_osc_interval,
                "rad_suscept": self.rad_suscept,
                "beta": self.beta,
                "gamma": self.gamma}

    def set_from_dict(self, params_dict):
        for dict_item in params_dict.items():
            if hasattr(self, dict_item[0]):
                setattr(self, dict_item[0], dict_item[1])

    def __repr__(self):
        s = '<%s object at %s>' % (
            self.__class__.__name__,
            hex(id(self)))

        return s


class EnergyScan(TaskNode):
    def __init__(self, sample = None, path_template = None, cpos = None):
        TaskNode.__init__(self)
        self.element_symbol = None
        self.edge = None
        self.set_requires_centring(True)
        self.centred_position = cpos

        if not sample:
            self.sample = Sample()
        else:
            self.sample = sample

        if not path_template:
            self.path_template = PathTemplate()
        else:
            self.path_template = path_template

        self.result = EnergyScanResult()

    def get_run_number(self):
        return self.path_template.run_number

    def get_prefix(self):
        return self.path_template.get_prefix()

    def get_path_template(self):
        return self.path_template

    def set_scan_result_data(self, data):
        self.result.data = data

    def get_scan_result(self):
        return self.result

    def is_collected(self):
        return self.is_executed()

    def set_collected(self, collected):
        return self.set_executed(collected)

    def get_point_index(self):
        if self.centred_position:
            return self.centred_position.get_index()

    def get_display_name(self):
        index = self.get_point_index()
        if index:
            index = str(index)
        else:
            index = "not defined"
        display_name = "%s (%s %s, Point - %s)" %(self.get_name(),
                                                  self.element_symbol,
                                                  self.edge,
                                                  index)
        return display_name

    def copy(self):
        new_node = copy.deepcopy(self)
        cpos = self.centred_position
        if cpos:
            snapshot_image = self.centred_position.snapshot_image
            if snapshot_image:
                snapshot_image_copy = snapshot_image.copy()
                new_node.centred_position.snapshot_image = snapshot_image_copy
        return new_node

    def set_snapshot(self, snapshot):
        self.centred_position.snapshot_image = snapshot

class EnergyScanResult(object):
    def __init__(self):
        object.__init__(self)
        self.inflection = None
        self.peak = None
        self.first_remote = None
        self.second_remote = None
        self.data_file_path = PathTemplate()
 
        self.data = []

        self.pk = None
        self.fppPeak = None
        self.fpPeak = None
        self.ip = None
        self.fppInfl = None
        self.fpInfl = None
        self.rm = None
        self.chooch_graph_x = None
        self.chooch_graph_y1 = None
        self.chooch_graph_y2 = None
        self.title = None


class XRFSpectrum(TaskNode):
    """
    Class represents XRF spectrum task
    """ 
    def __init__(self, sample=None, path_template=None, cpos=None):
        TaskNode.__init__(self)
        self.count_time = 1
        self.set_requires_centring(True)
        self.centred_position = cpos
        self.adjust_transmission = True

        if not sample:
            self.sample = Sample()
        else:
            self.sample = sample

        if not path_template:
            self.path_template = PathTemplate()
        else:
            self.path_template = path_template

        self.result = XRFSpectrumResult()

    def get_run_number(self):
        return self.path_template.run_number

    def get_prefix(self):
        return self.path_template.get_prefix()

    def get_path_template(self):
        return self.path_template

    def get_point_index(self):
        if self.centred_position:
            return self.centred_position.get_index()

    def get_display_name(self):
        index = self.get_point_index()
        if index:
            index = str(index)
        else:
            index = "not defined"
        display_name = "%s (Point - %s)" %(self.get_name(), index)
        return display_name

    def set_count_time(self, count_time):
        self.count_time = count_time

    def is_collected(self):
        return self.is_executed()

    def set_collected(self, collected):
        return self.set_executed(collected)

    def get_spectrum_result(self):
        return self.result

    def copy(self):
        new_node = copy.deepcopy(self)
        cpos = self.centred_position
        if cpos:
            snapshot_image = self.centred_position.snapshot_image
            if snapshot_image:
                snapshot_image_copy = snapshot_image.copy()
                new_node.centred_position.snapshot_image = snapshot_image_copy
        return new_node

    def set_snaphot(self, snapshot):
        self.centred_position.snapshot_image = snapshot

class XRFSpectrumResult(object):
    def __init__(self):
        object.__init__(self)
        self.mca_data = None
        self.mca_calib = None
        self.mca_config = None

class XrayCentering(TaskNode):
    def __init__(self, ref_data_collection=None, crystal=None):
        TaskNode.__init__(self)

        self.set_requires_centring(False)
        if not ref_data_collection:
            ref_data_collection = DataCollection()

        if not crystal:
            crystal = Crystal()

        self.reference_image_collection = ref_data_collection
        self.crystal = crystal

        self.html_report = None

    def get_display_name(self):
        path_template = self.get_path_template()
        if self.reference_image_collection.grid is not None:
            grid_info = "Mesh %d" % (self.reference_image_collection.grid.index + 1)
        else:
            grid_info = "Autogrid"
        return "Xray centring (%s)" % grid_info

    def get_path_template(self):
        return self.reference_image_collection.acquisitions[0].path_template

    def get_files_to_be_written(self):
        path_template = self.reference_image_collection.acquisitions[0].path_template
        file_locations = path_template.get_files_to_be_written()
        return file_locations

    def add_task(self, task):
        pass

class SampleCentring(TaskNode):
    """Manual 3 click centering"""

    def __init__(self, name = None, kappa = None, kappa_phi = None):
        TaskNode.__init__(self)
        self._tasks = []

        if name:
            self.set_name(name)
 
        self.kappa = kappa
        self.kappa_phi = kappa_phi

    def add_task(self, task_node):
        self._tasks.append(task_node)

    def get_tasks(self):
        return self._tasks

    def get_name(self):
        return self._name

    def get_kappa(self):
        return self.kappa

    def get_kappa_phi(self):
        return self.kappa_phi

class OpticalCentring(TaskNode):
    """Optical automatic centering with lucid"""

    def __init__(self, user_confirms=False):
        TaskNode.__init__(self)

        if user_confirms:
            self.set_name("Optical automatic centring (user confirms)")
        else:
            self.set_name("Optical automatic centring")
        if user_confirms:
            self.try_count = 3
        else:
            self.try_count = 1

    def add_task(self, task_node):
        pass

    def get_name(self):
        return self._name

class Acquisition(object):
    def __init__(self):
        object.__init__(self)

        self.path_template = PathTemplate()
        self.acquisition_parameters = AcquisitionParameters()

    def get_preview_image_paths(self):
        """
        Returns the full paths, including the filename, to preview/thumbnail
        images stored in the archive directory.

        :param acquisition: The acqusition object to generate paths for.
        :type acquisition: Acquisition

        :returns: The full paths.
        :rtype: str
        """
        paths = []

        for i in range(self.acquisition_parameters.first_image,
                       self.acquisition_parameters.num_images + \
                       self.acquisition_parameters.first_image):

            path = os.path.join(self.path_template.get_archive_directory(),
                                self.path_template.get_image_file_name(\
                                    suffix='thumb.jpeg') % i)

            paths.append(path)

        return paths


class PathTemplate(object):
    @staticmethod
    def set_data_base_path(base_directory):
        # os.path.abspath returns path without trailing slash, if any
        # eg. '/data/' => '/data'.
        PathTemplate.base_directory = os.path.abspath(base_directory)
    @staticmethod
    def set_archive_path(archive_base_directory, archive_folder):
        PathTemplate.archive_base_directory = os.path.abspath(archive_base_directory)
        PathTemplate.archive_folder = archive_folder

    @staticmethod
    def set_path_template_style(synchotron_name, template=None):
        PathTemplate.synchotron_name = synchotron_name
        PathTemplate.template = template

    @staticmethod
    def set_precision(precision):
        PathTemplate.precision = precision

    def __init__(self):
        object.__init__(self)

        self.directory = str()
        self.process_directory = str()
        self.xds_dir = str()
        self.base_prefix = str()
        self.mad_prefix = str()
        self.reference_image_prefix = str()
        self.wedge_prefix = str()
        self.run_number = int()
        self.suffix = str()
        #self.precision = str()
        self.start_num = int()
        self.num_files = int()

    def as_dict(self):
        return {"directory" : self.directory,
                "process_directory" : self.process_directory,
                "xds_dir" : self.xds_dir,
                "base_prefix" : self.base_prefix,
                "mad_prefix" : self.mad_prefix,
                "reference_image_prefix" : self.reference_image_prefix,
                "wedge_prefix" : self.wedge_prefix,
                "run_number" : self.run_number,
                "suffix" : self.suffix,
                "precision" : self.precision,
                "start_num" : self.start_num,
                "num_files" : self.num_files}

    def set_from_dict(self, params_dict):
        for dict_item in params_dict.items():
            if hasattr(self, dict_item[0]):
                setattr(self, dict_item[0], dict_item[1])

    def get_prefix(self):
        prefix = self.base_prefix

        if self.mad_prefix:
            prefix = self.base_prefix  + '-' + self.mad_prefix

        if self.reference_image_prefix:
            prefix = self.reference_image_prefix + '-' + prefix

        if self.wedge_prefix:
            prefix = prefix + '_' + self.wedge_prefix

        return prefix

    def get_image_file_name(self, suffix=None):
        template = "%s_%s_%%" + self.precision + "d.%s"

        if suffix:
            file_name = template % (self.get_prefix(),
                                    self.run_number, suffix)
        else:
            file_name = template % (self.get_prefix(),
                                    self.run_number, self.suffix)

        return file_name

    def get_image_path(self):
        path = os.path.join(self.directory,
                            self.get_image_file_name())
        return path

    def get_archive_directory(self):
        """
        Returns the archive directory, for longer term storage. synchotron_name
        is set via static function calles from session hwobj

        :rtype: str
        :returns: Archive directory
        """
        folders = self.directory.split('/')
        if PathTemplate.synchotron_name == "MAXLAB":
            archive_directory = self.directory
            archive_directory = archive_directory.replace("/data/data1/visitor", "/data/ispyb")
            archive_directory = archive_directory.replace("/data/data1/inhouse", "/data/ispyb")
            archive_directory = archive_directory.replace("/data/data1", "/data/ispyb")
        elif PathTemplate.synchotron_name == "EMBL-HH": 
            archive_directory = os.path.join(PathTemplate.archive_base_directory,
                                             PathTemplate.archive_folder)
            archive_directory = os.path.join(archive_directory,
                                             *folders[4:])
        else:
            directory = self.directory[len(PathTemplate.base_directory):]
            folders = directory.split('/')
            if 'visitor' in folders:
                endstation_name = folders[3]
                folders[1] = PathTemplate.archive_folder
                folders[3] = folders[2]
                folders[2] = endstation_name
            else:
                endstation_name = folders[1]
                folders[1] = PathTemplate.archive_folder
                folders[2] = endstation_name

            archive_directory = os.path.join(PathTemplate.archive_base_directory, *folders[1:])

        return archive_directory

    def __eq__(self, path_template):
        result = False
        lh_dir = os.path.normpath(self.directory)
        rh_dir = os.path.normpath(path_template.directory)

        if self.get_prefix() == path_template.get_prefix() and \
                lh_dir == rh_dir:
            result = True

        return result

    def intersection(self, rh_pt):
        result = False

        #Only do the intersection if there is possibilty for
        #Collision, that is directories are the same.
        if (self == rh_pt) and (self.run_number == rh_pt.run_number):
            if self.start_num < (rh_pt.start_num + rh_pt.num_files) and \
               rh_pt.start_num < (self.start_num + self.num_files):

               result = True
    
        return result

    def get_files_to_be_written(self):
        file_locations = []
        file_name_template = self.get_image_file_name()

        for i in range(self.start_num,
                       self.start_num + self.num_files):
           
            file_locations.append(os.path.join(self.directory,
                                               file_name_template % i))

        return file_locations

    def is_part_of(self, path_template):
        result = False
        
        if self == path_template and \
               self.run_number == path_template.run_number:
            if path_template.start_num >= self.start_num and \
               path_template.num_files + path_template.start_num <= self.num_files + self.start_num:
                
                result = True
        else:
            result = False

        return result

    def copy(self):
        return copy.deepcopy(self)

class AcquisitionParameters(object):
    def __init__(self):
        object.__init__(self)

        self.first_image = int()
        self.num_images = int()
        self.osc_start = float()
        self.osc_range = float()
        self.osc_total_range = float()
        self.overlap = float()
        self.kappa = float()
        self.kappa_phi = float()
        self.exp_time = float()
        self.num_passes = int()
        self.num_lines = 1
        self.energy = int()
        self.centred_position = CentredPosition()
        self.resolution = float()
        self.transmission = float()
        self.inverse_beam = False
        self.shutterless = False
        self.take_snapshots = True
        self.take_video = False
        self.take_dark_current = True
        self.skip_existing_images = False
        self.detector_mode = str()
        self.induce_burn = False
        self.mesh_range = ()        
        self.mesh_snapshot = None
        self.comments = ""
        self.in_queue = False
        self.in_interleave = None

    def set_from_dict(self, params_dict):
        for item in params_dict.items():
            if hasattr(self, item[0]):
                if item[0] == "centred_position": 
                    self.centred_position.set_from_dict(item[1])     
                else:
                     setattr(self, item[0], item[1])

    def copy(self):
        return copy.deepcopy(self)

class Crystal(object):
    def __init__(self):
        object.__init__(self)
        self.space_group = 0
        self.cell_a = 0
        self.cell_alpha = 0
        self.cell_b = 0
        self.cell_beta = 0
        self.cell_c = 0
        self.cell_gamma = 0
        self.protein_acronym = ""

        # MAD energies
        self.energy_scan_result = EnergyScanResult()


class CentredPosition(object):
    """
    Class that represents a centred position.
    Can also be initialized with a mxcube motor dict
    which simply is a dictonary with the motornames and
    their corresponding values.
    """
    MOTOR_POS_DELTA = 1E-4
    DIFFRACTOMETER_MOTOR_NAMES = []
    @staticmethod
    def set_diffractometer_motor_names(*names):
        CentredPosition.DIFFRACTOMETER_MOTOR_NAMES = names[:]
        
    def __init__(self, motor_dict=None):
        self.snapshot_image = None
        self.centring_method = True
        self.index = None
        #self.used_for_collection = 0
        self.motor_pos_delta = CentredPosition.MOTOR_POS_DELTA

        for motor_name in CentredPosition.DIFFRACTOMETER_MOTOR_NAMES:
            setattr(self, motor_name, None)

        if motor_dict is not None:
            for motor_item in motor_dict.items():
                setattr(self, motor_item[0], motor_item[1])

    def as_dict(self):
        return dict(zip(CentredPosition.DIFFRACTOMETER_MOTOR_NAMES,
                    [getattr(self, motor_name) for motor_name in CentredPosition.DIFFRACTOMETER_MOTOR_NAMES]))

    def set_from_dict(self, params_dict):
        for dict_item in params_dict.items():
            if hasattr(self, dict_item[0]):
                setattr(self, dict_item[0], dict_item[1])

    def as_str(self):
        motor_str = ""
        for motor_name in CentredPosition.DIFFRACTOMETER_MOTOR_NAMES:
            if getattr(self, motor_name):
                motor_str += "%s: %.3f " %(motor_name, abs(getattr(self, motor_name)))
        return motor_str

    def __repr__(self):
        return str(self.as_dict())

    def __eq__(self, cpos):
        eq = len(CentredPosition.DIFFRACTOMETER_MOTOR_NAMES)*[False]
        for i, motor_name in enumerate(CentredPosition.DIFFRACTOMETER_MOTOR_NAMES):
            self_pos = getattr(self, motor_name)
            cpos_pos = getattr(cpos, motor_name)
            if None in (self_pos, cpos_pos):
               continue
            eq[i] = abs(self_pos - cpos_pos) <= self.motor_pos_delta
        return all(eq)

    def __ne__(self, cpos):
        return not (self == cpos)

    def set_index(self, index):
        self.index = index

    def set_motor_pos_delta(self, delta):
        self.motor_pos_delta = delta

    def get_index(self):
        return self.index

    def get_kappa_value(self):
        return self.kappa

    def get_kappa_phi_value(self):
        return self.kappa_phi

class Workflow(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)
        self.path_template = PathTemplate()
        self._type = str()
        self.set_requires_centring(False)

    def set_type(self, workflow_type):
        self._type = workflow_type

    def get_type(self):
        return self._type

    def get_path_template(self):
        return self.path_template


#
# Collect hardware object utility function.
#
def to_collect_dict(data_collection, session, sample, centred_pos=None):
    """ return [{'comment': '',
          'helical': 0,
          'motors': {},
          'take_video': False,
          'take_snapshots': False,
          'fileinfo': {'directory': '/data/id14eh4/inhouse/opid144/' +\
                                    '20120808/RAW_DATA',
                       'prefix': 'opid144', 'run_number': 1,
                       'process_directory': '/data/id14eh4/inhouse/' +\
                                            'opid144/20120808/PROCESSED_DATA'},
          'in_queue': 0,
          'detector_mode': 2,
          'shutterless': 0,
          'sessionId': 32368,
          'do_inducedraddam': False,
          'sample_reference': {},
          'processing': 'False',
          'residues': '',
          'dark': True,
          'scan4d': 0,
          'input_files': 1,
          'oscillation_sequence': [{'exposure_time': 1.0,
                                    'kappaStart': 0.0,
                                    'phiStart': 0.0,
                                    'start_image_number': 1,
                                    'number_of_images': 1,
                                    'overlap': 0.0,
                                    'start': 0.0,
                                    'range': 1.0,
                                    'number_of_passes': 1}],
          'nb_sum_images': 0,
          'EDNA_files_dir': '',
          'anomalous': 'False',
          'file_exists': 0,
          'experiment_type': 'SAD',
          'skip_images': 0}]"""

    acquisition = data_collection.acquisitions[0]
    acq_params = acquisition.acquisition_parameters
    proc_params = data_collection.processing_parameters

    return [{'comment': '',
             #'helical': 0,
             #'motors': {},
             'take_video': acq_params.take_video,
             'take_snapshots': acq_params.take_snapshots,
             'fileinfo': {'directory': acquisition.path_template.directory,
                          'prefix': acquisition.path_template.get_prefix(),
                          'run_number': acquisition.path_template.run_number,
                          'archive_directory' : acquisition.\
                          path_template.get_archive_directory(),
                          'process_directory': acquisition.\
                          path_template.process_directory,
                          'template': acquisition.\
                          path_template.get_image_file_name()},
             'in_queue': acq_params.in_queue,
             'in_interleave' : acq_params.in_interleave,
             'detector_mode': acq_params.detector_mode,
             'shutterless': acq_params.shutterless,
             'sessionId': session.session_id,
             'do_inducedraddam': acq_params.induce_burn,
             'sample_reference': {'spacegroup': proc_params.space_group,
                                  'cell': proc_params.get_cell_str(),
                                  'blSampleId': sample.lims_id},
             'processing': str(proc_params.process_data and True),
             'residues':  proc_params.num_residues,
             'dark': acq_params.take_dark_current,
             #'scan4d': 0,
             'resolution': {'upper': acq_params.resolution},
             'transmission': acq_params.transmission,
             'energy': acq_params.energy,
             #'input_files': 1,
             'oscillation_sequence': [{'exposure_time': acq_params.exp_time,
                                       'kappaStart': acq_params.kappa,
                                       'phiStart': acq_params.kappa_phi,
                                       'start_image_number': acq_params.first_image,
                                       'number_of_images': acq_params.num_images,
                                       'overlap': acq_params.overlap,
                                       'start': acq_params.osc_start,
                                       'range': acq_params.osc_range,
                                       'number_of_passes': acq_params.num_passes,
                                       'number_of_lines': acq_params.num_lines,
                                       'mesh_range': acq_params.mesh_range}],
             'group_id': data_collection.lims_group_id,
             #'nb_sum_images': 0,
             'EDNA_files_dir': acquisition.path_template.process_directory,
             'xds_dir': acquisition.path_template.xds_dir,
             'anomalous': proc_params.anomalous,
             #'file_exists': 0,
             'experiment_type': queue_model_enumerables.\
             EXPERIMENT_TYPE_STR[data_collection.experiment_type],
             'skip_images': acq_params.skip_existing_images,
             'motors': centred_pos.as_dict() if centred_pos is not None else {}}]


def dc_from_edna_output(edna_result, reference_image_collection,
                        dcg_model, sample_data_model, beamline_setup_hwobj,
                        char_params = None):
    data_collections = []

    crystal = copy.deepcopy(reference_image_collection.crystal)
    ref_proc_params = reference_image_collection.processing_parameters
    processing_parameters = copy.deepcopy(ref_proc_params)

    try:
        char_results = edna_result.getCharacterisationResult()
        edna_strategy = char_results.getStrategyResult()
        collection_plan = edna_strategy.getCollectionPlan()[0]
        wedges = collection_plan.getCollectionStrategy().getSubWedge()
    except:
        pass
    else:
        try:
            resolution = collection_plan.getStrategySummary().\
                         getResolution().getValue()
            resolution = round(resolution, 3)
        except AttributeError:
            resolution = None

        try: 
            transmission = collection_plan.getStrategySummary().\
                           getAttenuation().getValue()
            transmission = round(transmission, 2)
        except AttributeError:
            transmission = None

        try:
            screening_id = edna_result.getScreeningId().getValue()
        except AttributeError:
            screening_id = None

        for i in range(0, len(wedges)):
            wedge = wedges[i]
            exp_condition = wedge.getExperimentalCondition()
            goniostat = exp_condition.getGoniostat()
            beam = exp_condition.getBeam()

            acq = Acquisition()
            acq.acquisition_parameters = beamline_setup_hwobj.\
                get_default_acquisition_parameters()
            acquisition_parameters = acq.acquisition_parameters

            acquisition_parameters.centred_position =\
                reference_image_collection.acquisitions[0].\
                acquisition_parameters.centred_position

            acq.path_template = beamline_setup_hwobj.get_default_path_template()

            # Use the same path tempalte as the reference_collection
            # and update the members the needs to be changed. Keeping
            # the directories of the reference collection.
            ref_pt= reference_image_collection.acquisitions[0].path_template
            acq.path_template = copy.deepcopy(ref_pt)
            acq.path_template.wedge_prefix = 'w' + str(i + 1)
            acq.path_template.reference_image_prefix = str()
            
            if resolution:
                acquisition_parameters.resolution = resolution

            if transmission:
                acquisition_parameters.transmission = transmission

            if screening_id:
                acquisition_parameters.screening_id = screening_id

            try:
                acquisition_parameters.osc_start = goniostat.\
                    getRotationAxisStart().getValue()
            except AttributeError:
                pass

            try:
                acquisition_parameters.osc_end = goniostat.\
                    getRotationAxisEnd().getValue()
            except AttributeError:
                pass

            try:
                acquisition_parameters.osc_range = goniostat.\
                    getOscillationWidth().getValue()
            except AttributeError:
                pass

            try:
                num_images = int(abs(acquisition_parameters.osc_end - \
                                     acquisition_parameters.osc_start) / acquisition_parameters.osc_range)
                
                acquisition_parameters.first_image = 1
                acquisition_parameters.num_images = num_images
                acq.path_template.num_files = num_images
                acq.path_template.start_num = 1
                
            except AttributeError:
                pass

            try:
                acquisition_parameters.transmission = beam.getTransmission().getValue()
            except AttributeError:
                pass

            try: 
                acquisition_parameters.energy = \
                   round((123984.0/beam.getWavelength().getValue())/10000.0, 4)
            except AttributeError:
                pass

            try:
                acquisition_parameters.exp_time = beam.getExposureTime().getValue()
            except AttributeError:
                pass


            # dc.parameters.comments = enda_result.comments
            # dc.parametets.path = enda_result.directory
            # dc.parameters.centred_positions = enda_result.centred_positions

            dc = DataCollection([acq], crystal, processing_parameters)
            data_collections.append(dc)

    return data_collections

def create_subwedges(total_num_images, sw_size, osc_range, osc_start):
    """
    Creates n subwedges where n = total_num_images / subwedge_size.

    :param total_num_images: The total number of images
    :type total_num_images: int

    :param subwedge_size: Number of images in each subwedge
    :type subwedge_size: int

    :param osc_range: Oscillation range for each image
    :type osc_range: double

    :param osc_start: The start angle/offset of the oscillation
    :type osc_start: double
    
    :returns: List of tuples with the format:
              (start image number, number of images, oscilation start)
    """
    number_of_subwedges = total_num_images / sw_size
    subwedges = []

    for sw_num in range(0, number_of_subwedges):
        _osc_start = osc_start + (osc_range * sw_size * sw_num)
        subwedges.append((sw_num * sw_size + 1, sw_size, _osc_start))

    return subwedges

def create_inverse_beam_sw(num_images, sw_size, osc_range,
                           osc_start, run_number):
    """
    Creates subwedges for inverse beam, and interleves the result.
    Wedges W1 and W2 are created 180 degres apart, the result is
    interleaved and given on the form:
    (W1_1, W2_1), ... (W1_n-1, W2_n-1), (W1_n, W2_n)

    :param num_images: The total number of images
    :type num_images: int

    :param sw_size: Number of images in each subwedge
    :type sw_size: int

    :param osc_range: Oscillation range for each image
    :type osc_range: double

    :param osc_start: The start angle/offset of the oscillation
    :type osc_start: double

    :param run_number: Run number for the first wedge (W1), the run number
                       of the second wedge will be run_number + 1.

    :returns: A list of tuples containing the swb wedges.
              The tuples are on the form:
              (start_image, num_images, osc_start, run_number)

    :rtype: List [(...), (...)]
    """
    w1 = create_subwedges(num_images, sw_size, osc_range, osc_start)
    w2 = create_subwedges(num_images, sw_size, osc_range, 180 + osc_start)
    w1 = [pair + (run_number,) for pair in w1]
    w2 = [pair + (run_number + 1,) for pair in w2]

    # Interlave subwedges
    subwedges = [sw_pair for pair in zip(w1, w2) for sw_pair in pair]
    
    return subwedges

def create_interleave_sw(interleave_list, num_images, sw_size):
    """
    Creates subwedges for interleved collection.
    Wedges W1, W2, Wm (where m is num_collections) are created:
    (W1_1, W2_1, ..., W1_m), ... (W1_n-1, W2_n-1, ..., Wm_n-1), 
    (W1_n, W2_n, ..., Wm_n)

    :param interleave_list: list of interleaved items
    :type interleave_list: list of dict

    :param num_images: number of images of first collection. Based on the 
    first collection certain number of subwedges will be created. If 
    first collection contains more images than others then in the end 
    the rest of images from first collections are created as last subwedge
    :type num_images: int

    :param sw_size: Number of images in each subwedge
    :type sw_size: int

    :returns: A list of tuples containing the swb wedges.
              The tuples are in the form:
              (collection_index, subwedge_index, subwedge_firt_image, 
               subwedge_start_osc)
    :rtype: List [(...), (...)]
    """
    subwedges = []
    sw_first_image = None
    for sw_index in range(num_images / sw_size):
        for collection_index in range(len(interleave_list)):
            collection_osc_start = interleave_list[collection_index]["data_model"].\
               acquisitions[0].acquisition_parameters.osc_start
            collection_osc_range = interleave_list[collection_index]["data_model"].\
               acquisitions[0].acquisition_parameters.osc_range
            collection_first_image = interleave_list[collection_index]["data_model"].\
               acquisitions[0].acquisition_parameters.first_image
            collection_num_images = interleave_list[collection_index]["data_model"].\
               acquisitions[0].acquisition_parameters.num_images
            if sw_index * sw_size <= collection_num_images:
                sw_actual_size = sw_size
                if sw_size > collection_num_images - (sw_index + 1) * sw_size > 0:
                    sw_actual_size = collection_num_images % sw_size
                sw_first_image = collection_first_image + sw_index * sw_size
                sw_osc_start = collection_osc_start + collection_osc_range * sw_index * sw_size
                sw_osc_range = collection_osc_range * sw_actual_size
                subwedges.append({"collect_index" : collection_index,
                                  "collect_first_image" : collection_first_image,
                                  "collect_num_images" : collection_num_images, 
                                  "sw_index" : sw_index,
                                  "sw_first_image" : sw_first_image, 
                                  "sw_actual_size": sw_actual_size,
                                  "sw_osc_start" : sw_osc_start,
                                  "sw_osc_range" : sw_osc_range})
        sw_first_image += sw_actual_size 
    return subwedges
            
