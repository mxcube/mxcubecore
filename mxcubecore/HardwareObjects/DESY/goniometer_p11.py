#!/usr/bin/env python

import tango
from motor import tango_motor
import numpy as np
from math import sin, cos, radians
import gevent
import copy

class goniometer_p11:

    motor_name_mapping = [
    ("AlignmentX", "phix"),
    ("AlignmentY", "phiy"),
    ("AlignmentZ", "phiz"),
    ("CentringX", "sampx"),
    ("CentringY", "sampy"),
    ("Omega", "phi"),
    ("Kappa", "kappa"),
    ("Phi", "kappa_phi"),
    ("beam_x", "beam_x"),
    ("beam_y", "beam_y"),
]
    
    def __init__(self, align_direction=[0, 0, 1]):

        self.phi = tango_motor('p11/servomotor/eh.1.01')
        self.phiz = tango_motor('p11/motor/eh.3.14')
        self.phiy = tango_motor('p11/motor/eh.3.12')
        self.sampy = tango_motor('p11/piezomotor/eh.4.01')
        self.sampx = tango_motor('p11/piezomotor/eh.4.02')
        self.backlight = tango.DeviceProxy('p11/register/eh.o.3.05')

        self.motors = ['phi', 'phiz', 'phiy', 'sampx', 'sampy']

        self.md2_to_mxcube = dict(
            [(key, value) for key, value in self.motor_name_mapping]
        )
        self.mxcube_to_md2 = dict(
            [(value, key) for key, value in self.motor_name_mapping]
        )
        self.align_direction = align_direction
        #self.redis = redis.StrictRedis()
        self.observation_fields = ['chronos', 'Omega'] 
        self.observations = []
        self.centringx_direction = -1.
        self.centringy_direction = +1.
        self.alignmenty_direction = -1.
        self.alignmentz_direction = +1.

    def set_position(self, position, wait=True):
        moves = []
        print('current position', self.get_position())
        print('moving to ', position)
        for motor in position:
            moves.append(gevent.spawn(getattr(self, motor).set_position, position[motor]))
        gevent.joinall(moves)

    def get_position(self):
        return dict([(motor, getattr(self, motor).get_position()) for motor in self.motors])
    
    def check_position(self, position):
        pass

    def get_kappa_position(self):
        return 0.
    def get_phi_position(self):
        return 0.
    
    def get_aligned_position(self):
        return self.get_position()
    
    def insert_backlight(self):
        if not self.backlight.value:
            self.backlight.value = 1

    def extract_backlight(self):
        if self.backlight.value:
            self.backlight.value = 0

    def insert_frontlight(self):
        pass
        # if not self.frontlight.value:
        #     self.frontlight.value = 1

    def extract_frontlight(self):
        pass
        # if self.frontlight.value:
        #     self.frontlight.value = 0

    def get_omega_position(self):
        return self.phi.get_position()
    
    def get_aligned_position_from_reference_position_and_shift(self, reference_position, horizontal_shift, vertical_shift, AlignmentZ_reference=0.0, epsilon=1.e-3):
        print('reference_position', reference_position)
        print('horizontal_shift', horizontal_shift)
        print('vertical_shift', vertical_shift)

        alignmentz_shift = reference_position['phiz'] - AlignmentZ_reference
        if abs(alignmentz_shift) < epsilon:
            alignmentz_shift = 0
        
        vertical_shift += alignmentz_shift
        
        centringx_shift, centringy_shift = self.get_x_and_y(0, vertical_shift, reference_position['phi'])
        
        aligned_position = copy.deepcopy(reference_position)
        
        aligned_position['phiz'] -= alignmentz_shift
        aligned_position['phiy'] -= horizontal_shift
        aligned_position['sampx'] += centringx_shift
        aligned_position['sampy'] += centringy_shift
        #a_cx = r_cx + s_cx => s_cx = a_cx - r_cx
        #a_cy = r_cy + s_cy => s_cy = a_cy - r_cy
        #a_az = r_az - s_az => s_az = r_az - a_az
        #a_ay = r_ay - s_ay => s_ay = r_ay - a_ay
        return aligned_position
    
    def get_vertical_and_horizontal_shift_between_two_positions(self, aligned_position, reference_position, epsilon=1.e-3):
        horizontal_shift = reference_position['phiy'] - aligned_position['phiy']
        alignmentz_shift = reference_position['phiz'] - aligned_position['phiz']
        centringx_shift = aligned_position['sampx'] - reference_position['sampx'] 
        centringy_shift = aligned_position['sampy'] - reference_position['sampy']
        
        focus, vertical_shift = self.get_focus_and_vertical(centringx_shift, centringy_shift, reference_position['phi'])
        if abs(alignmentz_shift) > epsilon:
            vertical_shift -= alignmentz_shift
            
        return np.array([vertical_shift, horizontal_shift])
    
    def get_aligned_position_from_reference_position_and_x_and_y(self, reference_position, x, y, AlignmentZ_reference=0.0):
        horizontal_shift = x - reference_position['sampy']
        vertical_shift = y - reference_position['sampx']
        
        return self.get_aligned_position_from_reference_position_and_shift(reference_position, horizontal_shift, vertical_shift, AlignmentZ_reference=AlignmentZ_reference)
        
    
    def get_x_and_y(self, focus, vertical, omega):
        omega = -radians(omega)
        R = np.array([[cos(omega), -sin(omega)], [sin(omega), cos(omega)]])
        R = np.linalg.pinv(R)
        return np.dot(R, [-focus, vertical])
    
    def get_focus_and_vertical(self, x, y, omega):
        omega = radians(omega)
        R = np.array([[cos(omega), -sin(omega)], [sin(omega), cos(omega)]])
        return np.dot(R, [-x, y])
    
    def set_omega_position(self, omega_position):
        self.phi.set_position(omega_position)

    def get_points_in_goniometer_frame(self, points, calibration, origin, center=np.array([160, 256, 256]), directions=np.array([-1,1,1]), order=[1,2,0]):
        mm = ((points-center)*calibration*directions)[:, order] + origin
        return mm

    def save_position(self):
        pass

 
    def get_move_vector_dictionary_from_fit(self, fit_vertical, fit_horizontal):
        c, r, alpha = fit_vertical.x
        
        centringx_direction=1
        centringy_direction=1.
        alignmenty_direction=1.
        alignmentz_direction=1.
        
        d_sampx = centringx_direction * r * np.sin(alpha)
        d_sampy = centringy_direction * r * np.cos(alpha)
        d_y = alignmenty_direction * fit_horizontal.x[0]
        d_z = alignmentz_direction * c

        move_vector_dictionary = {
            "phiz": d_z,
            "phiy": d_y,
            "sampx": d_sampx,
            "sampy": d_sampy,
        }

        return move_vector_dictionary
    
    def get_aligned_position_from_fit_and_reference(self, fit_vertical, fit_horizontal, reference):
        move_vector_dictionary = self.get_move_vector_dictionary_from_fit(fit_vertical, fit_horizontal)
        aligned_position = {}
        for key in reference:
            aligned_position[key] = reference[key]
            if key in move_vector_dictionary:
                aligned_position[key] += move_vector_dictionary[key]
        return aligned_position
    
    def get_move_vector_dictionary(self, vertical_displacements, horizontal_displacements, angles, calibrations, centringx_direction=1, centringy_direction=1., alignmenty_direction=-1., alignmentz_direction=1., centring_model='circle'):
        
        if centring_model == 'refractive':
            initial_parameters = lmfit.Parameters()
            initial_parameters.add_many(
                ("c", 0.0, True, -5e3, +5e3, None, None),
                ("r", 0.0, True, 0.0, 4e3, None, None),
                ("alpha", -np.pi / 3, True, -2 * np.pi, 2 * np.pi, None, None),
                ("front", 0.01, True, 0.0, 1.0, None, None),
                ("back", 0.005, True, 0.0, 1.0, None, None),
                ("n", 1.31, True, 1.29, 1.33, None, None),
                ("beta", 0.0, True, -2 * np.pi, +2 * np.pi, None, None),
            )

            fit_y = lmfit.minimize(
                self.refractive_model_residual,
                initial_parameters,
                method="nelder",
                args=(angles, vertical_discplacements),
            )
            self.log.info(fit_report(fit_y))
            optimal_params = fit_y.params
            v = optimal_params.valuesdict()
            c = v["c"]
            r = v["r"]
            alpha = v["alpha"]
            front = v["front"]
            back = v["back"]
            n = v["n"]
            beta = v["beta"]
            c *= 1.e-3
            r *= 1.e-3
            front *= 1.e-3
            back *= 1.e-3
            
        elif centring_model == 'circle':
            initial_parameters = [np.mean(vertical_discplacements), np.std(vertical_discplacements)/np.sin(np.pi/4), np.random.rand()*np.pi]
            fit_y = minimize(
                self.circle_model_residual,
                initial_parameters,
                method="nelder-mead",
                args=(angles, vertical_discplacements),
            )

            c, r, alpha = fit_y.x
            c *= 1.e-3
            r *= 1.e-3
            v = {"c": c, "r": r, "alpha": alpha}

        horizontal_center = np.mean(horizontal_displacements)

        d_sampx = centringx_direction * r * np.sin(alpha)
        d_sampy = centringy_direction * r * np.cos(alpha)
        d_y = alignmenty_direction * horizontal_center
        d_z = alignmentz_direction * c

        move_vector_dictionary = {
            "phiz": d_z,
            "phiy": d_y,
            "sampx": d_sampx,
            "sampy": d_sampy,
        }

        return move_vector_dictionary
    def circle_model(self, angles, c, r, alpha):
        return c + r*np.cos(angles - alpha)
    
    def circle_model_residual(self, varse, angles, data):
        c, r, alpha = varse
        model = self.circle_model(angles, c, r, alpha)
        return 1./(2*len(model)) * np.sum(np.sum(np.abs(data - model)**2))

    def projection_model(self, angles, c, r, alpha):
        return c + r*np.cos(np.dot(2, angles) - alpha)

    def projection_model_residual(self, varse, angles, data):
        c, r, alpha = varse
        model = self.projection_model(angles, c, r, alpha)
        return 1./(2*len(model)) * np.sum(np.sum(np.abs(data - model)**2))
    
    def translate_from_mxcube_to_md2(self, position):
        translated_position = {}

        for key in position:
            if isinstance(key, str):
                try:
                    translated_position[self.mxcube_to_md2[key]] = position[key]
                except:
                    pass
                    #self.log.exception(traceback.format_exc())
                
            else:
                translated_position[key.actuator_name] = position[key]
        return translated_position
    
    def translate_from_md2_to_mxcube(self, position):
        print('position to translate', position)
        translated_position = {}

        for key in position:
            translated_position[self.md2_to_mxcube[key]] = position[key]

        return translated_position