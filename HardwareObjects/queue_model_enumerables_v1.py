"""
Enumberables and oheter constants used by the queue model.
"""

from collections import namedtuple

StrategyComplexity = namedtuple('StrategyComplexity', ['SINGLE','FEW','MANY'])
STRATEGY_COMPLEXITY = StrategyComplexity('none', 'min', 'full')

ExperimentType = namedtuple('ExperimentType', ['SAD','SAD_INV', 'MAD',
                                               'MAD_INV', 'NATIVE','HELICAL',
                                               'EDNA_REF', 'OSC', 'MESH', 
                                               'COLLECT_MULTIWEDGE'])
EXPERIMENT_TYPE = ExperimentType(0,1,2,3,4,5,6,7,8,9)
EXPERIMENT_TYPE_STR = ExperimentType('SAD','SAD - Inverse Beam','MAD',
                                     'MAD - Inverse Beam', 'OSC','Helical',
                                     'Characterization', 'OSC', 'Mesh', 'Collect - Multiwedge')

StrategyOption = namedtuple('StrategyOption', ['AVG'])
STRATEGY_OPTION = StrategyOption(0)

CollectionOrigin = namedtuple('CollectionOrigin',['MXCUBE', 'EDNA', 'WORKFLOW'])
COLLECTION_ORIGIN = CollectionOrigin(0, 1, 2)
COLLECTION_ORIGIN_STR = CollectionOrigin('mxcube', 'edna', 'workflow')

EDNARefImages = namedtuple('EDNARefImages', ['FOUR', 'TWO', 'ONE', 'NONE'])
EDNA_NUM_REF_IMAGES = EDNARefImages(0, 1, 2, 3)

CentringMethod = namedtuple('CentringMethod', ['NO', 'MANUAL', 'LOOP', 'FULLY_AUTOMATIC', 'XRAY'])
CENTRING_METHOD = CentringMethod(0, 1, 2, 3, 4)

WorkflowType = namedtuple('WorkflowType', ['BURN', 'WF1', 'WF2', 'LineScan', 'MeshScan', 'XrayCentring'])
WORKFLOW_TYPE = WorkflowType(0, 1, 2, 3, 4, 5)

XTAL_SPACEGROUPS = ['', 'P1', 'P2', 'P21', 'C2', 'P222', 'P2221', 'P21212',
                    'P212121', 'C222 ', 'C2221', 'F222', 'I222', 'I212121',
                    'P4', 'P41', 'P42', 'P43', 'P422', 'P4212', 'P4122',
                    'P41212', 'P4222', 'P42212', 'P4322', 'P43212', 'I4',
                    'I41', 'I422', 'I4122', 'P3', 'P31', 'P32', 'P312',
                    'P321', 'P3112', 'P3121', 'P3212', 'P3221', 'P6', 'P61',
                    'P65', 'P62', 'P64', 'P63', 'P622', 'P6122', 'P6522',
                    'P6222', 'P6422', 'P6322', 'R3', 'R32', 'P23', 'P213',
                    'P432', 'P4232', 'P4332', 'P4132', 'F23', 'F432',
                    'F4132', 'I23', 'I213', 'I432', 'I4132']

ORIG_EDNA_SPACEGROUPS = {'I4132': '214', 'P21212': '18', 'P432': '207',
                         'P43212': '96', 'P6222': '180', 'P3': '143',
                         'C2': '5', 'P6422': '181', 'P212121': '19',
                         'F432': '209', 'P4132': '213', 'R32': '155',
                         'P23' : '195', 'I23': '197', 'I212121': '24',
                         'P3112': '151', 'P1': '1', 'P42212': '94',
                         'P321': '150', 'P63': '173', 'I422': '97',
                         'P41': '76', 'P6122': '178', 'P65 ': '170',
                         'I41': '80', 'P32 ': '145', 'I432 ': '211',
                         'C222': '21', 'F4132': '210', 'F23 ': '196',
                         'I222': '23', 'P42 ': '77', 'I213 ': '199',
                         'P2': '3', 'R3 ': '146', 'P213 ': '198',
                         'I4122': '98', 'P61': '169', 'P312 ': '149',
                         'I4': '79', 'P64': '172', 'P222 ': '16',
                         'P41212': '92', 'P3212 ': '153', 'P21': '4',
                         'P6': '168', 'P4322 ': '95', 'C2221': '20',
                         'P422': '89', 'F222': '22', 'P62 ': '171',
                         'P6322': '182', 'P4 ': '75', 'P31 ': '144',
                         'P3221': '154', 'P4122 ': '91', 'P6522 ': '179',
                         'P4212': '90', 'P2221 ': '17', 'P622': '177',
                         'P43': '78', 'P4222 ': '93', 'P3121 ': '152',
                         'P4232': '208', 'P4332': '212'}
