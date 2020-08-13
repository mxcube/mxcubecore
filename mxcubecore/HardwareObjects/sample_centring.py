from scipy import optimize
import numpy
import gevent.event
import math
import time
import logging
import os
import tempfile

try:
    import lucid3 as lucid
except ImportError:
    try:
        import lucid
    except ImportError:
        logging.warning(
            "Could not find autocentring library, automatic centring is disabled"
        )


def multiPointCentre(z, phis):
    def fitfunc(p, x):
        return p[0] * numpy.sin(x + p[1]) + p[2]

    def errfunc(p, x, y):
        return fitfunc(p, x) - y

    p1, success = optimize.leastsq(errfunc, [1.0, 0.0, 0.0], args=(phis, z))
    return p1


USER_CLICKED_EVENT = None
CURRENT_CENTRING = None
SAVED_INITIAL_POSITIONS = {}
READY_FOR_NEXT_POINT = gevent.event.Event()


class CentringMotor:
    def __init__(self, motor, reference_position=None, direction=1):
        self.motor = motor
        self.direction = direction
        self.reference_position = reference_position

    def __getattr__(self, attr):
        # delegate to motor object
        if attr.startswith("__"):
            raise AttributeError(attr)
        else:
            return getattr(self.motor, attr)


def prepare(centring_motors_dict):
    global SAVED_INITIAL_POSITIONS

    if CURRENT_CENTRING and not CURRENT_CENTRING.ready():
        end()

    global USER_CLICKED_EVENT
    USER_CLICKED_EVENT = gevent.event.AsyncResult()

    motors_to_move = dict()
    for m in centring_motors_dict.values():
        if m.reference_position is not None:
            motors_to_move[m.motor] = m.reference_position
    move_motors(motors_to_move)

    SAVED_INITIAL_POSITIONS = dict(
        [(m.motor, m.motor.get_value()) for m in centring_motors_dict.values()]
    )

    phi = centring_motors_dict["phi"]
    phiy = centring_motors_dict["phiy"]
    sampx = centring_motors_dict["sampx"]
    sampy = centring_motors_dict["sampy"]
    phiz = centring_motors_dict["phiz"]

    return phi, phiy, phiz, sampx, sampy


def start(
    centring_motors_dict,
    pixelsPerMm_Hor,
    pixelsPerMm_Ver,
    beam_xc,
    beam_yc,
    chi_angle=0,
    n_points=3,
):
    global CURRENT_CENTRING

    phi, phiy, phiz, sampx, sampy = prepare(centring_motors_dict)

    CURRENT_CENTRING = gevent.spawn(
        center,
        phi,
        phiy,
        phiz,
        sampx,
        sampy,
        pixelsPerMm_Hor,
        pixelsPerMm_Ver,
        beam_xc,
        beam_yc,
        chi_angle,
        n_points,
    )
    return CURRENT_CENTRING


def start_plate(
    centring_motors_dict,
    pixelsPerMm_Hor,
    pixelsPerMm_Ver,
    beam_xc,
    beam_yc,
    plate_vertical,
    chi_angle=0,
    n_points=3,
    phi_range=10,
    lim_pos=314.0,
):
    global CURRENT_CENTRING

    plateTranslation = centring_motors_dict["plateTranslation"]
    centring_motors_dict.pop("plateTranslation")
    phi, phiy, phiz, sampx, sampy = prepare(centring_motors_dict)

    phi.set_value(lim_pos)

    CURRENT_CENTRING = gevent.spawn(
        centre_plate,
        phi,
        phiy,
        phiz,
        sampx,
        sampy,
        plateTranslation,
        pixelsPerMm_Hor,
        pixelsPerMm_Ver,
        beam_xc,
        beam_yc,
        plate_vertical,
        chi_angle,
        n_points,
        phi_range,
    )
    return CURRENT_CENTRING


def start_plate_1_click(
    centring_motors_dict,
    pixelsPerMm_Hor,
    pixelsPerMm_Ver,
    beam_xc,
    beam_yc,
    plate_vertical,
    phi_min,
    phi_max,
    n_points=10,
):
    global CURRENT_CENTRING

    # plateTranslation = centring_motors_dict["plateTranslation"]
    # centring_motors_dict.pop("plateTranslation")

    # phi, phiy,phiz, sampx, sampy = prepare(centring_motors_dict)

    phi = centring_motors_dict["phi"]
    phiy = centring_motors_dict["phiy"]
    sampx = centring_motors_dict["sampx"]
    sampy = centring_motors_dict["sampy"]
    phiz = centring_motors_dict["phiz"]

    # phi.set_value(phi_min)
    plate_vertical()

    CURRENT_CENTRING = gevent.spawn(
        centre_plate1Click,
        phi,
        phiy,
        phiz,
        sampx,
        sampy,
        pixelsPerMm_Hor,
        pixelsPerMm_Ver,
        beam_xc,
        beam_yc,
        plate_vertical,
        phi_min,
        phi_max,
        n_points,
    )

    return CURRENT_CENTRING


def centre_plate1Click(
    phi,
    phiy,
    phiz,
    sampx,
    sampy,
    pixelsPerMm_Hor,
    pixelsPerMm_Ver,
    beam_xc,
    beam_yc,
    plate_vertical,
    phi_min,
    phi_max,
    n_points,
):

    global USER_CLICKED_EVENT

    try:
        i = 0
        previous_click_x = 99999
        previous_click_y = 99999
        dx = 99999
        dy = 99999

        # while i < n_points and (dx > 3 or dy > 3) :
        while (
            True
        ):  # it is now a while true loop that can be interrupted at any time by the save button, to allow user to have a 1 click centring as precise as he wants (see HutchMenuBrick)
            USER_CLICKED_EVENT = gevent.event.AsyncResult()
            try:
                x, y = USER_CLICKED_EVENT.get()
            except BaseException:
                raise RuntimeError("Aborted while waiting for point selection")

            # Move to beam
            phiz.set_value_relative((y - beam_yc) / float(pixelsPerMm_Ver))
            phiy.set_value_relative(-(x - beam_xc) / float(pixelsPerMm_Hor))

            # Distance to previous click to end centring if it converges
            dx = abs(previous_click_x - x)
            dy = abs(previous_click_y - y)
            previous_click_x = x
            previous_click_y = y

            # Alterning between phi min and phi max to gradually converge to the
            # centring point
            if i % 2 == 0:
                phi_min = (
                    phi.get_value()
                )  # in case the phi range sent us to a position where sample is invisible, if user moves phi, this modifications is saved for future moves
                phi.set_value(phi_max)
            else:
                phi_max = (
                    phi.get_value()
                )  # in case the phi range sent us to a position where sample is invisible, if user moves phi, this modifications is saved for future moves
                phi.set_value(phi_min)

            READY_FOR_NEXT_POINT.set()
            i += 1
    except BaseException:
        logging.exception("Exception while centring")
        move_motors(SAVED_INITIAL_POSITIONS)
        raise

    plate_vertical()

    centred_pos = SAVED_INITIAL_POSITIONS.copy()

    centred_pos.update(
        {sampx.motor: float(sampx.get_value()), sampy.motor: float(sampy.get_value())}
    )

    return centred_pos


def centre_plate(
    phi,
    phiy,
    phiz,
    sampx,
    sampy,
    plateTranslation,
    pixelsPerMm_Hor,
    pixelsPerMm_Ver,
    beam_xc,
    beam_yc,
    plate_vertical,
    chi_angle,
    n_points,
    phi_range=40,
):
    global USER_CLICKED_EVENT
    X, Y, phi_positions = [], [], []

    phi_angle = phi_range / (n_points - 1)

    try:
        i = 0
        while i < n_points:
            try:
                x, y = USER_CLICKED_EVENT.get()
            except BaseException:
                raise RuntimeError("Aborted while waiting for point selection")
            USER_CLICKED_EVENT = gevent.event.AsyncResult()
            X.append(x / float(pixelsPerMm_Hor))
            Y.append(y / float(pixelsPerMm_Ver))
            phi_positions.append(phi.direction * math.radians(phi.get_value()))
            if i != n_points - 1:
                phi.set_value_relative(phi.direction * phi_angle, timeout=None)
            READY_FOR_NEXT_POINT.set()
            i += 1
    except BaseException:
        logging.exception("Exception while centring")
        move_motors(SAVED_INITIAL_POSITIONS)
        raise

    # logging.info("X=%s,Y=%s", X, Y)
    chi_angle = math.radians(chi_angle)
    chiRotMatrix = numpy.matrix(
        [
            [math.cos(chi_angle), -math.sin(chi_angle)],
            [math.sin(chi_angle), math.cos(chi_angle)],
        ]
    )
    Z = chiRotMatrix * numpy.matrix([X, Y])
    z = Z[1]
    avg_pos = Z[0].mean()

    r, a, offset = multiPointCentre(numpy.array(z).flatten(), phi_positions)
    dy = r * numpy.sin(a)
    dx = r * numpy.cos(a)

    d = chiRotMatrix.transpose() * numpy.matrix([[avg_pos], [offset]])

    d_horizontal = d[0] - (beam_xc / float(pixelsPerMm_Hor))
    d_vertical = d[1] - (beam_yc / float(pixelsPerMm_Ver))

    phi_pos = math.radians(phi.direction * phi.get_value())
    phiRotMatrix = numpy.matrix(
        [
            [math.cos(phi_pos), -math.sin(phi_pos)],
            [math.sin(phi_pos), math.cos(phi_pos)],
        ]
    )

    centred_pos = SAVED_INITIAL_POSITIONS.copy()
    centred_pos.update(
        {
            sampx.motor: float(sampx.get_value() + sampx.direction * dx),
            sampy.motor: float(sampy.get_value() + sampy.direction * dy),
            phiz.motor: float(phiz.get_value() + phiz.direction * d_vertical[0, 0])
            if phiz.__dict__.get("reference_position") is None
            else phiz.reference_position,
            phiy.motor: float(phiy.get_value() + phiy.direction * d_horizontal[0, 0])
            if phiy.__dict__.get("reference_position") is None
            else phiy.reference_position,
        }
    )

    move_motors(centred_pos)
    plate_vertical()
    """
  try:
    x, y = USER_CLICKED_EVENT.get()
  except:
    raise RuntimeError("Aborted while waiting for point selection")
  USER_CLICKED_EVENT = gevent.event.AsyncResult()
  y_offset = -(y-beam_yc)  / float(pixelsPerMm_Ver)
  plateTranslation.set_value_relative(y_offset)
  """

    return centred_pos


def ready(*motors):
    return all([m.is_ready() for m in motors])


def move_motors(motor_positions_dict):
    def wait_ready(timeout=None):
        with gevent.Timeout(timeout):
            while not ready(*motor_positions_dict.keys()):
                time.sleep(0.1)

    wait_ready(timeout=30)

    if not ready(*motor_positions_dict.keys()):
        raise RuntimeError("Motors not ready")

    for motor, position in motor_positions_dict.items():
        motor.set_value(position)

    wait_ready()


def user_click(x, y, wait=False):
    READY_FOR_NEXT_POINT.clear()
    USER_CLICKED_EVENT.set((x, y))
    if wait:
        READY_FOR_NEXT_POINT.wait()


def center(
    phi,
    phiy,
    phiz,
    sampx,
    sampy,
    pixelsPerMm_Hor,
    pixelsPerMm_Ver,
    beam_xc,
    beam_yc,
    chi_angle,
    n_points,
    phi_range=180,
):
    global USER_CLICKED_EVENT
    X, Y, phi_positions = [], [], []

    phi_angle = phi_range / (n_points - 1)

    try:
        i = 0
        while i < n_points:
            try:
                x, y = USER_CLICKED_EVENT.get()
            except BaseException:
                raise RuntimeError("Aborted while waiting for point selection")
            USER_CLICKED_EVENT = gevent.event.AsyncResult()
            X.append(x / float(pixelsPerMm_Hor))
            Y.append(y / float(pixelsPerMm_Ver))
            phi_positions.append(phi.direction * math.radians(phi.get_value()))
            if i != n_points - 1:
                phi.set_value_relative(phi.direction * phi_angle, timeout=10)
            READY_FOR_NEXT_POINT.set()
            i += 1
    except BaseException:
        logging.exception("Exception while centring")
        move_motors(SAVED_INITIAL_POSITIONS)
        raise

    # logging.info("X=%s,Y=%s", X, Y)
    chi_angle = math.radians(chi_angle)
    chiRotMatrix = numpy.matrix(
        [
            [math.cos(chi_angle), -math.sin(chi_angle)],
            [math.sin(chi_angle), math.cos(chi_angle)],
        ]
    )
    Z = chiRotMatrix * numpy.matrix([X, Y])
    z = Z[1]
    avg_pos = Z[0].mean()

    r, a, offset = multiPointCentre(numpy.array(z).flatten(), phi_positions)
    dy = r * numpy.sin(a)
    dx = r * numpy.cos(a)

    d = chiRotMatrix.transpose() * numpy.matrix([[avg_pos], [offset]])

    d_horizontal = d[0] - (beam_xc / float(pixelsPerMm_Hor))
    d_vertical = d[1] - (beam_yc / float(pixelsPerMm_Ver))

    phi_pos = math.radians(phi.direction * phi.get_value())
    phiRotMatrix = numpy.matrix(
        [
            [math.cos(phi_pos), -math.sin(phi_pos)],
            [math.sin(phi_pos), math.cos(phi_pos)],
        ]
    )

    centred_pos = SAVED_INITIAL_POSITIONS.copy()
    centred_pos.update(
        {
            sampx.motor: float(sampx.get_value() + sampx.direction * dx),
            sampy.motor: float(sampy.get_value() + sampy.direction * dy),
            phiz.motor: float(phiz.get_value() + phiz.direction * d_vertical[0, 0])
            if phiz.__dict__.get("reference_position") is None
            else phiz.reference_position,
            phiy.motor: float(phiy.get_value() + phiy.direction * d_horizontal[0, 0])
            if phiy.__dict__.get("reference_position") is None
            else phiy.reference_position,
        }
    )

    return centred_pos


def end(centred_pos=None):
    if centred_pos is None:
        centred_pos = CURRENT_CENTRING.get()
    try:
        move_motors(centred_pos)
    except BaseException:
        logging.exception("Exception in centring 'end`, centred pos is %s", centred_pos)
        move_motors(SAVED_INITIAL_POSITIONS)
        raise


def start_auto(
    camera,
    centring_motors_dict,
    pixelsPerMm_Hor,
    pixelsPerMm_Ver,
    beam_xc,
    beam_yc,
    chi_angle=0,
    n_points=3,
    msg_cb=None,
    new_point_cb=None,
):
    global CURRENT_CENTRING

    phi, phiy, phiz, sampx, sampy = prepare(centring_motors_dict)

    CURRENT_CENTRING = gevent.spawn(
        auto_center,
        camera,
        phi,
        phiy,
        phiz,
        sampx,
        sampy,
        pixelsPerMm_Hor,
        pixelsPerMm_Ver,
        beam_xc,
        beam_yc,
        chi_angle,
        n_points,
        msg_cb,
        new_point_cb,
    )
    return CURRENT_CENTRING


def find_loop(camera, pixelsPerMm_Hor, chi_angle, msg_cb, new_point_cb):
    snapshot_filename = os.path.join(
        tempfile.gettempdir(), "mxcube_sample_snapshot.png"
    )
    camera.take_snapshot(snapshot_filename, bw=True)

    info, x, y = lucid.find_loop(
        snapshot_filename, rotation=-chi_angle, debug=False, IterationClosing=6)

    try:
        x = float(x)
        y = float(y)
    except Exception:
        return -1, -1

    if callable(msg_cb):
        msg_cb("Loop found: %s (%d, %d)" % (info, x, y))
    if callable(new_point_cb):
        new_point_cb((x, y))

    return x, y


def auto_center(
    camera,
    phi,
    phiy,
    phiz,
    sampx,
    sampy,
    pixelsPerMm_Hor,
    pixelsPerMm_Ver,
    beam_xc,
    beam_yc,
    chi_angle,
    n_points,
    msg_cb,
    new_point_cb,
):
    imgWidth = camera.get_width()
    imgHeight = camera.get_height()

    # check if loop is there at the beginning
    i = 0
    while -1 in find_loop(camera, pixelsPerMm_Hor, chi_angle, msg_cb, new_point_cb):
        phi.set_value_relative(90)
        i += 1
        if i > 4:
            if callable(msg_cb):
                msg_cb("No loop detected, aborting")
            return

    for k in range(1):
        if callable(msg_cb):
            msg_cb("Doing automatic centring")

        centring_greenlet = gevent.spawn(
            center,
            phi,
            phiy,
            phiz,
            sampx,
            sampy,
            pixelsPerMm_Hor,
            pixelsPerMm_Ver,
            beam_xc,
            beam_yc,
            chi_angle,
            n_points,
        )

        for a in range(n_points):
            x, y = find_loop(camera, pixelsPerMm_Hor, chi_angle, msg_cb, new_point_cb)
            # logging.info("in autocentre, x=%f, y=%f",x,y)
            if x < 0 or y < 0:
                for i in range(1, 18):
                    # logging.info("loop not found - moving back %d" % i)
                    phi.set_value_relative(5)
                    x, y = find_loop(
                        camera, pixelsPerMm_Hor, chi_angle, msg_cb, new_point_cb
                    )
                    if -1 in (x, y):
                        continue
                    if x >= 0:
                        if y < imgHeight / 2:
                            y = 0
                            if callable(new_point_cb):
                                new_point_cb((x, y))
                            user_click(x, y, wait=True)
                            break
                        else:
                            y = imgHeight
                            if callable(new_point_cb):
                                new_point_cb((x, y))
                            user_click(x, y, wait=True)
                            break
                if -1 in (x, y):
                    centring_greenlet.kill()
                    raise RuntimeError("Could not centre sample automatically.")
                phi.set_value_relative(-i * 5)
            else:
                user_click(x, y, wait=True)

        centred_pos = centring_greenlet.get()
        end(centred_pos)

    return centred_pos
