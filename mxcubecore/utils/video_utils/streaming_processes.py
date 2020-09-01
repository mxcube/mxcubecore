#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utileties for starting video encoding and streaming."""

import os
import fcntl
import subprocess
import sys
import time
import uuid
import logging
import struct
import ast
import statistics

from multiprocessing import Process


def initialize_loopback_device(
    loopback_device, width, height, channels, pixel_format=None
):
    import v4l2

    if os.path.exists(loopback_device):
        device = open(loopback_device, "wb", 0)
    else:
        msg = "Cannot open video device %s, path do not exist. " % loopback_device
        msg += "Make sure that the v4l2loopback kernel module is loaded (modprobe v4l2loopback). "
        msg += "Falling back to MJPEG."
        raise RuntimeError(msg)

    f = v4l2.v4l2_format()
    f.type = v4l2.V4L2_BUF_TYPE_VIDEO_OUTPUT
    f.fmt.pix.pixelformat = v4l2.V4L2_PIX_FMT_RGB24
    f.fmt.pix.width = width
    f.fmt.pix.height = height
    f.fmt.pix.field = v4l2.V4L2_FIELD_NONE
    f.fmt.pix.bytesperline = width * channels
    f.fmt.pix.sizeimage = width * height * channels
    f.fmt.pix.colorspace = v4l2.V4L2_COLORSPACE_SRGB

    res = fcntl.ioctl(device, v4l2.VIDIOC_S_FMT, f)

    if res != 0:
        raise RuntimeError("Could not initialize video device: %d" % res)

    return device


def get_image(lima_tango_device):
    global LAST_FRAME

    img_data = lima_tango_device.video_last_image

    hfmt = ">IHHqiiHHHH"
    hsize = struct.calcsize(hfmt)
    _, _, img_mode, frame_number, width, height, _, _, _, _ = struct.unpack(
        hfmt, img_data[1][:hsize]
    )

    raw_data = img_data[1][hsize:]

    return raw_data, width, height, frame_number


def poll_image(encoder_input, device_uri, debug, sleep_time):
    from PyTango import DeviceProxy

    connected = False
    while not connected:
        try:
            logging.getLogger("HWR").info("Connecting to %s", device_uri)
            lima_tango_device = DeviceProxy(device_uri)
            lima_tango_device.ping()

        except Exception as ex:
            logging.getLogger("HWR").exception("")
            logging.getLogger("HWR").info(
                "Could not connect to %s, retrying ...", device_uri
            )
            connected = False
            time.sleep(0.2)
        else:
            connected = True

    if isinstance(encoder_input, str):
        encoder_input = open(encoder_input, "wb", 0)

    # sleep_time = lima_tango_device.video_exposure
    last_frame_number = -1
    dtlist = []
    mean_poll_t = sleep_time

    while True:
        try:
            t0 = time.perf_counter()
            data, width, height, frame_number = get_image(lima_tango_device)

            if last_frame_number != frame_number:
                encoder_input.write(data)
                last_frame_number = frame_number

            dt = time.perf_counter() - t0
            dtlist.append(dt)

            if len(dtlist) > 25:
                mean_poll_t = statistics.mean(dtlist)
                if debug:
                    print("Poll took, %s(s) \n" % mean_poll_t)

                dtlist = []

        except Exception as ex:
            print(ex)
        finally:
            _sleep_time = sleep_time - mean_poll_t

            if _sleep_time < 0:
                _sleep_time = 0

            time.sleep(_sleep_time)


def start_video_stream(
    size, scale, _hash, video_mode, loopback_device=None, debug=False
):
    """
    Start encoding with ffmpeg and stream the video with the node
    websocket relay.

    :param str scale: Video width and height
    :param str _hash: Hash to use for relay
    :returns: Tupple with the two processes performing streaming and encoding
    :rtype: tuple
    """
    websocket_relay_js = os.path.join(os.path.dirname(__file__), "websocket-relay.js")

    if debug:
        STDOUT = subprocess.STDOUT
    else:
        STDOUT = open(os.devnull, "w")

    relay = subprocess.Popen(
        ["node", websocket_relay_js, _hash, "4041", "4042"], close_fds=True
    )

    # Make sure that the relay is running (socket is open)
    time.sleep(2)

    size = "%sx%s" % size
    w, h = scale

    if not loopback_device:
        ffmpeg_args = [
            "ffmpeg",
            "-fflags",
            "nobuffer",
            "-fflags",
            "discardcorrupt",
            "-flags",
            "low_delay",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-s",
            size,
            "-i",
            "-",
            "-vf",
            "scale=w=%s:h=%s" % (w, h),
            "-f",
            "mpegts",
            "-b:v",
            "10M",
            "-q:v",
            "4",
            "-an",
            "-vcodec",
            "mpeg1video",
            "http://localhost:4041/" + _hash,
        ]
    else:
        ffmpeg_args = [
            "ffmpeg",
            "-fflags",
            "nobuffer",
            "-fflags",
            "discardcorrupt",
            "-flags",
            "low_delay",
            "-f",
            "v4l2",
            "-framerate",
            "30",
            "-i",
            loopback_device,
            "-vf",
            "scale=w=%s:h=%s" % (w, h),
            "-f",
            "mpegts",
            "-b:v",
            "10M",
            "-q:v",
            "4",
            "-an",
            "-vcodec",
            "mpeg1video",
            "http://localhost:4041/" + _hash,
        ]

    ffmpeg = subprocess.Popen(
        ffmpeg_args, stderr=STDOUT, stdin=subprocess.PIPE, shell=False, close_fds=True
    )

    with open("/tmp/mxcube.pid", "a") as f:
        f.write("%s %s" % (relay.pid, ffmpeg.pid))

    return relay, ffmpeg


if __name__ == "__main__":
    try:
        video_device_uri = sys.argv[1].strip()
    except IndexError:
        video_device_uri = ""

    try:
        size = sys.argv[2].strip()
    except IndexError:
        size = "-1,-1"
    finally:
        size = tuple(size.split(","))

    try:
        scale = sys.argv[3].strip()
    except IndexError:
        scale = "-1,-1"
    finally:
        scale = tuple(scale.split(","))

    try:
        _hash = sys.argv[4].strip()
    except IndexError:
        _hash = "-1,-1"

    try:
        video_mode = sys.argv[5].strip()
    except IndexError:
        video_mode = "rgb24"

    try:
        loopback_device = sys.argv[6].strip()
    except IndexError:
        loopback_device = None

    try:
        debug = ast.literal_eval(sys.argv[7].strip())
    except IndexError:
        debug = False

    try:
        sleep_time = float(sys.argv[8].strip())
    except IndexError:
        sleep_time = 0.05

    # The stream has to exist before encoding it using V4L2, so polling is
    # started in subprocess
    if loopback_device:
        encoder_input = initialize_loopback_device(
            loopback_device, int(size[0]), int(size[1]), 3
        )
        p = Process(
            target=poll_image, args=(encoder_input, video_device_uri, debug, sleep_time)
        ).start()

    relay, ffmpeg = start_video_stream(
        size, scale, _hash, video_mode, loopback_device, debug
    )

    # Polling started after ffmpeg when using direct pipe as handle
    # to ffmpeg stdin is needed
    if not loopback_device:
        poll_image(ffmpeg.stdin, video_device_uri, debug, sleep_time)
