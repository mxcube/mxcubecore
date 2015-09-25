from HardwareRepository import HardwareRepository
from SOLEILMultiCollect import *
import shutil
import logging
from PyTango import DeviceProxy
import numpy
import re
import math

class PX2MultiCollect(SOLEILMultiCollect):
    def __init__(self, name):

        SOLEILMultiCollect.__init__(self, name, LimaAdscDetector(), TunableEnergy())
        #SOLEILMultiCollect.__init__(self, name, DummyDetector(), TunableEnergy())
        self.motors = ['sampx', 'sampy', 'phiz', 'phiy']
        
    def init(self):

        logging.info("headername is %s" % self.headername )

        self.headerdev     = DeviceProxy( self.headername )
        self.mono1dev      = DeviceProxy( self.mono1name )
        self.mono1_mt_rx   = DeviceProxy( self.mono1mtrxname )
        self.det_mt_ts_dev = DeviceProxy( self.detmttsname )
        self.det_mt_tx_dev = DeviceProxy( self.detmttxname )
        self.det_mt_tz_dev = DeviceProxy( self.detmttzname )
        
        self.helical = False
        self.linear = False
        self.grid = False
        self.translational = False
        self.standard_collect = False
        
        self.close_safty_shutter = self.getProperty("close_safty_shutter") 
        
        self.imgtojpeg = self.getProperty("imgtojpeg")
        self._detector.imgtojpeg = self.imgtojpeg
        self.jpegoption = self.getProperty("jpegoption")
        self.test_mode = int(self.getProperty("test_mode"))
        self.take_sample_snapshots = int(self.getProperty("take_sample_snapshots"))
        self.move_detector_flag = int(self.getProperty("move_detector_flag"))
        self.move_resolution_flag = int(self.getProperty("move_resolution_flag"))
        self.lima_overhead = float(self.getProperty("lima_overhead"))
        
        logging.info("<PX2 MultiCollect> lima_overhead %s" % self.lima_overhead)
        self._detector.prepareHeader = self.prepareHeader
        logging.getLogger("user_level_log").info("initializing PX2MultiCollect")
        SOLEILMultiCollect.init(self)
       
    def prepareHeader(self, X=None, Y=None, D=None):
        '''Will set up header given the actual values of beamline energy, mono and detector distance'''
        if X is None or Y is None:
            X, Y = self.beamCenter2()
        if D is None:
            D = self.distance2()
            
        #X, Y = self.beamCenter()

        BeamCenterX = str(round(X, 3))
        BeamCenterY = str(round(Y, 3))
        head = self.headerdev.read_attribute('header').value
        head = re.sub('BEAM_CENTER_X=\d\d\d\.\d', 'BEAM_CENTER_X=' + BeamCenterX, head)
        head = re.sub('BEAM_CENTER_Y=\d\d\d\.\d', 'BEAM_CENTER_Y=' + BeamCenterY, head)
        return head
    
    @task
    def move_motors(self, motor_position_dict, epsilon=0):
        logging.info("<PX2 MultiCollect> move_motors")
        for motor in motor_position_dict.keys(): #iteritems():
            position = motor_position_dict[motor]
            if isinstance(motor, str) or isinstance(motor, unicode):
                # find right motor object from motor role in diffractometer obj.
                motor_role = motor
                motor = self.bl_control.diffractometer.getDeviceByRole(motor_role)
                del motor_position_dict[motor_role]
                if motor is None:
                  continue
                motor_position_dict[motor]=position

            logging.getLogger("HWR").info("Moving motor '%s' to %f", motor.getMotorMnemonic(), position)
            motor.move(position, epsilon=epsilon, sync=True)

        while any([motor.motorIsMoving() for motor in motor_position_dict.iterkeys()]):
            logging.getLogger("HWR").info("Waiting for end of motors motion")
            time.sleep(0.1)  

    def distance2(self):
        logging.info('distance2 calculation')
        '''
        [-0.53371889  0.99843296]
        [ 0.33265006  0.00132375]
                                    OLS Regression Results                            
        ==============================================================================
        Dep. Variable:               distance   R-squared:                       1.000
        Model:                            OLS   Adj. R-squared:                  1.000
        Method:                 Least Squares   F-statistic:                 5.689e+05
        Date:                Wed, 16 Jul 2014   Prob (F-statistic):          3.99e-232
        Time:                        10:36:26   Log-Likelihood:                -255.97
        No. Observations:                 128   AIC:                             515.9
        Df Residuals:                     126   BIC:                             521.6
        Df Model:                           1                                         
        ==============================================================================
                        coef    std err          t      P>|t|      [95.0% Conf. Int.]
        ------------------------------------------------------------------------------
        const         -0.5337      0.333     -1.604      0.111        -1.192     0.125
        distance       0.9984      0.001    754.247      0.000         0.996     1.001
        ==============================================================================
        Omnibus:                      173.471   Durbin-Watson:                   1.902
        Prob(Omnibus):                  0.000   Jarque-Bera (JB):            11943.491
        Skew:                           4.863   Prob(JB):                         0.00
        Kurtosis:                      49.312   Cond. No.                         525.
        ==============================================================================
        '''
        #distance    = self.detector_mt_ts.read_attribute('position').value
        distance   = self.det_mt_ts_dev.read_attribute('position').value
        
        X = numpy.matrix([1., distance])
        theta = numpy.matrix([-0.53371889,  0.99843296])
        
        d = X * theta.T
        
        return float(d)

    def beamCenter(self):
        '''Will calculate beam center coordinates'''

        # Useful values
        tz_ref = -6.5     # reference tz position for linear regression
        tx_ref = -17.0    # reference tx position for linear regression
        q = 0.102592  # pixel size in milimeters

        wavelength = self.mono1dev.read_attribute('lambda').value
        distance   = self.det_mt_ts_dev.read_attribute('position').value
        tx         = self.det_mt_tx_dev.read_attribute('position').value
        tz         = self.det_mt_tz_dev.read_attribute('position').value

        zcor = tz - tz_ref
        xcor = tx - tx_ref

        Theta = numpy.matrix([[1.55557116e+03,  1.43720063e+03],
                              [-8.51067454e-02, -1.84118001e-03],
                              [-1.99919592e-01,  3.57937064e+00]])  # values from 16.05.2013

        X = numpy.matrix([1., distance, wavelength])

        Origin = Theta.T * X.T
        Origin = Origin * q

        return Origin[1] + zcor, Origin[0] + xcor
        
    def get_beam_center_x(self, X):
        logging.info('beam_center_x calculation')
        # values from 2014-07-01
        '''
        [  1.72620674e+03  -8.43965198e-02  -6.16352910e-01   9.74625808e+00]
        [ 0.10650521  0.00025538  0.09303154  0.00250652]
                                    OLS Regression Results                            
        ==============================================================================
        Dep. Variable:                   ORGX   R-squared:                       1.000
        Model:                            OLS   Adj. R-squared:                  1.000
        Method:                 Least Squares   F-statistic:                 8.059e+06
        Date:                Wed, 16 Jul 2014   Prob (F-statistic):               0.00
        Time:                        09:54:55   Log-Likelihood:                -22.630
        No. Observations:                 128   AIC:                             53.26
        Df Residuals:                     124   BIC:                             64.67
        Df Model:                           3                                         
        ==============================================================================
                        coef    std err          t      P>|t|      [95.0% Conf. Int.]
        ------------------------------------------------------------------------------
        const       1726.2067      0.107   1.62e+04      0.000      1725.996  1726.418
        distance      -0.0844      0.000   -330.478      0.000        -0.085    -0.084
        wavelength    -0.6164      0.093     -6.625      0.000        -0.800    -0.432
        mt_z           9.7463      0.003   3888.361      0.000         9.741     9.751
        ==============================================================================
        Omnibus:                       33.658   Durbin-Watson:                   1.310
        Prob(Omnibus):                  0.000   Jarque-Bera (JB):              118.590
        Skew:                          -0.869   Prob(JB):                     1.77e-26
        Kurtosis:                       7.383   Cond. No.                     1.32e+03
        ==============================================================================

        Warnings:
        [1] The condition number is large, 1.32e+03. This might indicate that there are
        strong multicollinearity or other numerical problems.
        '''
        theta = numpy.matrix([  1.50045368e+03,   1.60241789e-04,  3.87663239e+00,   9.77188997e+00])
        orgy = X * theta.T
        return float(orgy)
    
    def get_beam_center_y(self, X):
        logging.info('beam_center_y calculation')
        '''
        [  1.50045368e+03   1.60241789e-04   3.87663239e+00   9.77188997e+00]
        [ 0.09210914  0.00020683  0.08156218  0.00343946]
                                    OLS Regression Results                            
        ==============================================================================
        Dep. Variable:                   ORGY   R-squared:                       1.000
        Model:                            OLS   Adj. R-squared:                  1.000
        Method:                 Least Squares   F-statistic:                 2.852e+06
        Date:                Wed, 16 Jul 2014   Prob (F-statistic):          8.84e-300
        Time:                        09:54:55   Log-Likelihood:                -9.2162
        No. Observations:                 128   AIC:                             26.43
        Df Residuals:                     124   BIC:                             37.84
        Df Model:                           3                                         
        ==============================================================================
                        coef    std err          t      P>|t|      [95.0% Conf. Int.]
        ------------------------------------------------------------------------------
        const       1500.4537      0.092   1.63e+04      0.000      1500.271  1500.636
        distance       0.0002      0.000      0.775      0.440        -0.000     0.001
        wavelength     3.8766      0.082     47.530      0.000         3.715     4.038
        mt_x           9.7719      0.003   2841.110      0.000         9.765     9.779
        ==============================================================================
        Omnibus:                       22.231   Durbin-Watson:                   0.878
        Prob(Omnibus):                  0.000   Jarque-Bera (JB):               52.355
        Skew:                          -0.662   Prob(JB):                     4.28e-12
        Kurtosis:                       5.840   Cond. No.                     1.27e+03
        ==============================================================================

        Warnings:
        [1] The condition number is large, 1.27e+03. This might indicate that there are
        strong multicollinearity or other numerical problems.
        '''
        # values from 2014-07-01
        theta = numpy.matrix([  1.72620674e+03,  -8.43965198e-02,  -6.16352910e-01,   9.74625808e+00])
        orgx = X * theta.T
        return float(orgx)
    
    def beamCenter2(self):
        logging.info('beamCenter calculation')
        q = 0.102592
        
        wavelength = self.mono1dev.read_attribute('lambda').value
        distance   = self.det_mt_ts_dev.read_attribute('position').value
        tx         = self.det_mt_tx_dev.read_attribute('position').value
        tz         = self.det_mt_tz_dev.read_attribute('position').value
        logging.info('wavelength %s' % wavelength)
        logging.info('mt_ts %s' % distance)
        logging.info('mt_tx %s' % tx)
        logging.info('mt_tz %s' % tz)
        #wavelength  = self.mono1.read_attribute('lambda').value
        #distance    = self.detector_mt_ts.read_attribute('position').value
        #tx          = self.detector_mt_tx.position
        #tz          = self.detector_mt_tz.position
        
        X = numpy.matrix([1., distance, wavelength, tx, tz])
        
        beam_center_x = self.get_beam_center_x(X[:, [0, 1, 2, 4]])
        beam_center_y = self.get_beam_center_y(X[:, [0, 1, 2, 3]])
        
        #dirty fix for drift between Run3 and Run4 2014
        beam_center_x -= 3.08
        beam_center_y -= 1.45

        #dirty fix for shift (re-focusing) beginning Run1 2015
        beam_center_x += 0.15
        beam_center_y -= 2.34
        
        #shift beginning Run2 2015
        beam_center_x -= 0.21
        beam_center_y -= 0.86
        
        #shift beginning Run3 2015
        beam_center_x += 1.85
        beam_center_y -= 0

        #shift 2015-06-24 (something wierd happened with mirrors over the last weekend see., /927bis/ccd/gitRepos/Beamline/Suivi_2015-06-19)
        # optimal 1508.45   1527.97
        # input   1507.5    1527.4
        beam_center_x += 0
        beam_center_y -= 0
        
        
        beam_center_y *= q
        beam_center_x *= q
        
        # The following two lines fixes the loss of offsets from 2014-09-12 (apparently an init on translation stage device servers)
        beam_center_y += -17.2 #3.5
        beam_center_x += 3.5 #17.2
        
        print 'beamCenter2', beam_center_y, beam_center_x
        return beam_center_x, beam_center_y
                
    def set_collect_position(self, position):
        logging.info("<PX2 MultiCollect> set collect position %s" % position)
        logging.info("<PX2 MultiCollect> set collect position type %s" % type(position))
        self.standard_collect = True
        #pos = dict(position)
        #collect_position = {} 
        #for motor in self.motors:
            #collect_position[motor] = pos[motor]
            
        self.collect_position = self.bl_control.diffractometer.getPositions()
    
    def are_positions_equal(self, position1, position2, epsilon = 1.e-4):
        equal = True
        for key in position1:
            if key in position2:
                if abs(position1[key] - position2[key]) > epsilon:
                    return False
        return True
        
    def set_helical(self, onmode, positions=None):
        logging.info("<PX2 MultiCollect> set helical")
        self.helical = onmode
        if onmode:
            logging.info("<PX2 MultiCollect> set helical pos1 %s pos2 %s" % (positions['1'], positions['2']))
            self.helicalStart = positions['1']
            self.helicalFinal = positions['2']
        
    def set_translational(self, onmode, positions=None, step=None):
        logging.info("<PX2 MultiCollect> set translational")
        self.translational = onmode
        self.translationalStart = positions['1']
        self.translationalFinal = positions['2']
        if step is not None:
            self.translationalStep = step
        
    def set_linear(self, onmode, positions=None, step=None):
        logging.info("<PX2 MultiCollect> set linear")
        self.linear = onmode
        self.linearStart = positions['1']
        self.linearFinal = positions['2']
        if step is not None:
            self.linearStep = step
        
    def set_grid(self, onmode, positions=None):
        logging.info("<PX2 MultiCollect> set grid")
        self.grid = onmode

    def rotate(self, angle, unit='radians'):
        if unit != 'radians':
            angle = math.radians(angle)
            
        r = numpy.array([[ math.cos(angle),  math.sin(angle), 0.], 
                         [-math.sin(angle),  math.cos(angle), 0.], 
                         [              0.,               0., 1.]])
        return r
        

    def shift(self, displacement):
        s = numpy.array([[1., 0., displacement[0]], 
                         [0., 1., displacement[1]], 
                         [0., 0.,              1.]])
        return s


    def scale(self, factor):
        s = numpy.diag([factor[0], factor[1], 1.])
        return s
        

    def scan(self, center, nbsteps, lengths, attributes):
        '''2D scan on an md2 attribute'''
        
        center = numpy.array(center)
        nbsteps = numpy.array(nbsteps)
        lengths = numpy.array(lengths)
        
        stepsizes = lengths / nbsteps
        
        print 'center', center
        print 'nbsteps', nbsteps
        print 'lengths', lengths
        print 'stepsizes', stepsizes
        
        # adding [1] so that we can use homogeneous coordinates
        positions = list(itertools.product(range(nbsteps[0]), range(nbsteps[1]), [1])) 
        
        points = [numpy.array(position) for position in positions]
        points = numpy.array(points)
        points = numpy.dot(self.shift(- nbsteps / 2.), points.T).T
        points = numpy.dot(self.scale(stepsizes), points.T).T
        points = numpy.dot(self.shift(center), points.T).T
        
        grid = numpy.reshape(points, numpy.hstack((nbsteps, 3)))
        
        gs = grid.shape
        for i in range(gs[0]):
            line = grid[i, :]
            if (i + 1) % 2 == 0:
                line = line[: : -1]
            for point in line:
                self.moveMotors()
                self.measure()
    
    def raster(self, grid):
        gs = grid.shape
        orderedGrid = []
        for i in range(gs[0]):
            line = grid[i, :]
            if (i + 1) % 2 == 0:
                line = line[: : -1]
            orderedGrid.append(line)
        return numpy.array(orderedGrid)
        

    #def calculateGridPositions(self, grid_description):
        """
        The grid description dictionary has the following format:

        grid = {'id': 'grid-n',
                'dx_mm': total width in mm,
                'dy_mm': total height in mm,
                'steps_x': number of colls,
                'steps_y': number of rows,
                'x1': top left cell center x coord,
                'y1': top left cell center y coord,
                'beam_width': beam width in mm
                'beam_height': beam height in mm
                'angle': 0}
        """
        
    def calculateGridPositions(self, start=[0., 0.], nbsteps=[15, 10], lengths=[1.5, 1.], angle=0., motors=['PhiY', 'PhiZ']):
        #import scipy.ndimage #rotate, shift
        center = numpy.array(start)
        nbsteps = numpy.array(nbsteps)
        lengths = numpy.array(lengths)
        
        stepsizes = lengths / nbsteps
        
        print 'center', center
        print 'nbsteps', nbsteps
        print 'lengths', lengths
        print 'stepsizes', stepsizes
        
        # adding [1] so that we can use homogeneous coordinates
        positions = list(itertools.product(range(nbsteps[0]), range(nbsteps[1]), [1])) 
        
        points = [numpy.array(position) for position in positions]
        points = numpy.array(points)
        points = numpy.dot(self.shift(- nbsteps / 2.), points.T).T
        points = numpy.dot(self.rotate(angle), points.T).T
        points = numpy.dot(self.scale(stepsizes), points.T).T
        points = numpy.dot(self.shift(center), points.T).T
        
        grid = numpy.reshape(points, numpy.hstack((nbsteps, 3)))
        
        rastered = self.raster(grid)
        
        orderedPositions = rastered.reshape((grid.size/3, 3))
        
        dictionariesOfOrderedPositions = [{motors[0]: position[0], motors[1]: position[1]} for position in orderedPositions]
        
        return dictionariesOfOrderedPositions


    def setGridParameters(self, start, nbsteps, lengths):
        self.grid_start = start
        self.grid_nbsteps = nbsteps
        self.grid_lengths = lengths
        self.grid_angle = self.getPhiValue()
        
        
    def getPoints(self, start, final, nbSteps):
        logging.info("<PX2 MultiCollect> getPoints start %s, final %s" % (start, final))
        step = 1./ (nbSteps - 1)
        points = numpy.arange(0., 1.+(0.5*step), step)
        Positions = {}
        positions = []
        for motor in self.motors:
            scanRange = final[motor] - start[motor]
            Positions[motor] = start[motor] + points * scanRange
            positions.append(Positions[motor])
            
        positions = numpy.array(positions)
        return [dict(zip(self.motors, p)) for p in positions.T]
    
    def calculateHelicalCollectPositions(self, start, final, nImages):
        logging.info("<PX2 MultiCollect> calculateHelicalCollectPositions")
        positions = self.getPoints(start, final, nImages)
        return positions

    def calculateTranslationalCollectPositions(self, start, final, nImages):
        '''take into account the beam size and spread the positions optimally between start and final positions.'''
        logging.info("<PX2 MultiCollect> calculateTranslationalCollectPositions")
        logging.info("<PX2 MultiCollect> start %s, final %s, nImages %s" %(start, final, nImages))
        positions = []
        horizontal_beam_size = 0.015 #self.get_horizontal_beam_size()
        totalHorizontalDistance = abs(final['phiy'] - start['phiy'])
        freeHorizontalSpace = totalHorizontalDistance - horizontal_beam_size
        # Due to our rotational axis being horizontal we take the horizontal beam size as the basic step size
        nPositions = int(freeHorizontalSpace // horizontal_beam_size) + 2
        nImagesPerPosition, remainder = divmod(nImages, nPositions)
        logging.info("<PX2 MultiCollect> nImagesPerPosition %s, remainder %s" %(nImagesPerPosition,remainder))
        positions = self.getPoints(start, final, nPositions)
        explicit_positions = []
        k = 0
        for p in positions:
            k += 1
            to_add = [p] * (nImagesPerPosition)
            if k <= remainder:
                to_add += [p]
            explicit_positions += to_add
        return explicit_positions
    

    def safe_mono_turnoff(self):
        logging.info("<PX2 MultiCollect> truning off the mono1-mt_rx motor before collect")
        k=0
        while self.mono1_mt_rx.state().name != 'OFF':
            k+=1
            logging.info("<PX2 MultiCollect> truning off the mono1-mt_rx motor before collect -- attempt %s" % k)
            if self.mono1_mt_rx.state().name == 'STANDBY':
                self.mono1_mt_rx.Off()
            else:
                time.sleep(0.1)
                
    def mono_turnon(self):
        logging.info("<PX2 MultiCollect> turning on the mono1-mt_rx motor")
        if self.mono1_mt_rx.state().name == 'OFF':
            self.mono1_mt_rx.On()

    def getCollectPositions(self, nImages):
        logging.info("<PX2 MultiCollect> get collect positions")
        logging.info("getCollectPositions nImages %s" % nImages)
        positions = []
        if self.helical:
            start, final = self.helicalStart, self.helicalFinal
            positions = self.calculateHelicalCollectPositions(start, final, nImages)
            self.helical = False
        elif self.translational:
            start, final = self.translationalStart, self.translationalFinal
            positions = self.calculateTranslationalCollectPositions(start, final, nImages)
            self.translational = False
        elif self.linear:
            start, final = self.linearStart, self.linearFinal
            positions = self.getPoints(start, final, nImages)
            self.linear = False
        elif self.grid:
            positions = self.calculateGridPositions(grid_description)
            self.grid = False
        else:
            self.collect_position = {}
            positions = [ self.collect_position for k in range(nImages)]
        return positions
        
    def newWedge(self, imageNums, ScanStartAngle, template, positions):
        return {'imageNumbers': imageNums, 
                'startAtAngle': ScanStartAngle, 
                'template': template, 
                'positions': positions}
    
    def prepareWedges(self, firstImage, 
                            nbFrames, 
                            ScanStartAngle, 
                            ScanRange, 
                            wedgeSize, 
                            inverse, 
                            ScanOverlap, 
                            template):
        '''Based on collect parameters will prepare all the wedges to be collected.'''
        logging.info('Preparing wedges')
        search_template = template.lower()
        if self.helical:
            if 'transl' in search_template:
                self.helical = False
                self.translational = True
                self.translationalStart, self.translationalFinal = self.helicalStart, self.helicalFinal
            elif 'linear' in search_template:
                self.helical = False
                self.linear = True
                self.linearStart, self.linearFinal = self.helicalStart, self.helicalFinal
            else:
                pass
        wedges = []
        
        imageNums = range(firstImage, nbFrames + firstImage)
        positions = self.getCollectPositions(nbFrames)
        
        wedges = self.newWedge(imageNums, ScanStartAngle, template, positions)
        if inverse is True:
            inv_wedge = self.newWedge(imageNums, ScanStartAngle, template_inv, positions)
            wedgeSize = int(reference_interval)
            numberOfFullWedges, lastWedgeSize = divmod(nbFrames, wedgeSize)
            for k in range(0, numberOfFullWedges):
                start = k * numberOfFullWedges
                stop = (k+1) * numberOfFullWedges
                wedges.append(wedge[start: stop] + inv_wedge[start: stop])
            wedges.append(wedge[stop:] + inv_wedge[stop:])
        print 'Wedges to collect:'
        print wedges
        logging.info('Wedges to collect %s' % wedges)
        return wedges
    
    def get_sync_destination(self, directory, reference = '/home/experiences/proxima2a/com-proxima2a'):
        logging.info('get_sync_destination')
        self.sync_destination = os.path.join(reference, directory[1:])
        sync_process = os.path.join(self.sync_destination, 'process')
        logging.info('get_sync_destination %s ' %self.sync_destination )
        os.system('ssh p10 "mkdir -p %s"' % sync_process)
        
    def synchronize_thread(self, directory, filename):
        logging.info('Starting Synchronize Thread')
        logging.info('filename %s ' % filename)
        self.sthread = threading.Thread(target=self.synchronize_image, args=(directory, filename))
        self.sthread.daemon = True
        self.sthread.start()
        
    def synchronize_image(self, directory, filename):
        logging.info('Synchronizing image %s' % filename)
        filename = os.path.join(directory, filename)
        while not os.path.exists(filename):
            time.sleep(0.05)
        logging.info('Size of the image after it came to existence %s' % os.path.getsize(filename))
        time.sleep(0.2)
        while os.path.getsize(filename) != 18874880:
            time.sleep(0.05)
        logging.info('Size of the image before sync %s' % os.path.getsize(filename))
        logging.info('sync command %s' % ('ssh p10 "rsync -av %s %s"' % (filename, self.sync_destination)))
        os.system('ssh p10 "rsync -av %s %s"' % (filename, self.sync_destination))
    
    def sync_collect(self, file_location, last_file, image_file_template):
        logging.info('sync_last_collect')
        last_file = os.path.join(file_location, last_file)
        start = time.time()
        while (not os.path.exists(last_file)) and time.time() - start < 5.:
            time.sleep(0.1)
        source = os.path.join(file_location, image_file_template.replace('%04d', '*'))
        print 'sync_collect'
        print 'excuting command', 'ssh p10 "rsync -av %s %s"' % (source, self.sync_destination)
        os.system('ssh p10 "rsync -av %s %s"' % (source, self.sync_destination))
        
    def should_i_take_snapshots(self, data_collect_parameters):
        if data_collect_parameters['oscillation_sequence'][0]['start_image_number'] != 1:
            return False
        return True
        
    @task
    def do_collect(self, owner, data_collect_parameters, in_multicollect=False):
        # reset collection id on each data collect
        logging.info("<SOLEIL do_collect>  data_collect_parameters %s" % data_collect_parameters)
        logging.info("<SOLEIL do_collect>  in_multicollect %s" % in_multicollect)
        self.collection_id = None
        self.snapshots_taken = False

        # Preparing directory path for images and processing files
        # creating image file template and jpegs files templates
        file_parameters = data_collect_parameters["fileinfo"]

        file_parameters["suffix"] = self.bl_config.detector_fileext
        image_file_template = "%(prefix)s_%(run_number)s_%%04d.%(suffix)s" % file_parameters
        file_parameters["template"] = image_file_template

        archive_directory = self.get_archive_directory(file_parameters["directory"])
        data_collect_parameters["archive_dir"] = archive_directory

        if archive_directory:
            jpeg_filename="%s.jpeg" % os.path.splitext(image_file_template)[0]
            thumb_filename="%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
            jpeg_file_template = os.path.join(archive_directory, jpeg_filename)
            jpeg_thumbnail_file_template = os.path.join(archive_directory, thumb_filename)
        else:
            jpeg_file_template = None
            jpeg_thumbnail_file_template = None
        # database filling
        logging.info("<PX2MultiCollect> - LIMS is %s" % str(self.bl_control.lims))
        if self.bl_control.lims:
            data_collect_parameters["collection_start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if self.bl_control.machine_current is not None:
                data_collect_parameters["synchrotronMode"] = self.get_machine_fill_mode()
            data_collect_parameters["status"] = "failed"
            try:
                (self.collection_id, detector_id) = \
                                 self.bl_control.lims.store_data_collection(data_collect_parameters, self.bl_config)
              
                data_collect_parameters['collection_id'] = self.collection_id
    
                if detector_id:
                    data_collect_parameters['detector_id'] = detector_id
            except:
                import traceback
                logging.info("<PX2MultiCollect> - problem with connection to LIMS")
                data_collect_parameters['detector_id'] = 'ADSC Quantum 315r SN927'
                logging.info(traceback.print_exc())
        # Creating the directory for images and processing information
        logging.info("<PX2MultiCollect> - Creating directories for images and processing %s %s" % (file_parameters['directory'],file_parameters['process_directory'] ) )
        self.create_directories(file_parameters['directory'], file_parameters['process_directory'], os.path.join(file_parameters['directory'], 'process'))
        self.xds_directory, self.mosflm_directory = self.prepare_input_files(file_parameters["directory"], file_parameters["prefix"], file_parameters["run_number"], file_parameters['process_directory'])
        data_collect_parameters['xds_dir'] = self.xds_directory

        sample_id, sample_location, sample_code = self.get_sample_info_from_parameters(data_collect_parameters)
        data_collect_parameters['blSampleId'] = sample_id

        if self.bl_control.sample_changer is not None:
            data_collect_parameters["actualSampleBarcode"] = \
                self.bl_control.sample_changer.getLoadedSampleDataMatrix()
            data_collect_parameters["actualContainerBarcode"] = \
                self.bl_control.sample_changer.currentBasketDataMatrix

            basket, vial = (self.bl_control.sample_changer.currentBasket,
                        self.bl_control.sample_changer.currentSample)

            data_collect_parameters["actualSampleSlotInContainer"] = vial
            data_collect_parameters["actualContainerSlotInSC"] = basket

        else:
            data_collect_parameters["actualSampleBarcode"] = None
            data_collect_parameters["actualContainerBarcode"] = None

        centring_info = {}
        try:
            centring_status = self.diffractometer().getCentringStatus()
        except:
            pass
        else:
            centring_info = dict(centring_status)

        #Save sample centring positions
        motors = centring_info.get("motors", {})
        logging.info('do_collect motors %s' % motors)
        extra_motors = centring_info.get("extraMotors", {})

        positions_str = ""

        motors_to_move_before_collect = data_collect_parameters.setdefault("motors", {})
        
        for motor in motors:
          positions_str = "%s %s=%f" % (positions_str, motor, motors[motor])
          # update 'motors' field, so diffractometer will move to centring pos.
          motors_to_move_before_collect.update({motor: motors[motor]})
        for motor in extra_motors:
          positions_str = "%s %s=%f" % (positions_str, motor, extra_motors[motor])
          motors_to_move_before_collect.update({motor: extra_motors[motor]})
          
        data_collect_parameters['actualCenteringPosition'] = positions_str

        if self.bl_control.lims:
          try:
            if self.current_lims_sample:
              self.current_lims_sample['lastKnownCentringPosition'] = positions_str
              self.bl_control.lims.update_bl_sample(self.current_lims_sample)
          except:
            logging.getLogger("HWR").exception("Could not update sample infromation in LIMS")

        if 'images' in centring_info:
          # Save snapshots
          snapshot_directory = self.get_archive_directory(file_parameters["directory"])
          logging.getLogger("HWR").debug("Snapshot directory is %s" % snapshot_directory)

          try:
            self.create_directories(snapshot_directory)
          except:
              logging.getLogger("HWR").exception("Error creating snapshot directory")
          else:
              snapshot_i = 1
              snapshots = []
              for img in centring_info["images"]:
                img_phi_pos = img[0]
                img_data = img[1]
                snapshot_filename = "%s_%s_%s.snapshot.jpeg" % (file_parameters["prefix"],
                                                                file_parameters["run_number"],
                                                                snapshot_i)
                full_snapshot = os.path.join(snapshot_directory,
                                             snapshot_filename)

                try:
                  f = open(full_snapshot, "w")
                  f.write(img_data)
                except:
                  logging.getLogger("HWR").exception("Could not save snapshot!")
                  try:
                    f.close()
                  except:
                    pass

                data_collect_parameters['xtalSnapshotFullPath%i' % snapshot_i] = full_snapshot

                snapshots.append(full_snapshot)
                snapshot_i+=1

          try:
            data_collect_parameters["centeringMethod"] = centring_info['method']
          except:
            data_collect_parameters["centeringMethod"] = None

        if self.bl_control.lims:
            try:
                self.bl_control.lims.update_data_collection(data_collect_parameters)
            except:
                logging.getLogger("HWR").exception("Could not update data collection in LIMS")
        #import pdb;pdb.set_trace()
        oscillation_parameters = data_collect_parameters["oscillation_sequence"][0]
        sample_id = data_collect_parameters['blSampleId']
        inverse_beam = "reference_interval" in oscillation_parameters
        reference_interval = oscillation_parameters.get("reference_interval", 1)
        
        firstImage = oscillation_parameters["start_image_number"] 
        nbFrames = oscillation_parameters["number_of_images"]
        ScanStartAngle = oscillation_parameters["start"]
        ScanRange = oscillation_parameters["range"]
        wedgeSize = reference_interval
        inverse = inverse_beam
        ScanOverlap = oscillation_parameters["overlap"]
        template = image_file_template
        myWedges = self.prepareWedges(firstImage, 
                                      nbFrames, 
                                      ScanStartAngle, 
                                      ScanRange, 
                                      wedgeSize, 
                                      inverse, 
                                      ScanOverlap, 
                                      template)
        positions = myWedges['positions']
        wedges_to_collect = self.prepare_wedges_to_collect(oscillation_parameters["start"],
                                                           oscillation_parameters["number_of_images"],
                                                           oscillation_parameters["range"],
                                                           reference_interval,
                                                           inverse_beam,
                                                           oscillation_parameters["overlap"])
        logging.info('do_collect wedges_to_collect %s' % wedges_to_collect)
        nframes = len(wedges_to_collect)
        self.emit("collectNumberOfFrames", nframes) 

        start_image_number = oscillation_parameters["start_image_number"]    
        if data_collect_parameters["skip_images"]:
            for start, wedge_size in wedges_to_collect[:]:
              filename = image_file_template % start_image_number
              file_location = file_parameters["directory"]
              file_path  = os.path.join(file_location, filename)
              if os.path.isfile(file_path):
                logging.info("Skipping existing image %s", file_path)
                del wedges_to_collect[0]
                start_image_number += 1
                nframes -= 1
              else:
                # images have to be consecutive
                break
        
        if nframes == 0:
            return
            
        # write back to the dictionary to make macros happy... TODO: remove this once macros are removed!
        oscillation_parameters["start_image_number"] = start_image_number
        oscillation_parameters["number_of_images"] = nframes
        data_collect_parameters["skip_images"] = 0
 
        # data collection
        self.data_collection_hook(data_collect_parameters)
        
                                     
        if 'transmission' in data_collect_parameters:
          self.set_transmission(data_collect_parameters["transmission"])

        if 'wavelength' in data_collect_parameters:
          self.set_wavelength(data_collect_parameters["wavelength"])
        elif 'energy' in data_collect_parameters:
          self.set_energy(data_collect_parameters["energy"])
        
        if 'resolution' in data_collect_parameters:
          if self.move_resolution_flag == 1:
            resolution = data_collect_parameters["resolution"]["upper"]
            #self.set_resolution(resolution)
            self.send_resolution(resolution)
          else:
            logging.getLogger("HWR").info("Not changing resolution, if this is not intended, change the move_resolution configuration parameter in ~/mxcube_v2/HardwareObjects.xml/PX2/mxcollect.xml")
        elif 'detdistance' in oscillation_parameters:
          if self.move_detector_flag == 1:
            logging.getLogger("HWR").info("Moving the detector")
            #self.move_detector(oscillation_parameters["detdistance"])
            self.send_detector(oscillation_parameters["detdistance"])
          else:
            logging.getLogger("HWR").info("Not moving the detector, if this is not intended, change the move_detector configuration parameter in ~/mxcube_v2/HardwareObjects.xml/PX2/mxcollect.xml")
         
        try:
            if data_collect_parameters["take_snapshots"] and self.should_i_take_snapshots(data_collect_parameters) and self.take_sample_snapshots == 1:
                self.take_crystal_snapshots()
        except KeyError:
            pass
        
        frame = start_image_number
        osc_range = oscillation_parameters["range"]
        exptime = oscillation_parameters["exposure_time"]
        npass = oscillation_parameters["number_of_passes"]
        
        self.prepare_acquisition(1 if data_collect_parameters.get("dark", 0) else 0,
                                     wedges_to_collect[0][0],
                                     osc_range,
                                     exptime,
                                     npass,
                                     nframes,
                                     data_collect_parameters["comment"],
                                     lima_overhead = self.lima_overhead)
        #self.close_fast_shutter()

        with cleanup(self.data_collection_cleanup):
            self.open_safety_shutter(timeout=10)
            
            self.prepare_intensity_monitors()
           
            # update LIMS
            if self.bl_control.lims:
                  try:
                    data_collect_parameters["flux"] = self.get_flux()
                    data_collect_parameters["flux_end"] = data_collect_parameters["flux"]
                    data_collect_parameters["wavelength"]= self.get_wavelength()
                    data_collect_parameters["detectorDistance"] =  self.get_detector_distance()
                    data_collect_parameters["resolution"] = self.get_resolution()
                    data_collect_parameters["transmission"] = self.get_transmission()
                    gap1, gap2, gap3 = self.get_undulators_gaps()
                    data_collect_parameters["undulatorGap1"] = gap1
                    data_collect_parameters["undulatorGap2"] = gap2
                    data_collect_parameters["undulatorGap3"] = gap3
                    data_collect_parameters["resolutionAtCorner"] = self.get_resolution_at_corner()
                    beam_size_x, beam_size_y = self.get_beam_size()
                    data_collect_parameters["beamSizeAtSampleX"] = beam_size_x
                    data_collect_parameters["beamSizeAtSampleY"] = beam_size_y
                    data_collect_parameters["beamShape"] = self.get_beam_shape()
                    hor_gap, vert_gap = self.get_slit_gaps()
                    data_collect_parameters["slitGapHorizontal"] = hor_gap
                    data_collect_parameters["slitGapVertical"] = vert_gap
                    beam_centre_x, beam_centre_y = self.get_beam_centre()
                    data_collect_parameters["xBeam"] = beam_centre_x
                    data_collect_parameters["yBeam"] = beam_centre_y

                    logging.info("Updating data collection in ISPyB")
                    self.bl_control.lims.update_data_collection(data_collect_parameters, wait=True)
                    logging.info("Done")
                  except:
                    logging.getLogger("HWR").exception("Could not store data collection into LIMS")

            if self.bl_control.lims and self.bl_config.input_files_server:
                self.write_input_files(self.collection_id, wait=False) 

            data_collect_parameters["dark"] = 0

            # at this point input files should have been written           
            if self.bl_control.lims and self.bl_config.input_files_server:
              if data_collect_parameters.get("processing", False)=="True":
                self.trigger_auto_processing("before",
                                       self.xds_directory,
                                       data_collect_parameters["EDNA_files_dir"],
                                       data_collect_parameters["anomalous"],
                                       data_collect_parameters["residues"],
                                       inverse_beam,
                                       data_collect_parameters["do_inducedraddam"],
                                       in_multicollect,
                                       data_collect_parameters.get("sample_reference", {}).get("spacegroup", ""),
                                       data_collect_parameters.get("sample_reference", {}).get("cell", ""))
            
            k = 0
            reference_position = positions[0]
            #if self.standard_collect is True:
                #if self.are_positions_equal(self.collect_position, self.bl_control.diffractometer.getPositions()):
                    #logging.info("PX2MultiCollect moving into collect position %s " % self.collect_position)
                    #self.bl_control.diffractometer.moveMotors(self.collect_position)
               
            self.safe_mono_turnoff()
            
            file_location = file_parameters["directory"]
            self.get_sync_destination(file_location)
            
            self.verify_detector_distance()
            self.verify_resolution()
            self.bl_control.diffractometer.verifyGonioInCollect()
            
            logging.info('moving motors before collect %s' % motors_to_move_before_collect)
            self.move_motors(motors_to_move_before_collect)
            self.bl_control.diffractometer.wait()
            
            for start, wedge_size in wedges_to_collect:
                k += 1
                end = start + osc_range
                collect_position = positions[k-1]
                filename = image_file_template % frame
                try:
                  jpeg_full_path = jpeg_file_template % frame
                  jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame
                except:
                  jpeg_full_path = None
                  jpeg_thumbnail_full_path = None
                file_location = file_parameters["directory"]
                self.get_sync_destination(file_location)
                file_path  = os.path.join(file_location, filename)
                
                logging.info("Frame %d, %7.3f to %7.3f degrees", frame, start, end)

                self.set_detector_filenames(frame, start, file_path, jpeg_full_path, jpeg_thumbnail_full_path)
                
                osc_start, osc_end = self.prepare_oscillation(start, osc_range, exptime, npass)
                
                with error_cleanup(self.reset_detector):
                    self.move_motors(collect_position, epsilon=0.0002)
                    self.start_acquisition(exptime, npass, start_image_number)
                    if osc_end - osc_start < 1E-4:
                       self.open_fast_shutter()
                       time.sleep(exptime)
                       self.close_fast_shutter()
                    else:
                       self.do_oscillation(osc_start, osc_end, exptime, npass)
                    self.stop_acquisition()
                    last_frame = start_image_number + nframes - 1
                    self.write_image(last_frame, jpeg_full_path=jpeg_full_path, jpeg_thumbnail_full_path=jpeg_thumbnail_full_path)
                    
                    # Store image in lims
                    if self.bl_control.lims:
                      if self.store_image_in_lims(frame, frame == start_image_number, frame == last_frame):
                        lims_image={'dataCollectionId': self.collection_id,
                                    'fileName': filename,
                                    'fileLocation': file_location,
                                    'imageNumber': frame,
                                    'measuredIntensity': self.get_measured_intensity(),
                                    'synchrotronCurrent': self.get_machine_current(),
                                    'machineMessage': self.get_machine_message(),
                                    'temperature': self.get_cryo_temperature()}

                        if archive_directory:
                          lims_image['jpegFileFullPath'] = jpeg_full_path
                          lims_image['jpegThumbnailFileFullPath'] = jpeg_thumbnail_full_path

                        try:
                          self.bl_control.lims.store_image(lims_image)
                        except:
                          logging.getLogger("HWR").exception("Could not store image in LIMS")
                                              
                    self.emit("collectImageTaken", frame)
                        
                    if self.bl_control.lims and self.bl_config.input_files_server:
                      if data_collect_parameters.get("processing", False)=="True":
                         self.trigger_auto_processing("image",
                                                   self.xds_directory, 
                                                   data_collect_parameters["EDNA_files_dir"],
                                                   data_collect_parameters["anomalous"],
                                                   data_collect_parameters["residues"],
                                                   inverse_beam,
                                                   data_collect_parameters["do_inducedraddam"],
                                                   in_multicollect,
                                                   data_collect_parameters.get("sample_reference", {}).get("spacegroup", ""),
                                                   data_collect_parameters.get("sample_reference", {}).get("cell", ""))
                
                self.synchronize_thread(file_location, filename)
                frame += 1

            self.sync_collect(file_location, filename, image_file_template)
            self.finalize_acquisition()
    
    def generate_image_jpeg(self, *args):
        pass
    
    def last_image_saved(self, *args):
        pass
    
    def set_helical_pos(self, *args):
        pass
    
def test():
    import os
    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    coll = hwr.getHardwareObject("/mxcollect")

    print "Machine current is ", coll.get_machine_current()
    print "Synchrotron name is ", coll.bl_config.synchrotron_name
    res_corner = coll.get_resolution_at_corner()
    print "Resolution corner is ", res_corner

if __name__ == '__main__':
   test()

