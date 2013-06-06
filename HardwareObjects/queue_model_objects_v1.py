"""
"""

import pprint
import os
import time
import logging
import copy
import traceback

from collections import namedtuple

StrategyComplexity = namedtuple('StrategyComplexity', ['SINGLE','FEW','MANY'])
STRATEGY_COMPLEXITY = StrategyComplexity('none', 'min', 'full')

ExperimentType = namedtuple('ExperimentType', ['SAD','SAD_INV', 'MAD', 
                                               'MAD_INV', 'NATIVE','HELICAL', 'EDNA_REF', 'OSC'])
EXPERIMENT_TYPE = ExperimentType(0,1,2,3,4,5,6,7)

EXPERIMENT_TYPE_STR = ExperimentType('SAD','SAD - Inverse Beam','MAD','MAD - Inverse Beam',
                                     'OSC','Helical','Characterization', 'OSC')


StrategyOption = namedtuple('StrategyOption', ['AVG'])
STRATEGY_OPTION = StrategyOption(0)

CollectionOrigin = namedtuple('CollectionOrigin',['MXCUBE', 
                                                  'EDNA', 'WORKFLOW'])
COLLECTION_ORIGIN = CollectionOrigin(0, 1, 2)

COLLECTION_ORIGIN_STR = CollectionOrigin('mxcube', 'edna', 'workflow')

EDNARefImages = namedtuple('EDNARefImages', ['FOUR', 'TWO', 'ONE', 'NONE'])
EDNA_NUM_REF_IMAGES = EDNARefImages(0, 1, 2, 3)

CentringMethod = namedtuple('CentringMethod', ['MANUAL', 'LOOP', 'CRYSTAL'])
CENTRING_METHOD = CentringMethod(0, 1, 2)

logger = logging.getLogger('queue_model')
try:
    formatter = \
              logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr = logging.FileHandler('/users/blissadm/log/queue_model.log')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
except:
    pass

logger.setLevel(logging.INFO)
logger = logging.getLogger('queue_model').info("Module load, probably application start")


class TaskNode(object):
    def __init__(self):
        object.__init__(self)
        
        self._children = []
        self._name = str()
        self._number = int()
        self._executed = False
        self._parent = None
        self._names = {}
        self._enabled = False


    def is_enabled(self):
        return self._enabled


    def set_enabled(self, state):
        self._enabled = state


    def get_children(self):
        return self._children

        
    def get_parent(self):
        return self._parent


    def set_name(self, name):    
        self._name = name


    def set_number(self, number):
        self._number = number
        

    def _set_name(self, name):
        if name in self.get_parent()._names:
            self.get_parent()._names[name] += 1
        else:
            self.get_parent()._names[name] = 1

        self._number = self.get_parent()._names[name]
        self._name = name

        
    def get_name(self):
        return '%s - %i' % (self._name, self._number)


    def get_full_name(self):
        name_list = [self.get_name()]
        parent = self._parent
        root = self

        while(parent):
            name_list.append(parent.get_name())
            root = parent
            parent = parent._parent

        return name_list


    def get_run_number(self):
        return None


    def get_prefix(self):
        return None


    def get_files_to_be_written(self):
        return []

    
    def is_executed(self):
        return self._executed


    def set_executed(self, executed):
        self._executed = executed


    def pprint(self, indent = 0):
        s = indent * "\t" + str(self).replace('\n', '\n' + indent * "\t")  + "\n"

        for child in self._children:
            s += child.pprint(indent+1) 

        return s


    def get_root(self):
        parent = self._parent
        root = self
        
        if parent:
            while(parent):
                root = parent
                parent = parent._parent

        return root

    
    def __repr__(self):
        s = '<%s object at %s>' % (
             self.__class__.__name__,
             hex(id(self))
         )

        return s


class RootNode(TaskNode):
    def __init__(self):
        self._name = 'root'
        TaskNode.__init__(self)


class TaskGroup(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)


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
        
        self.loc_str = str()

        # A pair <basket_number, sample_number>
        self.location = (None, None)
        self.lims_location = (None, None)

        # Crystal information
        self.crystals = [Crystal()]

        self.energy_scan_result = EnergyScanResult()


    def __str__(self):
        s = '<%s object at %s>' % (
            self.__class__.__name__,
            hex(id(self))
            )

        return s


    def _print(self):
        print "sample: %s" % self.loc_str

    
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
            return acronym + '-' + name
        else:
            return ''


    def init_from_sc_sample(self, sc_sample):
         self.loc_str = str(sc_sample[1]) + ':' + str(sc_sample[2])
         self.location = (sc_sample[1], sc_sample[2])
         self.set_name(self.loc_str)
            

    def init_from_lims_object(self, lims_sample):
        if hasattr(lims_sample, 'cellA'):
            self.crystals[0].cell_a = lims_sample.cellA

        if hasattr(lims_sample, 'cellAlpha'):
             self.crystals[0].cell_alpha = lims_sample.cellAlpha

        if hasattr(lims_sample, 'cellB'):
            self.crystals[0].cell_b = lims_sample.cellB
        
        if hasattr(lims_sample, 'cellBeta'):
            self.crystals[0].cell_beta = lims_sample.cellBeta

        if hasattr(lims_sample, 'cellC'):
            self.crystals[0].cell_c = lims_sample.cellC

        if hasattr(lims_sample, 'cellGamma'):
            self.crystals[0].cell_gamma = lims_sample.cellGamma
            
        if hasattr(lims_sample, 'proteinAcronym'):
            self.crystals[0].protein_acronym = lims_sample.proteinAcronym

        if hasattr(lims_sample, 'crystalSpaceGroup'):
            self.crystals[0].space_group = lims_sample.crystalSpaceGroup

        if hasattr(lims_sample, 'code'):
           self.lims_code =  lims_sample.code
            
        if hasattr(lims_sample, 'holderLength'):
            self.holder_length = lims_sample.holderLength

        if hasattr(lims_sample, 'sampleId'):
            self.lims_id = lims_sample.sampleId
        
        if hasattr(lims_sample, 'sampleName'):
            self.name = lims_sample.sampleName
            
        if hasattr(lims_sample, 'containerSampleChangerLocation') and\
                hasattr(lims_sample, 'sampleLocation'):

            if lims_sample.containerSampleChangerLocation and \
                    lims_sample.sampleLocation:

                self.lims_sample_location = int(lims_sample.sampleLocation)
                self.lims_container_location = \
                    int(lims_sample.containerSampleChangerLocation)

                self.lims_location = (int(lims_sample.containerSampleChangerLocation),
                                 int(lims_sample.sampleLocation))
                
                self.location = (int(lims_sample.containerSampleChangerLocation),
                                 int(lims_sample.sampleLocation))
        
                self.loc_str = str(str(self.lims_location[0]) +\
                                   ':' + str(self.lims_location[1]))


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
    def __init__(self, acquisition_list = None, crystal = None,
                 processing_parameters = None, name = ''):
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
        self.experiment_type = EXPERIMENT_TYPE.NATIVE
        self.html_report = str()
        self.id = int()


    def as_dict(self):
        return {'prefix': self.acquisitions[0].path_template.prefix,
                'run_number' : self.acquisitions[0].path_template.run_number,
                'template' : self.acquisitions[0].path_template.template,
                'first_image' : self.acquisitions[0].acquisition_parameters.first_image,
                'num_images' : self.acquisitions[0].acquisition_parameters.num_images,
                'osc_start' : self.acquisitions[0].acquisition_parameters.osc_start,
                'osc_range' : self.acquisitions[0].acquisition_parameters.osc_range,
                'overlap': self.acquisitions[0].acquisition_parameters.overlap,
                'exp_time' : self.acquisitions[0].acquisition_parameters.exp_time,
                'num_passes' : self.acquisitions[0].acquisition_parameters.num_passes,
                'path' : self.acquisitions[0].path_template.directory,
                'centred_position': self.acquisitions[0].acquisition_parameters.centred_position,
                'energy': self.acquisitions[0].acquisition_parameters.energy,
                'resolution': self.acquisitions[0].acquisition_parameters.resolution,
                'transmission': self.acquisitions[0].acquisition_parameters.transmission,
                'shutterless': self.acquisitions[0].acquisition_parameters.shutterless,
                'inverse_beam': self.acquisitions[0].acquisition_parameters.inverse_beam,
                'sample': str(self.crystal),
                'acquisitions': str(self.acquisitions),
                'acq_parameters': str(self.acquisitions[0].acquisition_parameters),
                'snapshot': self.acquisitions[0].acquisition_parameters.centred_position.snapshot_image}


    def get_name(self):
        return '%s_%i' % (self._name, self._number)

        
    def is_collected(self):
        return self.is_executed()


    def set_collected(self, collected):
        return self.set_executed(collected)


    def get_run_number(self):
        return self.acquisitions[0].path_template.run_number
    

    def get_prefix(self):
        return self.acquisitions[0].path_template.prefix


    def get_files_to_be_written(self):
        file_locations = []
        
        path_template = self.acquisitions[0].path_template
        file_name_template = path_template.get_image_file_name()

        for i in range(path_template.start_num, 
                       path_template.start_num + path_template.num_files):
                    
            file_locations.append(os.path.join(path_template.directory,
                                               file_name_template % i))

        return file_locations


    def __str__(self):
        s = '<%s object at %s>' % (
            self.__class__.__name__,
            hex(id(self))
        )
        
        return s


    def __str__(self):
        return super(DataCollection, self).__str__()


    def _print(self):
        print "data collection: " + pprint.pformat(self.parameters)


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
        self.num_residues = 0
        self.process_data = True
        self.anomalous = False
        self.pdb_code = None
        self.pdb_file = str()


    def get_cell_str(self):
        return ",".join(map(str, (self.cell_a, self.cell_b,
                                  self.cell_c, self.cell_alpha,
                                  self.cell_beta, self.cell_gamma)))


class Characterisation(TaskNode):
   def __init__(self, ref_data_collection = None,
                characterisation_parameters = None, name = ''):
        TaskNode.__init__(self)

        if not characterisation_parameters:
            characterisation_parameters = CharacterisationParameters()

        if not ref_data_collection:
            ref_data_collection = DataCollection()

        self.reference_image_collection = ref_data_collection
        self.characterisation_parameters = characterisation_parameters
        self.set_name(name)
        
        self.html_report = None
        self.characterisation_software = None


   def get_name(self):
       return '%s_%i' % (self._name, self._number)


   def get_run_number(self):
       return  self.reference_image_collection.get_run_number()


   def get_prefix(self):
       return self.reference_image_collection.get_prefix()


   def get_files_to_be_written(self):
        file_locations = []
        
        path_template = self.reference_image_collection.acquisitions[0].\
                        path_template
        file_name_template = path_template.get_image_file_name()

        for i in range(path_template.start_num, 
                       path_template.start_num + path_template.num_files):
                    
            file_locations.append(os.path.join(path_template.directory,
                                               file_name_template % i))

        return file_locations


class CharacterisationParameters(object):
    def __init__(self):
        # Setting num_ref_images to EDNA_NUM_REF_IMAGES.NONE
        # will disable characterisation.
        self.path_template = PathTemplate()
        self.experiment_type = 0 

        # Optimisation parameters
        self.use_aimed_resolution = False
        self.aimed_resolution = 1.0
        self.use_aimed_multiplicity = False
        self.aimed_multiplicity = 4
        self.aimed_i_sigma = 3.0
        self.aimed_completness = 9.9e-01
        self.strategy_complexity = 1
        self.induce_burn = False
        self.use_permitted_rotation = False
        self.permitted_phi_start = 0.0
        self.permitted_phi_end = 360
        self.low_res_pass_strat = False

        # Crystal
        self.max_crystal_vdim = 1e-01
        self.min_crystal_vdim = 1e-01
        self.max_crystal_vphi = 360
        self.min_crystal_vphi = 0.0
        self.space_group = ""

        # Characterisation type
        self.use_min_dose = True
        self.use_min_time = False
        self.min_dose = 30.0
        self.min_time = 0.0
        self.account_rad_damage = True
        self.auto_res = False
        self.opt_sad = False
        self.determine_rad_params = False
        self.burn_osc_start = 0.0
        self.burn_osc_interval = 3

        # Radiation damage model
        self.rad_suscept = 1.0
        self.beta = 1
        self.gamma = 0.06


    def as_dict(self):
        return {"experiment_type": self.experiment_type,
                "aimed_resolution": self.aimed_resolution,
                "aimed_multiplicity": self.aimed_multiplicity,
                "aimed_i_sigma": self.aimed_i_sigma,
                "aimed_completness": self.aimed_completness,
                "strategy_complexity": self.strategy_complexity}


    def __repr__(self):
        s = '<%s object at %s>' % (
            self.__class__.__name__,
            hex(id(self)))

        return s


class EnergyScan(TaskNode):
    def __init__(self, sample = None, path_template = None):
        TaskNode.__init__(self)
        self.element_symbol = None
        self.edge = None

        if not sample:
            self.sample = sample
        else:
            self.sampel = Sample()
            
        if not path_template:
            self.path_template = path_template
        else:
            self.path_template = PathTemplate()
        
        self.result = EnergyScanResult()


    def get_run_number(self):
        return self.path_template.run_number
           

    def get_prefix(self):
        return self.path_template.prefix


    def next_available_run_number(self):
        parent_node = self.get_parent()
        largest = 1

        for task_node in parent_node.get_children():
            if task_node.get_prefix() == self.get_prefix():
                if task_node.get_run_number() > largest:
                    largest = task_node.get_run_number()

        return int(largest)


class EnergyScanResult(object):
    def __init__(self):
        object.__init__(self)   
        self.inflection = 0
        self.peak = 0
        self.first_remote = 0
        self.second_remote = 0
        self.data_file_path = PathTemplate()


class SampleCentring(TaskNode):
    def __init__(self):
        TaskNode.__init__(self)
        self._task = None


    def set_task(self, task_node):
        self._task = task_node


    def get_task(self):
        return self._task
    

class Acquisition(object):
    def __init__(self):
        object.__init__(self)

        self.path_template = PathTemplate()
        self.acquisition_parameters = AcquisitionParameters()


    def get_preview_image_paths(self, acquisition):
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

            path = os.path.join(selfpath_template.get_archive_directory(),
                                acquisition.path_template.get_image_file_name(\
                                    suffix = 'thumb.jpeg') % i)

            paths.append(path)

        return paths


class PathTemplate(object):
    def __init__(self):
        object.__init__(self)

        self.directory = str()
        self.process_directory = str()

        self.prefix = str()
        self.base_prefix = str()
        self.mad_prefix = str()
        self.reference_image_prefix = str()
        self.template = str()
        self.run_number = 1
        self.suffix = 'img'
        self.precision = '04'
        self.start_num = 1
        self.num_files = 1

        
    def get_prefix(self):
        prefix = self.base_prefix

        if self.mad_prefix:
            prefix = self.mad_prefix + '-' + self.base_prefix

        if self.reference_image_prefix:
            prefix = self.reference_image_prefix + '-' + prefix

        return prefix


    def get_image_file_name(self, suffix = None):
        template = "%s_%s_%%" + self.precision + "d.%s"

        if suffix:
            file_name = template % (self.prefix, self.run_number, suffix)
        else:
            file_name = template % (self.prefix, self.run_number, self.suffix)

        return file_name


    def get_image_path(self):
        path = os.path.join(self.directory,
                            self.get_image_file_name())
        return path


    def get_archive_directory(self):
        """
        Returns the archive directory, for longer term storage.

        :returns: Archive directory.
        :rtype: str
        """
        folders = self.directory.split('/')
        folders[2] = 'pyarch'
        folders[3] = self.endstation_name
        archive_directory = '/' +os.path.join(*folders[1:])

        return archive_directory


class AcquisitionParameters(object):
    def __init__(self):
        object.__init__(self)
        
        self.first_image = int(1)
        self.num_images = int(1)
        self.osc_start = float()
        self.osc_range = 2.0e-1
        self.overlap = float()
        self.exp_time = 1.0e-1
        self.num_passes = int(1)
        self.energy = int()
        self.centred_position = CentredPosition()
        self.resolution = float()
        self.transmission = float()
        self.inverse_beam = False
        self.shutterless = False
        self.take_snapshots = False
        self.take_dark_current = False
        self.skip_existing_images = False


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

    def __init__(self, motor_dict = None):
        object.__init__(self)
        
        self.sampx = int()
        self.sampy = int()
        self.phi = int()
        self.phiz = int()
        self.phiy = int()
        self.zoom = int()
        self.snapshot_image = None
        self.centring_method = True

        if motor_dict:
            try:
                self.sampx = motor_dict['sampx']
            except KeyError:
                pass

            try:
                self.sampy = motor_dict['sampy']
            except KeyError:
                pass

            try:
                self.phi = motor_dict['phi'] % 360
            except KeyError:
                pass

            try:
                self.phiz = motor_dict['phiz']
            except KeyError:
                pass

            try:
                self.phiy = motor_dict['phiy']
            except KeyError:
                pass

            try:
                self.zoom = motor_dict['zoom']
            except KeyError:
                pass


    def as_dict(self):
        return {'sampx': self.sampx,
                'sampy': self.sampy,
                'phi': self.phi,
                'phiz': self.phiz,
                'phiy': self.phiy,
                'zoom': self.zoom}


    def __repr__(self):
        return str({'sampx': str(self.sampx),
                    'sampy': str(self.sampy),
                    'phi': str(self.phi),
                    'phiz': str(self.phiz),
                    'phiy': str(self.phiy),
                    'zoom': str(self.zoom)})


#
# Collect hardware object utility function.
#
def to_collect_dict(data_collection, session):
    """ return [{'comment': '',
          'helical': 0,
          'motors': {},
          'take_snapshots': False,
          'fileinfo': {'directory': '/data/id14eh4/inhouse/opid144/20120808/RAW_DATA',
                       'prefix': 'opid144', 'run_number': 1,
                       'process_directory': '/data/id14eh4/inhouse/opid144/20120808/PROCESSED_DATA'},
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
             'helical': 0,
             'motors': {},
             'take_snapshots': acq_params.take_snapshots,
             'fileinfo': {'directory': acquisition.path_template.directory,
                          'prefix': acquisition.path_template.prefix,
                          'run_number': acquisition.path_template.run_number,
                          'process_directory': acquisition.path_template.process_directory},
             'in_queue': 0,
             'detector_mode': 0,
             'shutterless': acq_params.shutterless,
             'sessionId': session.session_id,
             'do_inducedraddam': False,
             'sample_reference': {'spacegroup': proc_params.space_group,
                                  'cell': proc_params.get_cell_str()},
             'processing': str(proc_params.process_data and True),
             'residues':  proc_params.num_residues,
             'dark': 'True', #acq_params.take_dark_current,
             'scan4d': 0,
             'resolution': {'upper': acq_params.resolution},
             'transmission': acq_params.transmission,
             'energy': acq_params.energy,
             'input_files': 1,
             'oscillation_sequence': [{'exposure_time': acq_params.exp_time,
                                       'kappaStart': 0.0,
                                       'phiStart': 0.0,
                                       'start_image_number': acq_params.first_image,
                                       'number_of_images': acq_params.num_images,
                                       'overlap': acq_params.overlap,
                                       'start': acq_params.osc_start,
                                       'range': acq_params.osc_range,
                                       'number_of_passes': acq_params.num_passes}],
             'nb_sum_images': 0,
             'EDNA_files_dir': '',
             'anomalous': proc_params.anomalous,
             'file_exists': 0,
             'experiment_type': EXPERIMENT_TYPE_STR[data_collection.experiment_type],
             'skip_images': acq_params.skip_existing_images}]


def next_available_run_number(parent_node, prefix):
    largest = 0

    for task_node in parent_node.get_children():
        if task_node.get_prefix() == prefix:
            if task_node.get_run_number() > largest:
                largest = task_node.get_run_number()

    return int(largest)


def dc_from_edna_output(edna_result, reference_image_collection,
                        dcg_model, sample_data_model, session,
                        char_params = None):
        data_collections = []

        crystal = copy.deepcopy(reference_image_collection.crystal)
        processing_parameters = copy.deepcopy(reference_image_collection.\
                                              processing_parameters)

        try:
            char_results = edna_result.getCharacterisationResult()
            edna_strategy = char_results.getStrategyResult()
            collection_plan = edna_strategy.getCollectionPlan()[0]
            wedges = collection_plan.getCollectionStrategy().getSubWedge()
        except:
            pass
        else:
            try:
                run_number = collection_plan.getCollectionPlanNumber().getValue()
            except AttributeError:
                run_number = 1

            try:
                resolution = collection_plan.getStrategySummary().\
                    getResolution().getValue()
            except AttributeError:
                resolution = None

            try: 
                transmission = collection_plan.getStrategySummary().\
                   getAttenuation().getValue()
            except AttributeError:
                transmission = None

            try:
                screening_id = edna_result.getScreeningId().getValue()
            except AttributeError:
                screening_id = None

            for wedge in wedges:
                exp_condition = wedge.getExperimentalCondition()
                goniostat = exp_condition.getGoniostat()
                beam = exp_condition.getBeam()
                
                acq = Acquisition()
                acquisition_parameters = acq.acquisition_parameters

                acquisition_parameters.centred_position =\
                    reference_image_collection.previous_acquisition.\
                    acquisition_parameters.centred_position

                sub_dir = dcg_model.get_name().lower().replace(' ','')

                data_directory = session.get_image_directory(sample_data_model,
                                                             sub_dir = sub_dir)
                
                proc_directory = session.get_process_directory(sample_data_model,
                                                               sub_dir = sub_dir)
                
                acq.path_template.directory = data_directory
                acq.path_template.process_directory = proc_directory
                
                acq.path_template.prefix = reference_image_collection.acquisitions[0].\
                                           path_template.prefix[4:]
                
                if run_number:
                    acquisition_parameters.run_number = run_number

                name = acq.path_template.prefix + '_' + str(run_number)

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
                    acquisition_parameters.osc_width = goniostat.\
                        getOscillationWidth().getValue()
                except AttributeError:
                    pass

                try:
                    acquisition_parameters.num_images = \
                        int(abs(acquisition_parameters.osc_end - \
                                acquisition_parameters.osc_start) / acquisition_parameters.osc_width)
                except AttributeError:
                    pass

                try:
                    acquisition_parameters.transmission = beam.getTransmission().getValue()
                except AttributeError:
                    pass

                try: 
                    acquisition_parameters.energy = \
                        int(123984.0/beam.getWavelength().getValue())/10000.0
                except AttributeError:
                    pass

                try:
                    acquisition_parameters.exp_time = beam.getExposureTime().getValue()
                except AttributeError:
                    pass


                # dc.parameters.comments = enda_result.comments
                # dc.parametets.path = enda_result.directory
                # dc.parameters.centred_positions = enda_result.centred_positions

                dc = DataCollection(dcg_model, [acq], crystal,
                                    processing_parameters, name = name)
                data_collections.append(dc)
            
        return data_collections
