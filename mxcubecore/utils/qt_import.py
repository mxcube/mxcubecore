# pylint: skip-file
"""

Description
--------------

This module import all symbols from PyQt in one single module
space

It also imports the *matplotlib* module and allow to check
version compatibility between PyQt and matplotbil

This module, on importing,  assigns the variables:

   qt_imported = [True,False]
   qt_version_no = <list of integers> example:  [4,8,1]
   qt_variant = ['PyQt5','PyQt4','PySide']

   mpl_imported = [True,False]
   mpl_version = <String as provided by matplotlib module>
   mpl_version_no = <list of integers> example:  [1,4,0]

Usage
-------------
This module could be imported directly instead of importing
PyQt.  But the original submodules in PyQt will be flattened.

For example::

   from PyQt4.QtCore import *
   from PyQt4.QtGui import *

   from PyQt5.QtCore import *
   from PyQt5.QtWidgets import *
   from PyQt5.QtGui import *

could be all replaced by::

   from qt_import import *

Or you could directly import things in this way::

  import qt_import as Qt
  app = Qt.QApplication([])

But import lines like::
   from qt_import import Qtcore

would fail (submodules are flattened)

To check the modules you are importing you can
directly use this module to print out a report::

   user@host: python qt_import.py
   Using PyQt:  PyQt4, version: 4.8.6
   Matplotlib:  PyQt4, version: 1.3.1
   Matplotlib is COMPATIBLE with PyQt




Credits
-------------
Inspired from code from "splot" (http://certif.com)
splot is licensed under LGPL license

"""
import os
import sys

qt_imported = False
qt_variant = None
qt_version_no = []

mpl_imported = False
mpl_version = None
mpl_version_no = False
#
#  Matplotlib import
#
try:
    import matplotlib

    mpl_imported = True
    mpl_version = matplotlib.__version__
    version_parts = mpl_version.split(".")
    mpl_major, mpl_minor = version_parts[:2]
    mpl_version_no = [int(mpl_major), int(mpl_minor), 0]

    if len(version_parts) > 2:
        try:
            import re

            rel = version_parts[2]
            m = re.search(r"(?P<release>\d+)", rel)
            if m:
                mpl_version_no[2] = int(m.group("release"))
        except BaseException:
            pass
except BaseException:
    pass

if "--pyqt5" in sys.argv:
    qt_variant = "PyQt5"
elif "--pyside" in sys.argv:
    qt_variant = "PySide"
elif "--pyqt4" in sys.argv:
    qt_variant = "PyQt4"
elif "--pyqt3" in sys.argv:
    qt_variant = "PyQt3"

#
# PyQt5
#
if (qt_variant == "PyQt5") or (qt_variant is None and not qt_imported):
    try:
        from PyQt5.QtCore import (
            PYQT_VERSION_STR,
            QT_VERSION_STR,
            QCoreApplication,
            QDir,
            QEvent,
            QEventLoop,
            QObject,
            QPoint,
            QPointF,
            QRect,
            QRectF,
            QRegExp,
            QSize,
            Qt,
            QTimer,
            pyqtSignal,
            pyqtSlot,
        )
        from PyQt5.QtGui import (
            QBrush,
            QColor,
            QContextMenuEvent,
            QCursor,
            QDoubleValidator,
            QFocusEvent,
            QFont,
            QIcon,
            QImage,
            QIntValidator,
            QKeyEvent,
            QKeySequence,
            QLinearGradient,
            QMouseEvent,
            QPainter,
            QPainterPath,
            QPalette,
            QPen,
            QPixmap,
            QPolygon,
            QRegExpValidator,
            QValidator,
        )
        from PyQt5.QtWidgets import (
            QAbstractItemView,
            QAction,
            QActionGroup,
            QApplication,
            QButtonGroup,
            QCheckBox,
            QColorDialog,
            QComboBox,
            QDesktopWidget,
            QDial,
            QDialog,
            QDoubleSpinBox,
            QFileDialog,
            QFrame,
            QGraphicsItem,
            QGraphicsPixmapItem,
            QGraphicsScene,
            QGraphicsView,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QHeaderView,
            QInputDialog,
            QLabel,
            QLayout,
            QLineEdit,
            QListView,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMenu,
            QMenuBar,
            QMessageBox,
            QProgressBar,
            QProgressDialog,
            QPushButton,
            QRadioButton,
            QScrollArea,
            QScrollBar,
            QSizePolicy,
            QSlider,
            QSpacerItem,
            QSpinBox,
            QSplashScreen,
            QSplitter,
            QStackedWidget,
            QStatusBar,
            QTableView,
            QTableWidget,
            QTableWidgetItem,
            QTabWidget,
            QTextBrowser,
            QTextEdit,
            QToolBar,
            QToolBox,
            QToolButton,
            QToolTip,
            QTreeView,
            QTreeWidget,
            QTreeWidgetItem,
            QTreeWidgetItemIterator,
            QVBoxLayout,
            QWhatsThis,
            QWidget,
        )
        from PyQt5.uic import loadUi

        QStringList = list
        getQApp = QCoreApplication.instance
        qApp = QCoreApplication.instance

        qt_imported = True
        qt_variant = "PyQt5"
        qt_version_no = list(map(int, QT_VERSION_STR.split(".")))
        _ver = PYQT_VERSION_STR.split(".")
        ver = _ver + ["0"] * (3 - len(_ver))
        pyqt_version_no = list(map(int, ver))[:3]
    except ImportError:
        pass

    try:
        from PyQt5.QtWebKit import QWebPage
    except ImportError:
        pass

#
# PyQt4
#
if (qt_variant == "PyQt4") or (qt_variant is None and not qt_imported):
    #
    # Maybe it is PyQt4 that you want
    #

    # force api 2 (so that the api is common for all pyqt versions)
    #   !! this means the classes below will not exist !!
    # but code is guaranteed to be compatible
    try:
        from PyQt4.QtCore import (
            PYQT_VERSION_STR,
            QT_VERSION_STR,
            SIGNAL,
            QDir,
            QEvent,
            QEventLoop,
            QObject,
            QPoint,
            QPointF,
            QRect,
            QRectF,
            QRegExp,
            QSize,
            QStringList,
            Qt,
            QTimer,
            QUrl,
            pyqtSignal,
            pyqtSlot,
        )
        from PyQt4.QtGui import (
            QAbstractItemView,
            QAction,
            QActionGroup,
            QApplication,
            QBrush,
            QButtonGroup,
            QCheckBox,
            QColor,
            QColorDialog,
            QComboBox,
            QContextMenuEvent,
            QCursor,
            QDesktopWidget,
            QDial,
            QDialog,
            QDoubleSpinBox,
            QDoubleValidator,
            QFileDialog,
            QFocusEvent,
            QFont,
            QFrame,
            QGraphicsItem,
            QGraphicsPixmapItem,
            QGraphicsScene,
            QGraphicsView,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QHeaderView,
            QIcon,
            QImage,
            QInputDialog,
            QIntValidator,
            QKeyEvent,
            QKeySequence,
            QLabel,
            QLayout,
            QLinearGradient,
            QLineEdit,
            QListView,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMenu,
            QMenuBar,
            QMessageBox,
            QMouseEvent,
            QPainter,
            QPainterPath,
            QPalette,
            QPen,
            QPixmap,
            QPolygon,
            QProgressBar,
            QProgressDialog,
            QPushButton,
            QRadioButton,
            QRegExpValidator,
            QScrollArea,
            QScrollBar,
            QSizePolicy,
            QSlider,
            QSpacerItem,
            QSpinBox,
            QSplashScreen,
            QSplitter,
            QStackedWidget,
            QStatusBar,
            QTableView,
            QTableWidget,
            QTableWidgetItem,
            QTabWidget,
            QTextBrowser,
            QTextEdit,
            QToolBar,
            QToolBox,
            QToolButton,
            QToolTip,
            QTreeView,
            QTreeWidget,
            QTreeWidgetItem,
            QTreeWidgetItemIterator,
            QValidator,
            QVBoxLayout,
            QWhatsThis,
            QWidget,
            qApp,
        )
        from PyQt4.uic import loadUi

        def getQApp():
            return qApp

        qt_imported = True
        qt_variant = "PyQt4"
        qt_version_no = list(map(int, QT_VERSION_STR.split(".")))
        _ver = PYQT_VERSION_STR.split(".")
        ver = _ver + ["0"] * (3 - len(_ver))
        pyqt_version_no = list(map(int, ver))[:3]
    except BaseException:
        pass

    try:
        from PyQt4.QtWebKit import QWebPage
    except ImportError:
        pass

#
# PySide
#
if (qt_variant == "PySide") or (qt_variant is None and not qt_imported):
    #
    # Finally try PySide (not fully tested)
    #
    try:
        from PySide import __version_info__

        pyqt_version_no = __version_info__[:3]
        from PySide.QtCore import __version_info__

        qt_version_no = __version_info__[:3]

        from PySide.QtCore import *
        from PySide.QtGui import *
        from PySide.QtSvg import *
        from PySide.QtUiTools import *
        from PySide.QtWebKit import *

        pyqtSignal = Signal
        pyqtSlot = Slot
        qt_imported = True
        qt_variant = "PySide"
        getQApp = QCoreApplication.instance

        def loadUi(filename, parent=None):
            loader = QUiLoader()
            uifile = QFile(filename)
            uifile.open(QFile.ReadOnly)
            ui = loader.load(uifile, parent)
            uifile.close()
            return ui

    except BaseException:
        pass

#
#  Matplotlib backend assignment
#
if mpl_imported:
    if qt_variant == "PyQt5":
        if mpl_version_no < [1, 4, 0]:
            mpl_compat = False
        else:
            mpl_compat = True
            matplotlib.use("Qt5Agg")

    elif qt_variant == "PySide":
        if mpl_version_no < [1, 1, 0]:
            mpl_compat = False
        else:
            mpl_compat = True
            matplotlib.use("Qt4Agg")
            from matplotlib import rcParams

            rcParams["backend.qt4"] = "PySide"

    elif qt_variant == "PyQt4":
        mpl_compat = True
        matplotlib.use("Qt4Agg")

if "QString" not in globals():
    QString = str

"""
if qt_imported:
    print("Using PyQt:  %s" % (qt_variant))
    print("   qt version: %s / pyqt version: %s" % ("%d.%d.%d" % tuple(qt_version_no), "%d.%d.%d" % tuple(pyqt_version_no)))
else:
    print("Cannot import PyQt")

if mpl_imported:
    print("Matplotlib version: %s" % "%d.%d.%d" % tuple(mpl_version_no))
else:
    print("Cannot import matplotlib")

if qt_imported and mpl_imported:
    if mpl_compat:
        print("  Matplotlib is COMPATIBLE with PyQt")
    else:
        print("  !!! Matplotlib is NOT COMPATIBLE with PyQt !!!")
"""

if qt_variant in ("PyQt4", "PyQt5", "PySide"):
    # QHeaderView is not defined for Qt3, so the import broke without the 'if'
    class RotatedHeaderView(QHeaderView):
        def __init__(self, parent=None):
            super(RotatedHeaderView, self).__init__(Qt.Horizontal, parent)
            self.setMinimumSectionSize(22)

        def paintSection(self, painter, rect, logicalIndex):
            painter.save()
            # translate the painter such that rotate will rotate around the correct
            # point
            painter.translate(rect.x() + rect.width(), rect.y())
            painter.rotate(90)
            # and have parent code paint at this location
            newrect = QRect(0, 0, rect.height(), rect.width())
            super(RotatedHeaderView, self).paintSection(painter, newrect, logicalIndex)
            painter.restore()

        def minimumSizeHint(self):
            size = super(RotatedHeaderView, self).minimumSizeHint()
            size.transpose()
            return size

        def sectionSizeFromContents(self, logicalIndex):
            size = super(RotatedHeaderView, self).sectionSizeFromContents(logicalIndex)
            size.transpose()
            return size

    class QDoubleSlider(QSlider):

        doubleValueChanged = pyqtSignal(float)

        def __init__(self, orientation=Qt.Horizontal, parent=None):
            super(QSlider, self).__init__(orientation, parent)
            self.decimals = 5
            self._max_int = 10**self.decimals

            super(QSlider, self).setMinimum(0)
            super(QSlider, self).setMaximum(self._max_int)

            self._min_value = 0.0
            self._max_value = 1.0

            self.valueChanged.connect(self.value_changed)

        def value_changed(self, value):
            self.doubleValueChanged.emit(value / float(self._max_int))

        @property
        def _value_range(self):
            return self._max_value - self._min_value

        def value(self):
            return (
                float(super(QSlider, self).value()) / self._max_int * self._value_range
                + self._min_value
            )

        def setValue(self, value):
            super(QSlider, self).setValue(
                int((value - self._min_value) / self._value_range * self._max_int)
            )

        def setMinimum(self, value):
            if value > self._max_value:
                raise ValueError("Minimum limit cannot be higher than maximum")

            self._min_value = value
            # self.setValue(self.value())

        def setMaximum(self, value):
            if value < self._min_value:
                raise ValueError("Minimum limit cannot be higher than maximum")

            self._max_value = value
            # self.setValue(self.value())

        def minimum(self):
            return self._min_value

        def maximum(self):
            return self._max_value


def load_ui_file(filename):
    current_path = os.path.dirname(os.path.abspath(__file__)).split(os.sep)
    current_path = os.path.join(*current_path[1:-1])
    return loadUi(os.path.join("/", current_path, "ui_files", filename))
