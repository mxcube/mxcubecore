# coding: utf-8
# /*##########################################################################
# Copyright (C) 2017 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ############################################################################*/
import pylab
import matplotlib.pyplot as pyplot
"""
Workflow library module for grid / mesh
"""

__author__ = "Olof Svensson"
__contact__ = "svensson@esrf.eu"
__copyright__ = "ESRF, 2017"
__updated__ = "2017-06-23"


import os
import numpy
import logging
import scipy.misc
import scipy.ndimage

import matplotlib
matplotlib.use('Agg', warn=False)

logging.basicConfig(level=logging.INFO)


def getAutoMesh(background_image, snapshot_list, beam_size,
                pixels_per_mm, debug=False, findLargestMesh=True):
    dictLoop = {}
    omega_list = []
    autoMeshWorkingDir = "/tmp/mxcube/automesh"

    for snapshot in snapshot_list:
        differenceImage = numpy.abs(background_image - snapshot["image"])
        filteredImage = filterDifferenceImage(differenceImage)
        (listIndex, listUpper, listLower) = loopExam(filteredImage)
        dictLoop["%d" % snapshot["omega"]] = (listIndex, listUpper, listLower)
        omega_list.append(snapshot["omega"])

    areTheSameImage = checkForCorrelatedImages(dictLoop)
    ny, nx = background_image.shape
    (angleMinThickness, x1Pixels, y1Pixels, dxPixels, dyPixels, deltaPhiz, stdPhiz) = \
        findOptimalMesh(dictLoop, nx, ny,
                        autoMeshWorkingDir=autoMeshWorkingDir,
                        debug=debug,
                        loopMaxWidth=300, loopMinWidth=150,
                        findLargestMesh=findLargestMesh,
                        omega_list=omega_list)

    deltaPhizPixels = 0.0
    xOffsetLeft = 0.05
    xOffsetRight = 0.05
    overSamplingX = 1.5
    overSamplingY = 1.5
    x1 = x1Pixels / pixels_per_mm[0] - xOffsetLeft
    y1 = -(y1Pixels + dyPixels + deltaPhizPixels) / pixels_per_mm[1]
    dx_mm = dxPixels / pixels_per_mm[0] + xOffsetLeft + xOffsetRight
    dy_mm = dyPixels / pixels_per_mm[1]
    steps_x = int(
        (dxPixels /
         pixels_per_mm[0] +
         xOffsetLeft +
         xOffsetRight) /
        beam_size[0] *
        overSamplingX)
    steps_y = int(dyPixels / pixels_per_mm[1] / beam_size[1] * overSamplingY)
    grid_info = {"x1": x1,
                 "y1": y1,
                 "dx_mm": dx_mm,
                 "dy_mm": dy_mm,
                 "steps_x": steps_x,
                 "steps_y": steps_y}

    (x1Pixels, y1Pixels, dxPixels, dyPixels) = gridInfoToPixels(grid_info, pixels_per_mm)
    imgshape = background_image.shape
    ny, nx = imgshape
    meshXmin = nx / 2 + x1Pixels
    meshYmin = ny / 2 + y1Pixels
    meshXmax = meshXmin + dxPixels
    meshYmax = meshYmin - dyPixels

    print imgshape
    print meshXmin, meshXmax, meshYmin, meshYmax
    grid_info["center_x"] = meshXmin + (meshXmax - meshXmin) / 2
    grid_info["center_y"] = meshYmin + (meshYmax - meshYmin) / 2
    grid_info["angle"] = angleMinThickness

    print("Auto grid_info: %r" % grid_info)

    return grid_info


def autoMesh(snapshotDir, workflowWorkingDir, autoMeshWorkingDir, loopMaxWidth=300,
             loopMinWidth=150, prefix="snapshot", debug=False, findLargestMesh=False):
    os.chmod(autoMeshWorkingDir, 0o755)
    background_image = os.path.join(snapshotDir, "%s_background.png" % prefix)
    dictLoop = {}
    for omega in [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]:
        logging.info("Analysing snapshot image at omega = %d degrees" % omega)
        imagePath = os.path.join(snapshotDir, "%s_%03d.png" % (prefix, omega))
        raw_img = readImage(imagePath)

        if debug:
            plot_img(
                raw_img,
                os.path.join(
                    autoMeshWorkingDir,
                    "rawImage_%03d.png" %
                    omega))

        if background_image.endswith(".npy"):
            background = numpy.load(background_image)
        else:
            background = scipy.misc.imread(background_image, flatten=True)

        differenceImage = numpy.abs(background - raw_img)

        if debug:
            plot_img(
                differenceImage,
                plotPath=os.path.join(
                    autoMeshWorkingDir,
                    "differenceImage_%03d.png" %
                    omega))

        filteredImage = filterDifferenceImage(differenceImage)
        if debug:
            plot_img(
                filteredImage,
                plotPath=os.path.join(
                    autoMeshWorkingDir,
                    "filteredImage_%03d.png" %
                    omega))
        (listIndex, listUpper, listLower) = loopExam(filteredImage)
        if debug:
            pylab.plot(listIndex, listUpper, '+')
            pylab.plot(listIndex, listLower, '+')
            raw_img = scipy.misc.imread(imagePath, flatten=True)
            imgshape = raw_img.shape
            extent = (0, imgshape[1], 0, imgshape[0])
            pylab.axes(extent)
            pylab.savefig(
                os.path.join(
                    autoMeshWorkingDir,
                    "shapePlot_%03d.png" %
                    omega))
            pyplot.close()
        dictLoop["%d" % omega] = (listIndex, listUpper, listLower)
    areTheSameImage = checkForCorrelatedImages(dictLoop)
    image000Path = os.path.join(snapshotDir, "%s_%03d.png" % (prefix, 0))
    ny, nx = scipy.misc.imread(image000Path, flatten=True).shape
    (angleMinThickness, x1Pixels, y1Pixels, dxPixels, dyPixels, deltaPhiz, stdPhiz) = findOptimalMesh(dictLoop, nx, ny, autoMeshWorkingDir, debug=debug,
                                                                                                      loopMaxWidth=loopMaxWidth, loopMinWidth=loopMinWidth,
                                                                                                      findLargestMesh=findLargestMesh)
    imagePath = None
    if angleMinThickness is not None:
        imagePath = os.path.join(
            snapshotDir, "%s_%03d.png" %
            (prefix, angleMinThickness))
    return (angleMinThickness, x1Pixels, y1Pixels, dxPixels,
            dyPixels, deltaPhiz, stdPhiz, imagePath, areTheSameImage)


def subtractBackground(image, backgroundImage):
    return numpy.abs(image - backgroundImage)


def filterDifferenceImage(differenceImage, thresholdValue=30):
    """
    First applies a threshold of default value 30. Then erodes the image twice, and then dilates the
    image twice.
    """
    thresholdValue = 30
    binaryImage = (differenceImage >= thresholdValue)
    filteredImage = scipy.ndimage.morphology.binary_erosion(
        binaryImage).astype(binaryImage.dtype)
    filteredImage = scipy.ndimage.morphology.binary_erosion(
        filteredImage).astype(binaryImage.dtype)
    filteredImage = scipy.ndimage.morphology.binary_dilation(
        filteredImage).astype(binaryImage.dtype)
    filteredImage = scipy.ndimage.morphology.binary_dilation(
        filteredImage).astype(binaryImage.dtype)
    return filteredImage


def loopExam(filteredImage):
    """
    This method examines the loop in one image.

    """
    ny, nx = filteredImage.shape
    shapeListIndex = []
    shapeListUpper = []
    shapeListLower = []
    for indexX in range(nx):
        column = filteredImage[:, indexX]
        indices = numpy.where(column)[0]
        if len(indices) > 0:
            shapeListIndex.append(indexX)
            shapeListUpper.append(indices[0])
            shapeListLower.append(indices[-1])
    arrayIndex = numpy.array(shapeListIndex)
    arrayUpper = ny - numpy.array(shapeListUpper)
    arrayLower = ny - numpy.array(shapeListLower)
    return (arrayIndex.tolist(), arrayUpper.tolist(), arrayLower.tolist())


def checkForCorrelatedImages(dictLoop):
    # Check if all the indices are the same
    firstListIndex = None
    firstUpperIndex = None
    firstLowerIndex = None
    areTheSame = True
    for loopIndex in dictLoop:
        listIndex, listUpper, listLower = dictLoop[loopIndex]
        if firstListIndex is None:
            firstListIndex = listIndex
            firstUpperIndex = listUpper
            firstLowerIndex = listLower
        elif cmp(firstListIndex, listIndex):
            areTheSame = False
            break
        elif cmp(firstUpperIndex, listUpper):
            areTheSame = False
            break
        elif cmp(firstLowerIndex, listLower):
            areTheSame = False
            break
    return areTheSame


def findOptimalMesh(dictLoop, nx, ny, autoMeshWorkingDir=None, loopMaxWidth=300, loopMinWidth=150,
                    debug=False, findLargestMesh=False, omega_list=None):
    if omega_list is None:
        omega_list = [0, 30, 60, 90, 120, 150, 180, 210, 270, 300, 330]
    arrayPhiz = None
    minThickness = None
    angleMinThickness = None
    maxThickness = None
    angleMaxThickness = None
    meshXmax = None
    stdPhiz = None
    loopMinWidth = int(loopMinWidth)
    loopMaxWidth = int(loopMaxWidth)

    for omega in omega_list[:len(omega_list) / 2]:
        print omega, omega + 180
        strOmega1 = "%d" % omega
        strOmega2 = "%03d" % (omega + 180)
        (listIndex1, listUpper1, listLower1) = dictLoop[strOmega1]
        (listIndex2, listUpper2, listLower2) = dictLoop[strOmega2]
        arrayIndex1 = numpy.array(listIndex1)
        arrayIndex2 = numpy.array(listIndex2)
        if len(arrayIndex1) == 0 or len(arrayIndex2) == 0:
            break
        if meshXmax is None:
            meshXmax = numpy.max(arrayIndex1)
        elif meshXmax > numpy.max(arrayIndex1):
            meshXmax = numpy.max(arrayIndex1)
        if meshXmax > numpy.max(arrayIndex2):
            meshXmax = numpy.max(arrayIndex2)
    if meshXmax is None:
        meshXmax = loopMaxWidth
    meshXmin = meshXmax - loopMaxWidth
    nPhi = 0
    for omega in omega_list[:len(omega_list) / 2]:
        strOmega1 = "%d" % omega
        strOmega2 = "%03d" % (omega + 180)
        (arrayIndex1, arrayUpper1, arrayLower1) = dictLoop[strOmega1]
        (arrayIndex2, arrayUpper2, arrayLower2) = dictLoop[strOmega2]
        arrayIndex = numpy.arange(meshXmin, meshXmax - 1)
        # Exclude regio in horizontal center
        xExcludMin = numpy.float64(nx / 2 - 20)
        xExcludMax = numpy.float64(nx / 2 + 20)
        indices1 = numpy.where(((arrayIndex1 > meshXmin) & (arrayIndex1 < xExcludMin)) |
                               ((arrayIndex1 < meshXmax) & (arrayIndex1 > xExcludMax)))
        indices2 = numpy.where(((arrayIndex2 > meshXmin) & (arrayIndex2 < xExcludMin)) |
                               ((arrayIndex2 < meshXmax) & (arrayIndex2 > xExcludMax)))
        arrayUpper1 = numpy.array(arrayUpper1)[indices1]
        arrayUpper2 = numpy.array(arrayUpper2)[indices2]
        arrayLower1 = numpy.array(arrayLower1)[indices1]
        arrayLower2 = numpy.array(arrayLower2)[indices2]
        if debug:
            pylab.plot(arrayUpper1, '+', color="red")
            pylab.plot(arrayUpper2, '+', color="blue")
            pylab.plot(arrayLower1, '+', color="red")
            pylab.plot(arrayLower2, '+', color="blue")
            pylab.savefig(
                os.path.join(
                    autoMeshWorkingDir, "shapePlot_%03d_%03d.png" %
                    (omega, omega + 180)))
            pylab.close()
        phiz = None
        if (arrayUpper1.shape == arrayLower2.shape) and (
                arrayUpper2.shape == arrayLower1.shape):
            phiz1 = (arrayUpper1 + arrayLower2) / 2.0
            phiz2 = (arrayUpper2 + arrayLower1) / 2.0
            phiz = (phiz1 + phiz2) / 2.0
        elif arrayUpper1.shape == arrayLower2.shape:
            phiz = (arrayUpper1 + arrayLower2) / 2.0
        elif arrayUpper2.shape == arrayLower1.shape:
            phiz = (arrayUpper2 + arrayLower1) / 2.0
        if phiz is not None:
            if debug:
                pylab.plot(phiz, "+")
                pylab.savefig(
                    os.path.join(
                        autoMeshWorkingDir, "phiz_%03d_%03d.png" %
                        (omega, omega + 180)))
                pylab.close()
            if arrayPhiz is None:
                arrayPhiz = numpy.array(phiz)
                nPhi += 1
            else:
                if arrayPhiz.shape == phiz.shape:
                    arrayPhiz += phiz
                    nPhi += 1
    if nPhi > 0:
        arrayPhiz /= nPhi
        # Cut off 20 points from each side of array in order to remove artifacts
        # at end points
        arrayPhiz = arrayPhiz[20:-20]
        arrayIndexPhiz = arrayIndex[20:-20]
        if debug:
            pylab.plot(arrayPhiz, "+")
            strPhizPath = os.path.join(autoMeshWorkingDir, "phiz.png")
            pylab.savefig(strPhizPath)
            pylab.close()
        averagePhiz = numpy.mean(arrayPhiz)
        stdPhiz = numpy.std(arrayPhiz)
        deltaPhiz = ny / 2 - averagePhiz
    else:
        averagePhiz = None
        deltaPhiz = None
    # Sample thickness
    listThicknessIndex = []
    for omega in omega_list:
        strOmega = "%d" % omega
        (arrayIndex, arrayUpper, arrayLower) = dictLoop[strOmega]
        indices = numpy.where((arrayIndex > meshXmin) & (arrayIndex < meshXmax))
        arrayUpper = numpy.array(arrayUpper)[indices]
        arrayLower = numpy.array(arrayLower)[indices]
        arrayThickness = arrayUpper - arrayLower
        # Look for a minima between 100 and 300 pixels from the right:
        arrayThicknessCrop = arrayThickness[-loopMaxWidth:-loopMinWidth]
        indicesThicknessCrop = indices[0][-loopMaxWidth:-loopMinWidth]
        if debug:
            pylab.plot(arrayUpper, "-")
            pylab.plot(arrayLower, "*")
            pylab.plot(arrayThicknessCrop, "+")
            strPhizPath = os.path.join(
                autoMeshWorkingDir,
                "thickness_%s.png" %
                strOmega)
            pylab.savefig(strPhizPath)
            pylab.close()
        if len(arrayThicknessCrop) > 0:
            tmpMin = numpy.argmin(arrayThicknessCrop)
#            if tmpMin > 75:
#                tmpMin = 75
            indexMin = indicesThicknessCrop[tmpMin]
            # Minimum mesh length: 150 pixels
            listThicknessIndex.append(indexMin)
            logging.debug("Index min: %d for omega = %d" % (indexMin, omega))
    logging.debug("List of thicknesses: %r" % listThicknessIndex)
    if not findLargestMesh and len(listThicknessIndex) > 0:
        maxIndexThickness = max(listThicknessIndex)
        meshXmin = maxIndexThickness
        logging.debug("Max index for thickess: %d" % maxIndexThickness)
    else:
        meshXmin = meshXmax - loopMaxWidth
        if meshXmin < 0:
            meshXmin = 0
    logging.debug("meshXmin: %d" % meshXmin)
    minThicknessMeshYmin = None
    minThicknessMeshYmax = None
    maxThicknessMeshYmin = None
    maxThicknessMeshYmax = None
    for omega in omega_list:
        strOmega = "%d" % omega
        (arrayIndex, arrayUpper, arrayLower) = dictLoop[strOmega]
        indices = numpy.where((arrayIndex > meshXmin) & (arrayIndex < meshXmax))
        arrayUpper = numpy.array(arrayUpper)[indices]
        arrayLower = numpy.array(arrayLower)[indices]
        if len(arrayLower) == 0 or len(arrayUpper) == 0:
            break
        maxThick = numpy.max(arrayUpper) - numpy.min(arrayLower)
        if maxThick > 400:
            # Ignored
            pass
        else:
            arrayIndex = numpy.arange(meshXmin, meshXmax - 1)
            if minThickness is None or minThickness > maxThick:
                minThickness = maxThick
                angleMinThickness = omega
                minThicknessMeshYmin = numpy.min(arrayLower)
                minThicknessMeshYmax = numpy.max(arrayUpper)
    #             if True:
    #                 pylab.plot(arrayUpper, '+')
    #                 pylab.plot(arrayLower, '+')
    #                 pylab.show()
            if maxThickness is None or maxThickness < maxThick:
                maxThickness = maxThick
                angleMaxThickness = omega
                maxThicknessMeshYmin = numpy.min(arrayLower)
                maxThicknessMeshYmax = numpy.max(arrayUpper)
    meshXmin -= 50
    logging.debug(
        "Max thickness = %r pxiels at omega %r" %
        (maxThickness, angleMaxThickness))
    logging.debug("Mesh: xMin=%r, xMax=%r, yMin=%r, yMax = %r" %
                  (meshXmin, meshXmax, maxThicknessMeshYmin, maxThicknessMeshYmax))
    logging.debug(
        "Min thickness = %r pixels at omega %r" %
        (minThickness, angleMinThickness))
    logging.debug("Mesh: xMin=%r, xMax=%r, yMin=%r, yMax = %r" %
                  (meshXmin, meshXmax, minThicknessMeshYmin, minThicknessMeshYmax))
    if meshXmin < 10:
        meshXmin = 10
    if deltaPhiz is not None:
        logging.debug("Average delta phiz: %.4f pixels" % deltaPhiz)
        logging.debug("Std delta phiz: %.4f pixels" % stdPhiz)
    else:
        logging.warning("Delta phiz could not be determined!")

    x1Pixels = meshXmin - nx / 2
    dxPixels = meshXmax - meshXmin
    y1Pixels = None
    dyPixels = None
    angle = None
    if (minThicknessMeshYmin is not None) and \
        (minThicknessMeshYmax is not None) and \
        (maxThicknessMeshYmin is not None) and \
            (maxThicknessMeshYmax is not None):
        if findLargestMesh:
            y1Pixels = maxThicknessMeshYmin - ny / 2
            dyPixels = maxThicknessMeshYmax - maxThicknessMeshYmin
            angle = angleMaxThickness
        else:
            y1Pixels = minThicknessMeshYmin - ny / 2
            dyPixels = minThicknessMeshYmax - minThicknessMeshYmin
            angle = angleMinThickness
    logging.debug(
        "angle={0}, x1Pixels={1}, y1Pixels={2}, dxPixels={3}, dyPixels={4}, deltaPhiz={5}, stdPhiz={6}".format(
            angle,
            x1Pixels,
            y1Pixels,
            dxPixels,
            dyPixels,
            deltaPhiz,
            stdPhiz))
    return (angle, x1Pixels, y1Pixels, dxPixels, dyPixels, deltaPhiz, stdPhiz)


def plot_img(img, plotPath):
    imgshape = img.shape
    extent = (0, imgshape[1], 0, imgshape[0])
    implot = pyplot.imshow(img, extent=extent)
    pyplot.gray()
    pyplot.colorbar()
    pyplot.savefig(plotPath)
    pyplot.close()
    return


def plotMesh(imagePath, grid_info, pixelsPerMM, destinationDir,
             signPhiy=1, fileName="snapshot_automesh.png"):
    (x1Pixels, y1Pixels, dxPixels, dyPixels) = gridInfoToPixels(grid_info, pixelsPerMM)
    img = scipy.misc.imread(imagePath, flatten=True)
    imgshape = img.shape
    extent = (0, imgshape[1], 0, imgshape[0])
    pylab.matshow(img / numpy.max(img), extent=extent)
    pylab.gray()
    ny, nx = imgshape
    if signPhiy < 0:
        meshXmin = nx / 2 - x1Pixels
    else:
        meshXmin = nx / 2 + x1Pixels
    meshYmin = ny / 2 - y1Pixels
    meshXmax = meshXmin + dxPixels
    meshYmax = meshYmin - dyPixels
    pylab.plot([meshXmin, meshXmin], [meshYmin, meshYmax], color='red', linewidth=2)
    pylab.plot([meshXmax, meshXmax], [meshYmin, meshYmax], color='red', linewidth=2)
    pylab.plot([meshXmin, meshXmax], [meshYmin, meshYmin], color='red', linewidth=2)
    pylab.plot([meshXmin, meshXmax], [meshYmax, meshYmax], color='red', linewidth=2)
    meshSnapShotPath = os.path.join(destinationDir, fileName)
    axes = pyplot.gca()
    axes.set_xlim([0, imgshape[1]])
    axes.set_ylim([0, imgshape[0]])
    pylab.savefig(meshSnapShotPath, bbox_inches='tight')
    pylab.show()
    pylab.close()
    return meshSnapShotPath, (meshXmin, meshYmin, meshXmax, meshYmax)


def gridInfoToPixels(grid_info, pixelsPerMM):
    if type(pixelsPerMM) in (list, tuple):
        x1Pixels = grid_info["x1"] * pixelsPerMM[0]
        y1Pixels = grid_info["y1"] * pixelsPerMM[1]
        dxPixels = grid_info["dx_mm"] * pixelsPerMM[0]
        dyPixels = grid_info["dy_mm"] * pixelsPerMM[1]
    else:
        x1Pixels = grid_info["x1"] * pixelsPerMM
        y1Pixels = grid_info["y1"] * pixelsPerMM
        dxPixels = grid_info["dx_mm"] * pixelsPerMM
        dyPixels = grid_info["dy_mm"] * pixelsPerMM
    return (x1Pixels, y1Pixels, dxPixels, dyPixels)


def readImage(imagePath):
    if imagePath.endswith(".png"):
        image = scipy.misc.imread(imagePath, flatten=True)
    elif imagePath.endswith(".npy"):
        image = numpy.load(imagePath)
    return image


def plotImage(image):
    imgshape = image.shape
    extent = (0, imgshape[1], 0, imgshape[0])
    pyplot.imshow(image, extent=extent)
    pyplot.show()


def plotLoopExam(image, listIndex, listLower, listUpper):
    pyplot.plot(listIndex, listUpper, '+')
    pyplot.plot(listIndex, listLower, '+')
    imgshape = image.shape
    extent = (0, imgshape[1], 0, imgshape[0])
    # pyplot.axes(extent)
    pyplot.show()


def cmp(a, b):
    """
    Python3 doesn't have cmp, see:
    https://codegolf.stackexchange.com/questions/49778/how-can-i-use-cmpa-b-with-python3
    """
    return (a > b) - (a < b)
