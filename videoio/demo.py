#!/usr/bin/env python3

"""demo for Perfect video Capture module.

Usage:   videoio.py [--src=<RTSP-url>]
                        [--width=<pixel>] [--height=<pixel>]
                        [--fps_rdg=<int>]
                        [--verbose=<int>]

            videoio.py -h | --help | --version

"""

import datetime
import faulthandler
import itertools
import os
import socket
import sys
import time

import utils.helpers as hvio
from docopt import docopt
from utils.fps import FPS

from videoio import RedisVideoCapture  # type: ignore

lib_path = os.path.abspath(os.path.join(__file__, "..", "..", ""))
sys.path.append(lib_path)
from docs import config as cfg  # noqa: E402

# ==================================
faulthandler.enable()
config_path = os.path.dirname(os.path.abspath(cfg.__file__))


# ==================================
# main function
# ==================================
def main() -> None:
    """Implement the main function."""
    arguments = docopt(__doc__, version="0.1.1rc")

    # read the config file
    initfile = os.path.join(config_path, "config.ini")
    config, default_args = cfg.read_ini(initfile)

    # merge the arguments with the config file
    args = cfg.merge(arguments, default_args)
    verbose = int(args["--verbose"])

    try:
        # make the module unique to run on the same machine
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind("\0" + config["process"]["processname"])

        # set variables
        c = itertools.count(0)
        frameID = next(c)
        stop_bit = True
        rec_event = False

        # start the service
        if verbose == 2:
            print("[INFO] Starting service")

        while stop_bit:

            # initialize the video capture and start the thread
            cap = RedisVideoCapture(config)
            cap.start()

            # start the FPS logger
            fps_log = FPS()
            fps_log.start()

            # start the video reader main loop
            while cap.stream.isOpened():
                tic = time.time()

                # Wait until the shared memory is empty if capture fails.
                if cap.capture_failed and cap.shmem.empty():
                    break

                # get the frame from the buffer
                frame, grabbed, timestamp = cap.read()

                # Wait until the frame buffer is full
                cap.waitOnFrameBuf()

                # if the frame is grabbed, process it
                if grabbed:
                    frameID = next(c)  # increment frame ID
                    if verbose == 2:
                        print(
                            f"{frameID}-th frame grabbed @ {timestamp}"
                            f" and Q_size: {cap.shmem.qsize()}"
                        )

                # if permited to record
                if cap.rec_permit:
                    # fill the buffer of the video writer
                    cap.writer.update(frame)

                    # if we are not recording, start recording
                    if not cap.writer.recStarted and rec_event:
                        now = datetime.datetime.now()
                        cap.writer.recStart(now, "test_rec")

                    # if we are recording, stop recording
                    elif cap.writer.recStarted and not rec_event:
                        cap.writer.recStop()

                # Try to keep FPS consistent
                if cap.fps_van != 0:
                    hvio.sleep_fps(tic, cap.fpsTime_van)

                # update the FPS logger
                fps_log.update()
                if verbose == 1:
                    print(f"[INFO] approx. video analitic FPS: {fps_log.fps():.2f}")

                # Some dummy conditions!
                # recording event
                if frameID in range(100, 200):
                    if not rec_event:
                        rec_event = True

                # recording event finished
                elif rec_event and frameID > 200:
                    rec_event = False

                # Loop exiting condition
                elif frameID >= 300:
                    stop_bit = False
                    break
            # end while

            # stop the services
            cap.writer.recStop()
            cap.stop()
            fps_log.stop()
            time.sleep(1)
            cap = None

        print("[INFO] Exiting service")
        time.sleep(3)
        print("By")

    except socket.error as msg:
        print("Process already running.")
        print(str(msg) + "\n" + "Exiting")
        time.sleep(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
