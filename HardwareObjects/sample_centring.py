from scipy import optimize
import numpy
import gevent.event
import math
import time

#try:
#  import lucid
#except ImportError:
#  logging.warning("lucid cannot load: automatic centring is disabled")


def multiPointCentre(z,phis) :
    fitfunc = lambda p,x: p[0] * numpy.sin(x+p[1]) + p[2]
    errfunc = lambda p,x,y: fitfunc(p,x) - y
    p1, success = optimize.leastsq(errfunc,[1.,0.,0.],args = (phis,z))
    return p1

USER_CLICKED_EVENT = None
CURRENT_CENTRING = None
SAVED_INITIAL_POSITIONS = {}

class CentringMotor:
  def __init__(self, motor, reference_position=None, direction=1):
    self.motor = motor
    self.direction = direction
    self.reference_position = reference_position if reference_position is not None else motor.getPosition()
  def __getattr__(self, attr):
    # delegate to motor object
    if attr.startswith("__"):
      raise AttributeError(attr)
    else:
      return getattr(self.motor, attr)
    
def start(centring_motors_dict,
          pixelsPerMm_Hor, pixelsPerMm_Ver, 
          beam_xc, beam_yc,
          chi_angle = 0,
          n_points = 3):
  global USER_CLICKED_EVENT
  global CURRENT_CENTRING
  global SAVED_INITIAL_POSITIONS

  if CURRENT_CENTRING and not CURRENT_CENTRING.ready():
    raise RuntimeError("Cannot start new centring while centring in progress")

  USER_CLICKED_EVENT = gevent.event.AsyncResult()  

  move_motors(dict([(m.motor, m.reference_position) for m in centring_motors_dict.itervalues()]))
  SAVED_INITIAL_POSITIONS = dict([(m, m.motor.getPosition()) for m in centring_motors_dict.itervalues()])
  
  phi = centring_motors_dict["phi"]
  phiy = centring_motors_dict["phiy"]
  sampx = centring_motors_dict["sampx"]
  sampy = centring_motors_dict["sampy"]

  CURRENT_CENTRING = gevent.spawn(center, 
                                  phi,
                                  phiy,
                                  sampx, 
                                  sampy, 
                                  pixelsPerMm_Hor, pixelsPerMm_Ver, 
                                  beam_xc, beam_yc,
                                  chi_angle,
                                  n_points)
  return CURRENT_CENTRING

def ready(*motors):
  return not any([m.motorIsMoving() for m in motors])

def move_motors(motor_positions_dict):
  def wait_ready(timeout=None):
    with gevent.Timeout(timeout):
      while not ready(*motor_positions_dict.keys()):
        time.sleep(0.1)

  wait_ready(timeout=3)

  if not ready(*motor_positions_dict.keys()):
    raise RuntimeError("Motors not ready")

  for motor, position in motor_positions_dict.iteritems():
    motor.move(position)
  
  wait_ready()
  
def user_click(x,y):
  USER_CLICKED_EVENT.set((x,y))

def center(phi, phiy,
           sampx, sampy, 
           pixelsPerMm_Hor, pixelsPerMm_Ver, 
           beam_xc, beam_yc,
           chi_angle,
           n_points):
  global USER_CLICKED_EVENT

  X, Y, phi_positions = [], [], []

  phi_angle = 180.0/(n_points-1)

  try:
    i = 0
    while i < n_points:
      x, y = USER_CLICKED_EVENT.get()
      X.append(x / float(pixelsPerMm_Hor))
      Y.append(y / float(pixelsPerMm_Ver))
      phi_positions.append(phi.direction*math.radians(phi.getPosition()))

      USER_CLICKED_EVENT = gevent.event.AsyncResult()
      
      phi.moveRelative(phi.direction*phi_angle)
      i += 1
  except:
    move_motors(SAVED_INITIAL_POSITIONS)
    raise

  chi_angle = math.radians(chi_angle)
  chiRotMatrix = numpy.matrix([[math.cos(chi_angle), -math.sin(chi_angle)],
                               [math.sin(chi_angle), math.cos(chi_angle)]])
  Z = chiRotMatrix*numpy.matrix([X,Y])
  z = Z[1]; avg_pos = Z[0].mean()

  r, a, offset = multiPointCentre(numpy.array(z).flatten(), phi_positions)
  dy = r * numpy.sin(a)
  dx = r * numpy.cos(a)
  
  d = chiRotMatrix.transpose()*numpy.matrix([[avg_pos],
                                             [offset]])

  d_horizontal =  d[0] - (beam_xc / float(pixelsPerMm_Hor))
  d_vertical =  d[1] - (beam_yc / float(pixelsPerMm_Ver))

  phi_pos = math.radians(phi.direction*phi.getPosition())
  phiRotMatrix = numpy.matrix([[math.cos(phi_pos), -math.sin(phi_pos)],
                               [math.sin(phi_pos), math.cos(phi_pos)]])
  vertical_move = phiRotMatrix*numpy.matrix([[0],d_vertical])
  
  centred_pos = SAVED_INITIAL_POSITIONS.copy()
  centred_pos.update({ sampx: float(sampx.getPosition() + sampx.direction*(dx + vertical_move[0,0])),
                       sampy: float(sampy.getPosition() + sampy.direction*(dy + vertical_move[1,0])),
                       phiy: float(phiy.getPosition() + phiy.direction*d_horizontal[0,0]) })
  return centred_pos


def end():
  centred_pos = CURRENT_CENTRING.get()
  try:
    move_motors(centred_pos)
  except:
    move_motors(SAVED_INITIAL_POSITIONS)
