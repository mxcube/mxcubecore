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
along with MXCuBE.  If not, see <https://www.gnu.org/licenses/>.
"""

import uuid
from collections import OrderedDict
from collections import namedtuple

__copyright__ = """ Copyright © 2016 - 2019 by Global Phasing Ltd. """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"


# Enumerations

# MessageIntents = ('INSTRUCTION', 'QUERY', 'RESPONSE', 'ACKNOWLEDGEMENT',
#                   'INFO', )
_MessageIntents = ["DOCUMENT", "COMMAND", "EVENT"]

MessageIntents = dict((x, x) for x in _MessageIntents)

IndexingFormats = ("IDXREF",)

AbsorptionEdges = ("K", "LI", "LII", "LIII", "MI", "MII", "MIII", "MIV", "MV")
# # Currently not used
# WavelengthRoles = OrderedDict((('PEAK','Peak'),('REMOTE','Remote'),
#                                ('RINF','Rising inflection'),
#                                ('FINF','Falling inflection'),
#                                ('HREM','High-energy remote'),
#                               ))

ChemicalElements = OrderedDict(
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

CentringStatus = ("NEXT", "DONE")

CrystalSystems = (
    "TRICLINIC",
    "MONOCLINIC",
    "ORTHORHOMBIC",
    "TETRAGONAL",
    "TRIGONAL",
    "HEXAGONAL",
    "CUBIC",
)
# Map from single letter code tro Crystal system name
# # NB trigonal and hexagonal DO both have code 'h'
crystalSystemMap = dict(zip("amothhc", CrystalSystems))

PointGroups = ("1", "2", "222", "4", "422", "6", "622", "32", "23", "432")

ParsedMessage = namedtuple(
    "ParsedMessage", ("message_type", "payload", "enactment_id", "correlation_id")
)


# Abstract classes


class MessageData(object):
    """Topmost superclass for all message data objects

    Later to add e.g. stringification"""


class Payload(MessageData):
    """Payload - top level message object"""

    _intent = None

    def __init__(self):

        # This class is abstract
        intent = self.__class__._intent
        if intent not in MessageIntents:
            if intent is None:
                raise RuntimeError("Attempt to instantiate abstract class Payload")
            else:
                raise RuntimeError(
                    "Programming error - "
                    "Payload subclass %s intent %s must be one of: %s"
                    % (self.__class__.__name__, intent, sorted(MessageIntents.keys))
                )

    @property
    def intent(self):
        """Message intent - class-level property"""
        return self.__class__._intent


class IdentifiedElement(MessageData):
    """Object with persistent uuid"""

    def __init__(self, id=None):

        # This class is abstract
        if self.__class__.__name__ == "IdentifiedElement":
            raise RuntimeError(
                "Attempt to instantiate abstract class IdentifiedElement"
            )

        self._id = None
        self.__setId(id)

    @property
    def id(self):
        """Unique identifier (UUID) for IdentifiedElement.
        Defaults to new, time-based uuid"""
        return self._id

    def __setId(self, value):
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

    _intent = "COMMAND"


class ObtainPriorInformation(Payload):
    """Prior information request"""

    _intent = "COMMAND"


class PrepareForCentring(Payload):
    """Prior information request"""

    _intent = "COMMAND"


class ReadyForCentring(Payload):
    """Prior information request"""

    _intent = "DOCUMENT"


class SubprocessStopped(Payload):
    """Subprocess Stopped request message"""

    _intent = "EVENT"


class ConfigurationData(Payload):
    """Configuration Data message"""

    _intent = "DOCUMENT"

    # NB coded as mandatory, even if not explicitly non-null
    # (but raises MalformedUrlException) in Java.

    def __init__(self, location):
        self._location = location

    @property
    def location(self):
        """Url for directory containing configuration data.
        Generally an absolute file path."""
        return self._location


class SubprocessStarted(Payload):
    """Subprocess Started message"""

    _intent = "EVENT"

    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        """name of subprocess"""
        return self._name


class ChooseLattice(Payload):
    """Choose lattice instruction"""

    _intent = "COMMAND"

    def __init__(self, format, solutions, crystalSystem=None, lattices=None):
        if format in IndexingFormats:
            self._format = format
        else:
            raise ValueError(
                "Indexing format %s not in supported formats: %s"
                % (format, IndexingFormats)
            )
        if not lattices:
            self._lattices = ()
        elif isinstance(lattices, str):
            # Allows you to pass in lattices as a string without silly errors
            self._lattices = frozenset((lattices,))
        else:
            self._lattices = frozenset(lattices)
        self._solutions = solutions
        self._crystalSystem = crystalSystem

    @property
    def format(self):
        """format of solutions string"""
        return self._format

    @property
    def crystalSystem(self):
        """One-letter code for crystal system (one of 'amothhc')"""
        return self._crystalSystem

    @property
    def lattices(self):
        """Expected lattices for solution"""
        return self._lattices

    @property
    def solutions(self):
        """String containing proposed solutions"""
        return self._solutions


class SelectedLattice(MessageData):
    """Lattice selected message"""

    _intent = "DOCUMENT"

    def __init__(self, format, solution):
        if format in IndexingFormats:
            self._format = format
        else:
            raise ValueError(
                "Indexing format %s not in supported formats: %s"
                % (format, IndexingFormats)
            )
        self._solution = tuple(solution)

    @property
    def format(self):
        """format of solutions string"""
        return self._format

    @property
    def solution(self):
        """Tuple of strings containing proposed solution"""
        return self._solution


class CollectionDone(MessageData):
    """Collection Done message"""

    _intent = "EVENT"

    def __init__(self, proposalId, status, imageRoot=None):
        self._proposalId = proposalId
        self._imageRoot = imageRoot
        self._status = status

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


# Complex payloads


class WorkflowDone(Payload):
    """End-of-workflow message"""

    _intent = "EVENT"

    def __init__(self, issues=None):

        super(WorkflowDone, self).__init__()

        if self.__class__.__name__ == "WorkflowDone":
            raise RuntimeError("Attempt to instantiate abstract class WorkflowDone")

        if issues:
            ll = list(x for x in issues if not isinstance(x, Issue))
            if ll:
                raise ValueError("issues parameter contains non-issues: %s" % ll)
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

    _intent = "COMMAND"


# Simple data objects


class AnomalousScatterer(MessageData):
    def __init__(self, element, edge):

        if element in ChemicalElements:
            self._element = element
        else:
            raise ValueError("Chemical element code %s not recognised" % element)

        if edge in AbsorptionEdges:
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

    def __init__(self, component, message, code=None, id=None):
        IdentifiedElement.__init__(self, id)
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

    def __init__(self, wavelength, role=None, id=None):
        IdentifiedElement.__init__(self, id)
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


class BeamSetting(IdentifiedElement):
    """Beam setting"""

    def __init__(self, wavelength, id=None):
        IdentifiedElement.__init__(self, id)
        self._wavelength = wavelength

    @property
    def wavelength(self):
        """Wavelength setting for beam"""
        return self._wavelength


class ScanExposure(IdentifiedElement):
    """Scan Exposure"""

    def __init__(self, time, transmission, id=None):
        IdentifiedElement.__init__(self, id)
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

    def __init__(self, imageWidth, numImages, id=None):
        IdentifiedElement.__init__(self, id)
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

    def __init__(self, id=None, **axisSettings):

        super(PositionerSetting, self).__init__(id=id)

        if self.__class__.__name__ == "PositionerSetting":
            # This class is abstract
            raise RuntimeError(
                "Programming error - attempt to instantiate abstract class PositionerSetting"
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

    def __init__(self, resolution, id=None, orgxy=(), **axisSettings):
        PositionerSetting.__init__(self, id=id, **axisSettings)
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

    def __init__(self, id=None, **axisSettings):
        PositionerSetting.__init__(self, id=id, **axisSettings)
        self._translation = None

    @property
    def translation(self):
        """GoniostatTranslation corresponding to self

        NB This link can be set only by GoniostatTranslation.__init__"""
        return self._translation


class GoniostatSweepSetting(GoniostatRotation):
    """Goniostat Sweep setting"""

    def __init__(self, scanAxis, id=None, **axisSettings):
        GoniostatRotation.__init__(self, id=id, **axisSettings)
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
          (requestedRotationId is None or requestedRotationId == rotation.id):
        self.requestedRotationId = rotation.id
        self.newRotation = None"""

    def __init__(
        self, rotation=None, requestedRotationId=None, id=None, **axisSettings
    ):
        PositionerSetting.__init__(self, id=id, **axisSettings)

        if rotation is None:
            if requestedRotationId is None:
                raise ValueError("rotation and requestedRotationId cannot both be None")
            else:
                self._newRotation = None
                self._requestedRotationId = requestedRotationId
        else:
            if requestedRotationId is None or requestedRotationId == rotation.id:
                self._newRotation = None
                self._requestedRotationId = rotation.id
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

    def __init__(
        self,
        scatterers=(),
        lattice=None,
        pointGroup=None,
        spaceGroup=None,
        cell=None,
        expectedResolution=None,
        isAnisotropic=None,
    ):

        self._scatterers = scatterers
        self._lattice = lattice
        self._pointGroup = pointGroup
        self._spaceGroup = spaceGroup
        self._cell = cell
        self._expectedResolution = expectedResolution
        self._isAnisotropic = isAnisotropic

    @property
    def scatterers(self):
        return self._scatterers

    @property
    def lattice(self):
        return self._lattice

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
        id=None,
    ):

        super(Sweep, self).__init__(id=id)

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

    def _addScan(self, scan):
        """Implementation method. *Only* to be called from Scan.__init__"""
        self._scans.add(scan)

    def get_initial_settings(self):
        """Get dictionary of rotation motor settings for start of sweep"""

        sweepSetting = self.goniostatSweepSetting
        result = dict(sweepSetting.axisSettings)
        translation = sweepSetting.translation
        if translation is not None:
            result.update(translation.axisSettings)
        result[sweepSetting.scanAxis] = self.start
        #
        return result


class Scan(IdentifiedElement):
    """Collection strategy Scan"""

    def __init__(
        self, width, exposure, imageStartNum, start, sweep, filenameParams, id=None
    ):

        super(Scan, self).__init__(id=id)

        self._filenameParams = dict(filenameParams)

        self._width = width
        self._exposure = exposure
        self._imageStartNum = imageStartNum
        self._start = start

        sweep._addScan(self)
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

    _intent = "COMMAND"

    def __init__(
        self,
        isInterleaved,
        isUserModifiable,
        defaultDetectorSetting,
        defaultBeamSetting,
        allowedWidths=(),
        defaultWidthIdx=None,
        sweeps=(),
        id=None,
    ):

        super(GeometricStrategy, self).__init__(id=id)

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

    @property
    def isInterleaved(self):
        return self._isInterleaved

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

        WARNING we do not have the necessary information.
        So we sort in increasing order by angles, in alphabetical name order,
        (in pracite, 'kappa', 'kappa_phi', 'phi')
        HORRIBLE HACK, but as it happens this will give
        at least the first one correct mostly
        and anyway is the best approximation we have

        TODO get this right, once the workflow allows"""
        ll = []
        for sweep in self._sweeps:
            dd = sweep.get_initial_settings()
            ll.append((tuple(dd[x] for x in sorted(dd)), sweep))
        #
        return list(tt[1] for tt in sorted(ll))


class CollectionProposal(IdentifiedElement, Payload):
    """Collection proposal """

    _intent = "COMMAND"

    def __init__(self, relativeImageDir, strategy, scans, id=None):

        super(CollectionProposal, self).__init__(id=id)

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

    _intent = "DOCUMENT"

    def __init__(
        self, sampleId, sampleName=None, rootDirectory=None, userProvidedInfo=None
    ):

        if isinstance(sampleId, uuid.UUID):
            self._sampleId = sampleId
        else:
            raise TypeError("sampleId input must be of type uuid.UUID")

        self._sampleName = sampleName
        # Draft in API, not currently coded in Java:
        # self._referenceFile = referenceFile
        self._rootDirectory = rootDirectory
        self._userProvidedInfo = userProvidedInfo

    @property
    def sampleId(self):
        return self._sampleId

    @property
    def sampleName(self):
        return self._sampleName

    # @property
    # def referenceFile(self):
    #     return self._referenceFile

    @property
    def rootDirectory(self):
        return self._rootDirectory

    @property
    def userProvidedInfo(self):
        return self._userProvidedInfo


class RequestCentring(Payload):
    """Request for centering"""

    _intent = "COMMAND"

    def __init__(self, currentSettingNo, totalRotations, goniostatRotation):
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

    _intent = "DOCUMENT"

    def __init__(self, status, timestamp, goniostatTranslation):
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
    _intent = "DOCUMENT"

    def __init__(
        self,
        imageWidth,
        transmission,
        exposure,
        interleaveOrder="",
        wedgeWidth=None,
        beamstopSetting=None,
        detectorSetting=None,
        goniostatTranslations=(),
        wavelengths=(),
    ):

        self._imageWidth = imageWidth
        self._transmission = transmission
        self._exposure = exposure
        self._interleaveOrder = interleaveOrder
        self._wedgeWidth = wedgeWidth
        self._beamstopSetting = beamstopSetting
        self._detectorSetting = detectorSetting
        self._goniostatTranslations = frozenset(goniostatTranslations)
        self._wavelengths = frozenset(wavelengths)

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
