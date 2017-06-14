#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
EMBLAutoProcessing
"""

import pickle
import os
import commands
import re
import numpy
import scipy.ndimage
import glob
import scipy.misc
import traceback
import subprocess

import os
import time
import logging
import gevent 
import subprocess

from XSDataAutoprocv1_0 import XSDataAutoprocInput

from XSDataCommon import XSDataDouble
from XSDataCommon import XSDataFile
from XSDataCommon import XSDataInteger
from XSDataCommon import XSDataString

from HardwareRepository.BaseHardwareObjects import HardwareObject


__author__ = "Laurent Gadea"
__credits__ = ["MXCuBE colaboration"]
__version__ = "0."


class SOLEILPX2AutoProcessing(HardwareObject):
    """
    Descript. :
    """
    def __init__(self, name):
        """
        Descript. :
        """
        HardwareObject.__init__(self, name)
        self.result = None
        self.autoproc_programs = None
        self.current_autoproc_procedure = None
        self.spots = None

    def init(self):
        """
        Descript. :
        """
        self.autoproc_programs = self["programs"]

    def execute_autoprocessing(self, process_event, params_dict, 
                               frame_number, run_processing=True):
        """
        Descript. : 
        """
        self.autoproc_procedure(process_event,
                                params_dict, 
                                frame_number,
                                run_processing)
    
    
    def get_nspots_nimage(self,a):
        """
        return un dictionnaire contenant pour chaque image(numero) le pixel le plus fort
        """
        results = {}
        for line in a:
            try:
                nspots, nimage = map(int, re.findall('Found (\d*) strong pixels on image (\d*)', line)[0])
                results[nimage] = {}
                results[nimage]['dials_all_spots'] = nspots
            except:
                print traceback.print_exc()
        return results
    
    #
    def save_results(self,results_file, results):
        with open(results_file, 'w') as f:
            pickle.dump(results, f)
    
    #
    def get_parameters(self,directory, name_pattern):
        return pickle.load(open(os.path.join(directory, '%s_parameters.pickle' % name_pattern)))
    
    #create spot
    def get_z(self,parameters, results):
        """
        rempli chaque pixel de l'image par lq valeur du dials_spots
        [[ 0  1  2]
         [ 3  4  5]
         [ 6  7  8]
         [ 9 10 11]]
        """
        number_of_rows = parameters['number_of_rows']
        number_of_columns = parameters['number_of_columns']
        points = numpy.arange(1,number_of_columns*number_of_rows)
        #points = parameters['cell_positions']# contient x,y et le numero d'image
        #indexes = parameters['indexes'] # not used !!!!!!!!!!!!!!!!!!!!!!
        
        z = numpy.zeros((number_of_rows, number_of_columns))
    
        if parameters['scan_axis'] == 'horizontal':
            for r in range(number_of_rows):
                for c in range(number_of_columns):
                    for index in points:
                        try:
                            z[r,c] = results[int(index)]['score']
                        except KeyError:
                            z[r,c] = 0
            z = self.raster(z)
            z = self.mirror(z) 
        
        if parameters['scan_axis'] == 'vertical':
            z = numpy.ravel(z)
            for n in range(len(z)):
                try:
                    z[n] = results[n+1]['score']
                except:
                    z[n] = 0
            z = numpy.reshape(z, (number_of_columns, number_of_rows))
            z = self.raster(z)
            z = z.T
            z = self.mirror(z)

        return z
    
    def mirror(self,grid):
        """
        inverse grid sense
        v<<<<<<<<<
        >>>>>>>>>v
        v<<<<<<<<<
        [[ 2  1  0]
         [ 3  4  5]
         [ 8  7  6]
         [ 9 10 11]]
        """
        return self.raster(grid,k=0,l=1)
    
    def raster(self,grid, k=0, l=2): 
        """
        # donne le sense de l'acquisition ici >>>>>>>>v
        #                                     v<<<<<<<<
        #                                     >>>>>>>>v
        [[ 0  1  2]
         [ 5  4  3]
         [ 6  7  8]
         [11 10  9]]
        """
        gs = grid.shape
        orderedGrid = []
        for i in range(gs[0]):
            line = grid[i, :]
            if (i + 1) % l == k:
                line = line[: : -1]
            orderedGrid.append(line)
        return numpy.array(orderedGrid)
        
    def scale_z(self,z, scale):
        return scipy.ndimage.zoom(z, scale)
    
    # on
    def get_results(self,directory, name_pattern, parameters):
        """
        etape 1 : on utilise dials_env.sh pour rechercher dans chaque image le spot le plus fort
        etape2 : dans le fichier cree par le script ci-dessus on extrait les lignes correspondantes au reg
        etqpe3 : grep > fichier on cree alors un dic [image][spot]
        """
       
        #on suppose que le dossier existe
        results_file = os.path.join(directory, '%s_%s' % (name_pattern, 'results.pickle'))
                
        if not os.path.isfile(results_file):
            process_dir = os.path.join(directory, '%s_%s' % ('process', name_pattern) )
            
            spot_find_line = 'ssh process1 "source /usr/local/dials-v1-3-3/dials_env.sh; '\
                             'cd %s ;'\
                             'echo $(pwd); '\
                             'dials.find_spots shoebox=False per_image_statistics=True spotfinder.filter.ice_rings.filter=True nproc=80 ../%s_master.h5"' % (process_dir, name_pattern)
            subprocess.Popen(spot_find_line, shell=True, stdin=None,stdout=None, stderr=None, close_fds=True)
            while not os.path.isfile("%s/dials.find_spots.log" % process_dir):
                print 'Waiting for dials.find_spots.log file to appear on the disk'
                time.sleep(0.1)
            #fin du subprocess
            #recherche par re des lignes "Found 17 strong pixels on image 1055" dans le fichier dials.find_spots.log get_nspots_nimage
            rechercheSpot = commands.getoutput("grep  'Found' --include=dials.find_spots.log *").split('\n')
            
            #save des resultats dans 'results.pickle'
            self.save_results(results_file, self.get_nspots_nimage(rechercheSpot))
                
        return pickle.load(open(results_file))
        
    
    def generate_full_grid_image(self,z, center, angle=0, fullshape=(493, 659)):
        empty = numpy.zeros(fullshape)
        gd1, gd2 = z.shape
        cd1, cd2 = center
        start1 = int(cd1-gd1/2.)
        end1 = int(cd1+gd1/2.) 
        start2 = int(cd2-gd2/2.)
        end2 = int(cd2+gd2/2.) 
        s1 = 0
        s2 = 0
        e1 = gd1 + 1
        e2 = gd2 + 1
        if start1 < 0:
            s1 = -start1 + 1 
            start1 = 0
        if end1 > fullshape[0]:
            e1 = e1 - (end1 - fullshape[0]) - 2
            end1 = fullshape[0] + 1
        if start2 < 0:
            s2 = -start2 + 1
            start2 = 0
        if end2 > fullshape[1]:
            e2 = e2 - (end2 - fullshape[1]) - 1 
            end2 = fullshape[1] + 1
        empty[start1: end1, start2: end2] = z[s1: e1, s2: e2]
        full = empty
        return full
    
    def foundSpot(self,img):
        
        #found seuil > 0.9 
        center = img > 0.9* self.spots.max()
        labels, nlabels = scipy.ndimage.label(center)
        print 'labels ',labels
        print 'nlabels ',nlabels
        spots = numpy.ma.masked_array(labels, ~center)*255
        return spots
        

    def autoproc_procedure(self, process_event, params_dict, 
                           frame_number, run_processing=True):
        
        snapshot_directory = params_dict["fileinfo"]["archive_directory"]
        name_pattern = params_dict["fileinfo"]["template"]
        logging.info("SOLEILPX2AutoProcessing ")
        
        # step[1]
        results = self.get_results(snapshot_directory, name_pattern, parameters=None)
        
        #step[2]
        self.spots = self.get_z(parameters, results)
        grid_shape_on_real_image_in_pixels = lengths / calibration

        scale = grid_shape_on_real_image_in_pixels[::-1] / shape[::-1]
        
        # step[3]-Mise a l'echelle
        z_scaled = scipy.ndimage.zoom(self.spots, scale[::-1])
        
        # step[4] generation de l'image entiere 
        z_full = self.generate_full_grid_image(z_scaled, center)
        
        self.foundSpot(z_full)
    


    def autoproc_done(self, current_autoproc):
        """
        Descript. :
        """
        self.current_autoproc_procedure = None
    
    
    def create_autoproc_input(self, event, params):
        """
        Descript. : CODE EMBL
        """
        return None, True
        