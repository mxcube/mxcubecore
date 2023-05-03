#! /usr/bin/env python
# encoding: utf-8
""" Abstract beamline interface message classes

License:

This file is part of MXCuBE.

MXCuBE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MXCuBE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.
"""
from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import uuid
import json
from collections import OrderedDict
from collections import namedtuple

from mxcubecore.utils.conversion import string_types

from mxcubecore.model import crystal_symmetry

__copyright__ = """ Copyright © 2016 - 2019 by Global Phasing Ltd. """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"


# Enumerations

MESSAGE_INTENTS = {"DOCUMENT", "COMMAND", "EVENT"}

INDEXING_FORMATS = ("IDXREF",)

ABSORPTION_EDGES = ("K", "LI", "LII", "LIII", "MI", "MII", "MIII", "MIV", "MV")

CHEMICAL_ELEMENTS = OrderedDict(
    (
        ("H", "hydrogen"),
        ("HE", "helium"),
        ("LI", "lithium"),
        ("BE", "beryllium"),
        ("B", "boron"),
        ("C", "carbon"),
        ("N", "nitrogen"),
        ("O", "oxygen"),
        ("F", "fluorine"),
        ("NE", "neon"),
        ("NA", "sodium"),
        ("MG", "magnesium"),
        ("AL", "aluminium"),
        ("SI", "silicon"),
        ("P", "phosphorus"),
        ("S", "sulfur"),
        ("CL", "chlorine"),
        ("AR", "argon"),
        ("K", "potassium"),
        ("CA", "calcium"),
        ("SC", "scandium"),
        ("TI", "titanium"),
        ("V", "vanadium"),
        ("CR", "chromium"),
        ("MN", "manganese"),
        ("FE", "iron"),
        ("CO", "cobalt"),
        ("NI", "nickel"),
        ("CU", "copper"),
        ("ZN", "zinc"),
        ("GA", "gallium"),
        ("GE", "germanium"),
        ("AS", "arsenic"),
        ("SE", "selenium"),
        ("BR", "bromine"),
        ("KR", "krypton"),
        ("RB", "rubidium"),
        ("SR", "strontium"),
        ("Y", "yttrium"),
        ("ZR", "zirconium"),
        ("NB", "niobium"),
        ("MO", "molybdenum"),
        ("TC", "technetium"),
        ("RU", "ruthenium"),
        ("RH", "rhodium"),
        ("PD", "palladium"),
        ("AG", "silver"),
        ("CD", "cadmium"),
        ("IN", "indium"),
        ("SN", "tin"),
        ("SB", "antimony"),
        ("TE", "tellurium"),
        ("I", "iodine"),
        ("XE", "xenon"),
        ("CS", "caesium"),
        ("BA", "barium"),
        ("LA", "lanthanum"),
        ("CE", "cerium"),
        ("PR", "praseodymium"),
        ("ND", "neodymium"),
        ("PM", "promethium"),
        ("SM", "samarium"),
        ("EU", "europium"),
        ("GD", "gadolinium"),
        ("TB", "terbium"),
        ("DY", "dysprosium"),
        ("HO", "holmium"),
        ("ER", "erbium"),
        ("TM", "thulium"),
        ("YB", "ytterbium"),
        ("LU", "lutetium"),
        ("HF", "hafnium"),
        ("TA", "tantalum"),
        ("W", "tungsten"),
        ("RE", "rhenium"),
        ("OS", "osmium"),
        ("IR", "iridium"),
        ("PT", "platinum"),
        ("AU", "gold"),
        ("HG", "mercury"),
        ("TL", "thallium"),
        ("PB", "lead"),
        ("BI", "bismuth"),
        ("PO", "polonium"),
        ("AT", "astatine"),
        ("RN", "radon"),
        ("FR", "francium"),
        ("RA", "radium"),
        ("AC", "actinium"),
        ("TH", "thorium"),
        ("PA", "protactinium"),
        ("U", "uranium"),
        ("NP", "neptunium"),
        ("PU", "plutonium"),
        ("AM", "americium"),
        ("CM", "curium"),
        ("BK", "berkelium"),
        ("CF", "californium"),
        ("ES", "einsteinium"),
        ("FM", "fermium"),
        ("MD", "mendelevium"),
        ("NO", "nobelium"),
        ("LR", "lawrencium"),
        ("RF", "rutherfordium"),
        ("DB", "dubnium"),
        ("SG", "seaborgium"),
        ("BH", "bohrium"),
        ("HS", "hassium"),
        ("MT", "meitnerium"),
        ("DS", "darmstadtium"),
        ("RG", "roentgenium"),
        ("CN", "copernicium"),
        ("UUT", "ununtrium"),
        ("FL", "flerovium"),
        ("UUP", "ununpentium"),
        ("LV", "livermorium"),
    )
)

ParsedMessage = namedtuple(
    "ParsedMessage", ("message_type", "payload", "enactment_id", "correlation_id")
)


# Abstract classes


class MessageData(object):
    """Topmost superclass for all message data objects

    Later to add e.g. stringification"""


class Payload(MessageData):
    """Payload - top level message object"""

    INTENT = None

    def __init__(self):

        # This class is abstract
        intent = self.__class__.INTENT
        if intent not in MESSAGE_INTENTS:
            if intent is None:
                raise RuntimeError("Attempt to instantiate abstract class Payload")
            else:
                raise RuntimeError(
                    "Programming error - "
                    "Payload subclass %s intent %s must be one of: %s"
                    % (self.__class__.__name__, intent, sorted(MESSAGE_INTENTS))
                )

    @property
    def intent(self):
        """Message intent - class-level property"""
        return self.__class__.INTENT


class IdentifiedElement(MessageData):
    """Object with persistent uuid"""

    def __init__(self, id_=None):

        # This class is abstract
        if self.__class__.__name__ == "IdentifiedElement":
            raise RuntimeError(
                "Attempt to instantiate abstract class IdentifiedElement"
            )

        self._id = None
        self.__set_id(id_)

    @property
    def id_(self):
        """Unique identifier (UUID) for IdentifiedElement.
        Defaults to new, time-based uuid"""
        return self._id

    def __set_id(self, value):
        """Setter for uuid - accessible only within this class"""
        if value is None:
            self._id = uuid.uuid1()
        elif isinstance(value, uuid.UUID):
            self._id = value
        else:
            raise TypeError("UUID input must be of type uuid.UUID")


# Sync with Java 4/5/2017
# Acknowledge???
# Images???
# OrientationMatrix. NB this is a JAva stub. Not needed for now
# ObtainPriorInformation
# PrepareForCentring
# ReadyForCentring

# Intent is now  DOCUMENT, COMMAND, EVENT # NBNB TODO
# (data, command, info ca.) I could skip them?

# Simple payloads


class RequestConfiguration(Payload):
    """Configuration request message"""

    INTENT = "COMMAND"


class ObtainPriorInformation(Payload):
    """Prior information request"""

    INTENT = "COMMAND"


class PrepareForCentring(Payload):
    """Prior information request"""

    INTENT = "COMMAND"


class ReadyForCentring(Payload):
    """Prior information request"""

    INTENT = "DOCUMENT"


class SubprocessStopped(Payload):
    """Subprocess Stopped request message"""

    INTENT = "EVENT"


class ConfigurationData(Payload):
    """Configuration Data message"""

    INTENT = "DOCUMENT"

    # NB coded as mandatory, even if not explicitly non-null
    # (but raises MalformedUrlException) in Java.

    def __init__(self, location):
        super(ConfigurationData, self).__init__()
        self._location = location

    @property
    def location(self):
        """Url for directory containing configuration data.
        Generally an absolute file path."""
        return self._location


class SubprocessStarted(Payload):
    """Subprocess Started message"""

    INTENT = "EVENT"

    def __init__(self, name):
        super(SubprocessStarted, self).__init__()
        self._name = name

    @property
    def name(self):
        """name of subprocess"""
        return self._name


class ChooseLattice(Payload):
    """Choose lattice instruction"""

    INTENT = "COMMAND"

    def __init__(
        self,
        indexingSolutions,
        indexingFormat="IDXREF",
        crystalFamilyChar=None,
        lattices=None,
        userProvidedCell=None,
        indexingHeader=None
    ):
        """

        Args:
            indexingSolutions (list(IndexingSolution):
            indexingFormat (str):
            crystalFamilyChar (str):
            lattices sequence(str): string or sequence with one, or two unique strings
            userProvidedCell (UnitCell):
            indexingHeader (str):
        """
        super(ChooseLattice, self).__init__()

        self._indexingSolutions = indexingSolutions
        self._indexingFormat = indexingFormat
        self._crystalFamilyChar = crystalFamilyChar
        if not lattices:
            self._lattices = frozenset()
        elif isinstance(lattices, string_types):
            # Allows you to pass in lattices as a string without silly errors
            self._lattices = frozenset((lattices,))
        else:
            self._lattices = frozenset(lattices)
        self._userProvidedCell = userProvidedCell
        self._indexingHeader = indexingHeader
        self._crystalClasses = frozenset()

    @property
    def crystalFamilyChar(self):
        """One-letter code for crystal system (one of 'amothc')"""
        return self._crystalFamilyChar

    @property
    def lattices(self):
        """ set of expected lattices for solution"""
        return self._lattices

    @property
    def crystalClasses(self):
        """ set of crystal class names"""
        return self._crystalClasses

    @property
    def indexingSolutions(self):
        """List of IndexingSolution"""
        return self._indexingSolutions

    @property
    def indexingFormat(self):
        """Indexing format"""
        return self._indexingFormat

    @property
    def indexingHeader(self):
        """Indexing table header"""
        return self._indexingHeader


class SelectedLattice(MessageData):
    """Lattice selected message"""

    INTENT = "DOCUMENT"

    def __init__(
        self,
        data_model,
        indexingSolution,
        userPointGroup=None,
    ):
        self._indexingSolution = indexingSolution
        self._strategyDetectorSetting = data_model.detector_setting
        self._strategyWavelength = data_model.wavelengths[0]
        self._strategyControl = json.dumps(
            data_model.strategy_options, sort_keys=True
        )
        self._userPointGroup = userPointGroup

    @property
    def indexingSolution(self):
        """Proposed solution"""
        return self._indexingSolution

    @property
    def strategyDetectorSetting(self):
        """Detector setting to use for strategy calculation and acquisition"""
        return self._strategyDetectorSetting

    @property
    def strategyWavelength(self):
        """Wavelength to use for strategy calculation adn acquisition"""
        return self._strategyWavelength

    @property
    def strategyControl(self):
        """JSON string of command line options (*without* prefix)
        to use for startcal wrapper call"""
        return self._strategyControl

    @property
    def userPointGroup(self):
        """Point group given by user for strategy calculation"""
        return self._userPointGroup

class IndexingSolution(MessageData):
    """Indexing solution data"""

    def __init__(
        self,
        bravaisLattice,
        cell,
        isConsistent=None,
        latticeCharacter=None,
        qualityOfFit=None
    ):
        """

        Args:
            bravaisLattice (string): One of the 14 Bravais lattices ('aP' etc.)
            cell (UnitCell):
            isConsistent (bool): Is solution consistent with know symmetry?
            latticeCharacter (int):  Integer 1-44
            qualityOfFit (float):
        """
        self._bravaisLattice = bravaisLattice
        self._cell = cell
        self._isConsistent = isConsistent
        self._latticeCharacter = latticeCharacter
        self._qualityOfFit = qualityOfFit

    def bravaisLattice(self):
        """One of the 14 Bravais lattices ('aP' etc.) """
        return self._bravaisLattice

    @property
    def bravaisLattice(self):
        """"""
        return self._bravaisLattice
    @property
    def cell(self):
        """Unit ce;;"""
        return self._cell

    @property
    def isConsistent(self):
        """ Is solution consistent with know symmetry? """
        return self._isConsistent

    @property
    def latticeCharacter(self):
        """Integer 1-44 """
        return self._latticeCharacter

    @property
    def qualityOfFit(self):
        """"""
        return self._qualityOfFit


class CollectionDone(MessageData):
    """Collection Done message"""

    INTENT = "EVENT"

    def __init__(self, proposalId, status, procWithLatticeParams=False, imageRoot=None):
        self._proposalId = proposalId
        self._imageRoot = imageRoot
        self._status = status
        self._procWithLatticeParams = procWithLatticeParams

    @property
    def proposalId(self):
        """uuid of collection proposal that has been executed."""
        return self._proposalId

    @property
    def imageRoot(self):
        """Url for directory containing images.
        Generally an absolute file path."""
        return self._imageRoot

    @property
    def status(self):
        """Integer status code for collection result"""
        return self._status

    @property
    def procWithLatticeParams(self):
        """Boolean, whether lattice parameters should be used for processing"""
        return self._procWithLatticeParams


# Complex payloads


class WorkflowDone(Payload):
    """End-of-workflow message"""

    INTENT = "EVENT"

    def __init__(self, issues=None):

        super(WorkflowDone, self).__init__()

        if self.__class__.__name__ == "WorkflowDone":
            raise RuntimeError("Attempt to instantiate abstract class WorkflowDone")

        if issues:
            ll0 = list(x for x in issues if not isinstance(x, Issue))
            if ll0:
                raise ValueError("issues parameter contains non-issues: %s" % ll0)
            else:
                self._issues = tuple(issues)


class WorkflowCompleted(WorkflowDone):
    pass


class WorkflowAborted(WorkflowDone):
    pass


class WorkflowFailed(WorkflowDone):
    def __init__(self, reason=None, issues=None):

        super(WorkflowFailed, self).__init__(issues=issues)
        self._reason = reason

    @property
    def reason(self):
        return self._reason


class BeamlineAbort(Payload):
    """Abort workflow from beamline"""

    INTENT = "COMMAND"


# Simple data objects


class AnomalousScatterer(MessageData):
    def __init__(self, element, edge):

        if element in CHEMICAL_ELEMENTS:
            self._element = element
        else:
            raise ValueError("Chemical element code %s not recognised" % element)

        if edge in ABSORPTION_EDGES:
            self._edge = edge
        else:
            raise ValueError("Absorption edge code %s not recognised" % edge)

    @property
    def element(self):
        return self._element

    @property
    def edge(self):
        return self._edge


class UnitCell(MessageData):
    """Unit cell data type"""

    def __init__(self, a, b, c, alpha, beta, gamma):
        self._lengths = (a, b, c)
        self._angles = (alpha, beta, gamma)

    @property
    def lengths(self):
        return self._lengths

    @property
    def angles(self):
        return self._angles

    @property
    def a(self):
        return self._lengths[0]

    @property
    def b(self):
        return self._lengths[1]

    @property
    def c(self):
        return self._lengths[2]

    @property
    def alpha(self):
        return self._angles[0]

    @property
    def beta(self):
        return self._angles[1]

    @property
    def gamma(self):
        return self._angles[2]


class Issue(IdentifiedElement):
    """Issue (status information returned with WorkflowDone messages)"""

    def __init__(self, component, message, code=None, id_=None):
        IdentifiedElement.__init__(self, id_)
        self._component = component
        self._message = message
        self._code = code

    @property
    def component(self):
        """Part of unique identifier of issue definition"""
        return self._component

    @property
    def code(self):
        """Part of unique identifier of issue definition"""
        return self._code

    @property
    def message(self):
        """Text providing specific details about this issue"""
        return self._message


class PhasingWavelength(IdentifiedElement):
    """Phasing Wavelength"""

    def __init__(self, wavelength, role=None, id_=None):
        IdentifiedElement.__init__(self, id_)
        self._role = role
        self._wavelength = wavelength

    @property
    def role(self):
        """Wavelength role"""
        return self._role

    @property
    def wavelength(self):
        """Wavelength setting for beam"""
        return self._wavelength

    @wavelength.setter
    def wavelength(self, value):
        if self._wavelength:
            raise TypeError("PhasingWavelength values cannot be re-set if non-zero")
        self._wavelength = value


class BeamSetting(IdentifiedElement):
    """Beam setting"""

    def __init__(self, wavelength, id_=None):
        IdentifiedElement.__init__(self, id_)
        self._wavelength = wavelength

    @property
    def wavelength(self):
        """Wavelength setting for beam"""
        return self._wavelength


class ScanExposure(IdentifiedElement):
    """Scan Exposure"""

    def __init__(self, time, transmission, id_=None):
        IdentifiedElement.__init__(self, id_)
        self._time = time
        self._transmission = transmission

    @property
    def transmission(self):
        """Scan exposure transmission"""
        return self._transmission

    @property
    def time(self):
        """Scan exposure transmission"""
        return self._time


class ScanWidth(IdentifiedElement):
    """Scan Width"""

    def __init__(self, imageWidth, numImages, id_=None):
        IdentifiedElement.__init__(self, id_)
        self._imageWidth = imageWidth
        self._numImages = numImages

    @property
    def imageWidth(self):
        """Scan image width"""
        return self._imageWidth

    @property
    def numImages(self):
        """Number of images"""
        return self._numImages


class PositionerSetting(IdentifiedElement):
    """Positioner Setting object.

    Has a uuid and a settings dictionary of axisName:value
    """

    def __init__(self, id_=None, **axisSettings):

        super(PositionerSetting, self).__init__(id_=id_)

        if self.__class__.__name__ == "PositionerSetting":
            # This class is abstract
            raise RuntimeError(
                "Programming error -"
                " attempt to instantiate abstract class PositionerSetting"
            )
        if None in axisSettings.values():
            raise ValueError(
                "axisSettings contain value None: %s" % sorted(axisSettings.items())
            )
        self._axisSettings = axisSettings.copy()

    @property
    def axisSettings(self):
        """axisName:value settings dictionary. NB the returned value is a copy;
        modifying it does *not* modify the object internals."""
        return self._axisSettings.copy()


class DetectorSetting(PositionerSetting):
    """Detector position setting"""


class BcsDetectorSetting(DetectorSetting):
    """Detector position setting with additional (beamline-side) resolution and orgxy"""

    def __init__(self, resolution, id_=None, orgxy=(), **axisSettings):
        super(BcsDetectorSetting, self).__init__(id_=id_, **axisSettings)
        self._resolution = resolution
        self._orgxy = tuple(orgxy)

    @property
    def resolution(self):
        """Resolution (in A) matching detector distance"""
        return self._resolution

    @property
    def orgxy(self):
        """Tuple, empty or of two floats; beam centre on detector """
        return self._orgxy


class BeamstopSetting(PositionerSetting):
    """Beamstop position setting"""


class GoniostatRotation(PositionerSetting):
    """Goniostat Rotation setting"""

    def __init__(self, id_=None, **axisSettings):
        PositionerSetting.__init__(self, id_=id_, **axisSettings)
        self._translation = None

    @property
    def translation(self):
        """GoniostatTranslation corresponding to self

        NB This link can be set only by GoniostatTranslation.__init__"""
        return self._translation

    def get_motor_settings(self):
        """Get dictionary of rotation and translation motor setting"""
        result = dict(self.axisSettings)
        translation = self.translation
        if translation is not None:
            result.update(translation.axisSettings)
        #
        return result


class GoniostatSweepSetting(GoniostatRotation):
    """Goniostat Sweep setting"""

    def __init__(self, scanAxis, id_=None, **axisSettings):
        GoniostatRotation.__init__(self, id_=id_, **axisSettings)
        self._scanAxis = scanAxis

    @property
    def scanAxis(self):
        """Scanning axis"""
        return self._scanAxis


class GoniostatTranslation(PositionerSetting):
    """Goniostat Translation setting

    NB the reverse GoniostatRotation.translation link is set from here.
    For this reason the constructor parameters are different from the
    object attributes. rotation is taken to be newRotation, except that:

    if ( rotation is not None and
          (requestedRotationId is None or requestedRotationId == rotation.id_):
        self.requestedRotationId = rotation.id_
        self.newRotation = None"""

    def __init__(
        self, rotation=None, requestedRotationId=None, id_=None, **axisSettings
    ):
        PositionerSetting.__init__(self, id_=id_, **axisSettings)

        if rotation is None:
            if requestedRotationId is None:
                raise ValueError("rotation and requestedRotationId cannot both be None")
            else:
                self._newRotation = None
                self._requestedRotationId = requestedRotationId
        else:
            if requestedRotationId is None or requestedRotationId == rotation.id_:
                self._newRotation = None
                self._requestedRotationId = rotation.id_
            else:
                self._newRotation = rotation
                self._requestedRotationId = requestedRotationId

            # NBNB this deliberately interferes with the internals of
            # GoniostatRotation
            rotation._translation = self

    @property
    def newRotation(self):
        return self._newRotation

    @property
    def requestedRotationId(self):
        return self._requestedRotationId


# Complex data objects


class UserProvidedInfo(MessageData):
    """User-provided information"""

    def __init__(self, data_model):

        self._scatterers = ()
        crystal_classes = data_model.crystal_classes
        strategy_point_group = crystal_symmetry.strategy_point_group(crystal_classes)
        self._pointGroup = strategy_point_group
        crystal_systems = set(
            crystal_symmetry.CRYSTAL_CLASS_MAP[name].crystal_system
            for name in crystal_classes
        )
        if crystal_systems in (set(("Trigonal")), set(("Trigonal", "Hexagonal"))):
            crystal_family = "Hexagonal"
        elif len(crystal_systems) == 1:
            crystal_family = crystal_systems.pop()
        else:
            crystal_family = None
        self._crystal_family = crystal_family.upper()

        sg_data = crystal_symmetry.SPACEGROUP_MAP.get(data_model.space_group)
        self._spaceGroup = sg_data.number if sg_data else None
        cell_parameters = data_model.cell_parameters
        if cell_parameters:
            self._cell = UnitCell(*cell_parameters)
        else:
            self._cell = None
        self._expectedResolution = data_model.aimed_resolution
        self._isAnisotropic = None

    @property
    def scatterers(self):
        return self._scatterers

    @property
    def crystal_family(self):
        return self._crystal_family

    @property
    def pointGroup(self):
        return self._pointGroup

    @property
    def spaceGroup(self):
        return self._spaceGroup

    @property
    def cell(self):
        return self._cell

    @property
    def expectedResolution(self):
        return self._expectedResolution

    @property
    def isAnisotropic(self):
        return self._isAnisotropic


class Sweep(IdentifiedElement):
    """Geometric strategy Sweep"""

    def __init__(
        self,
        goniostatSweepSetting,
        detectorSetting,
        beamSetting,
        start,
        width,
        beamstopSetting=None,
        sweepGroup=None,
        id_=None,
    ):

        super(Sweep, self).__init__(id_=id_)

        self._scans = set()

        self._goniostatSweepSetting = goniostatSweepSetting
        self._detectorSetting = detectorSetting
        self._beamSetting = beamSetting
        self._beamstopSetting = beamstopSetting
        self._start = start
        self._width = width
        self._sweepGroup = sweepGroup

    @property
    def goniostatSweepSetting(self):
        return self._goniostatSweepSetting

    @property
    def detectorSetting(self):
        return self._detectorSetting

    @property
    def beamSetting(self):
        return self._beamSetting

    @property
    def beamstopSetting(self):
        return self._beamstopSetting

    @property
    def start(self):
        return self._start

    @property
    def width(self):
        return self._width

    @property
    def sweepGroup(self):
        return self._sweepGroup

    @property
    def scans(self):
        """Scans that belong to sweeps.

        NB this is a two-way link.
        It is populated when the Scan objects are created"""
        return frozenset(self._scans)

    def _add_scan(self, scan):
        """Implementation method. *Only* to be called from Scan.__init__"""
        self._scans.add(scan)

    def get_initial_settings(self):
        """Get dictionary of rotation and translation motor settings for start of sweep"""
        result = self.goniostatSweepSetting.get_motor_settings()
        result[self.goniostatSweepSetting.scanAxis] = self.start
        #
        return result


class Scan(IdentifiedElement):
    """Collection strategy Scan"""

    def __init__(
        self, width, exposure, imageStartNum, start, sweep, filenameParams, id_=None
    ):

        super(Scan, self).__init__(id_=id_)

        self._filenameParams = dict(filenameParams)

        self._width = width
        self._exposure = exposure
        self._imageStartNum = imageStartNum
        self._start = start

        sweep._add_scan(self)
        self._sweep = sweep

    @property
    def width(self):
        return self._width

    @property
    def exposure(self):
        return self._exposure

    @property
    def imageStartNum(self):
        return self._imageStartNum

    @property
    def start(self):
        return self._start

    @property
    def sweep(self):
        return self._sweep

    @property
    def filenameParams(self):
        return dict(self._filenameParams)


class GeometricStrategy(IdentifiedElement, Payload):
    """Geometric strategy """

    INTENT = "COMMAND"

    def __init__(
        self,
        isInterleaved,
        isUserModifiable,
        defaultDetectorSetting,
        defaultBeamSetting,
        allowedWidths=(),
        sweepOffset=None,
        sweepRepeat=None,
        defaultWidthIdx=None,
        sweeps=(),
        id_=None,
    ):

        super(GeometricStrategy, self).__init__(id_=id_)

        self._isInterleaved = isInterleaved
        self._isUserModifiable = isUserModifiable
        self._defaultDetectorSetting = defaultDetectorSetting
        self._defaultBeamSetting = defaultBeamSetting
        self._defaultWidthIdx = defaultWidthIdx
        self._sweeps = frozenset(sweeps)

        if len(set(allowedWidths)) != len(allowedWidths):
            raise ValueError(
                "allowedWidths contains duplicate value: %s" % allowedWidths
            )
        else:
            self._allowedWidths = tuple(allowedWidths)

        self._sweepOffset = sweepOffset
        self._sweepRepeat = sweepRepeat

    @property
    def isInterleaved(self):
        return self._isInterleaved

    @property
    def sweepRepeat(self):
        return self._sweepRepeat

    @property
    def sweepOffset(self):
        return self._sweepOffset

    @property
    def isUserModifiable(self):
        return self._isUserModifiable

    @property
    def defaultWidthIdx(self):
        return self._defaultWidthIdx

    @property
    def defaultDetectorSetting(self):
        return self._defaultDetectorSetting

    @property
    def defaultBeamSetting(self):
        return self._defaultBeamSetting

    @property
    def allowedWidths(self):
        return self._allowedWidths

    @property
    def sweeps(self):
        return self._sweeps

    def get_ordered_sweeps(self):
        """Get sweeps in acquisition order.

        Acquisition order is determined by the sweepGroup -
        to get results deterministic we use a secondary sort on
        angles, in alphabetical name order as a backup,
        (in pracite, 'kappa', 'kappa_phi', 'phi')
        which should match what the workflow does internally.
        Anyway, it is the sweep"""
        ll0 = []
        for sweep in self._sweeps:
            dd0 = sweep.get_initial_settings()
            ll0.append((sweep.sweepGroup, tuple(dd0[x] for x in sorted(dd0)), sweep))
        #
        return list(tt0[2] for tt0 in sorted(ll0))


class CollectionProposal(IdentifiedElement, Payload):
    """Collection proposal """

    INTENT = "COMMAND"

    def __init__(self, relativeImageDir, strategy, scans, id_=None):

        super(CollectionProposal, self).__init__(id_=id_)

        self._relativeImageDir = relativeImageDir
        self._strategy = strategy
        self._scans = tuple(scans)

    @property
    def relativeImageDir(self):
        return self._relativeImageDir

    @property
    def strategy(self):
        return self._strategy

    @property
    def scans(self):
        return self._scans


class PriorInformation(Payload):
    """Prior information to workflow calculation"""

    INTENT = "DOCUMENT"

    def __init__(self, data_model, image_root):

        super(PriorInformation, self).__init__()

        # Look for existing uuid
        sample_model = data_model.get_sample_node()
        for text in sample_model.lims_code, sample_model.code, sample_model.name:
            if text:
                try:
                    sampleId = uuid.UUID(text)
                except Exception:
                    # The error expected if this goes wrong is ValueError.
                    # But whatever the error we want to continue
                    pass
                else:
                    # Text was a valid uuid string. Use the uuid.
                    break
        else:
            sampleId = uuid.uuid1()
        if isinstance(sampleId, uuid.UUID):
            self._sampleId = sampleId
        else:
            raise TypeError("sampleId input must be of type uuid.UUID")

        self._sampleName = data_model.path_template.base_prefix
        # Draft in API, not currently coded in Java:
        self._rootDirectory = image_root
        self._userProvidedInfo = UserProvidedInfo(data_model)

    @property
    def sampleId(self):
        return self._sampleId

    @property
    def sampleName(self):
        return self._sampleName

    @property
    def rootDirectory(self):
        return self._rootDirectory

    @property
    def userProvidedInfo(self):
        return self._userProvidedInfo


class RequestCentring(Payload):
    """Request for centering"""

    INTENT = "COMMAND"

    def __init__(self, currentSettingNo, totalRotations, goniostatRotation):
        super(RequestCentring, self).__init__()
        self._currentSettingNo = currentSettingNo
        self._totalRotations = totalRotations
        self._goniostatRotation = goniostatRotation

    @property
    def currentSettingNo(self):
        return self._currentSettingNo

    @property
    def totalRotations(self):
        return self._totalRotations

    @property
    def goniostatRotation(self):
        return self._goniostatRotation


class CentringDone(Payload):
    """Centering-done message"""

    INTENT = "DOCUMENT"

    def __init__(self, status, timestamp, goniostatTranslation):
        super(CentringDone, self).__init__()
        self._status = status
        self._timestamp = timestamp
        self._goniostatTranslation = goniostatTranslation

    @property
    def status(self):
        return self._status

    @property
    def timestamp(self):
        """Time in seconds since the epoch (Jan 1, 1970),
        as returned by time.time()"""
        return self._timestamp

    @property
    def goniostatTranslation(self):
        return self._goniostatTranslation


class SampleCentred(Payload):
    INTENT = "DOCUMENT"

    def __init__(self, data_model):

        super(SampleCentred, self).__init__()
        self._imageWidth = data_model.image_width
        self._transmission = 0.01 * data_model.transmission
        self._exposure = data_model.exposure_time
        self._wedgeWidth = data_model.wedge_width
        self._interleaveOrder = data_model.interleave_order
        self._beamstopSetting = data_model.beamstop_setting
        self._goniostatTranslations = frozenset(data_model.goniostat_translations)
        self._repetition_count = data_model.repetition_count

        if data_model.characterisation_done:
            self._wavelengths = tuple(data_model.wavelengths)
            self._detectorSetting = None
        else:
            # Ths trick assumes that characterisation and diffractcal
            # use one, the first, wavelength and default interleave order
            # Which is true. Not the ideal place to put this code
            # but it works.
            self._wavelengths = tuple((data_model.wavelengths[0],))
            self._detectorSetting = data_model.detector_setting

    @property
    def imageWidth(self):
        return self._imageWidth

    @property
    def transmission(self):
        return self._transmission

    @property
    def exposure(self):
        return self._exposure

    @property
    def interleaveOrder(self):
        return self._interleaveOrder

    @property
    def wedgeWidth(self):
        return self._wedgeWidth

    @property
    def beamstopSetting(self):
        return self._beamstopSetting

    @property
    def detectorSetting(self):
        return self._detectorSetting

    @property
    def goniostatTranslations(self):
        return self._goniostatTranslations

    @property
    def wavelengths(self):
        return self._wavelengths
    @property
    def repetition_count(self):
        return self._repetition_count
