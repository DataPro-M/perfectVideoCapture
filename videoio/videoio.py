"""Perfect video Capture module."""

import threading
import time
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import utils.helpers as hvio
from utils.fps import FPS
from utils.redis_shmem import RedisShmem
from utils.video_writer import video_writer


class RedisVideoCapture:
    """RedisVideoCapture class."""

    def __init__(self, cfg: Dict) -> None:
        """Initialize the video capture context."""
        if int(cfg["defaultArgs"]["--verbose"]) == 1:
            print("\n[INFO] Initializing VideoCapture context")
        self.src = cfg["defaultArgs"]["--src"]
        self.stream = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
        self.shmem = RedisShmem(cfg)
        self.verbose = int(cfg["defaultArgs"]["--verbose"])
        self.writer = video_writer(cfg)
        self.rec_permit = cfg["record"]["rec_permit"]
        self.fps_rdg = int(cfg["defaultArgs"]["--fps_rdg"])
        self.fpsTime_rdg = 1 / float(self.fps_rdg) if self.fps_rdg != 0 else 0
        self.fps_van = (
            int(cfg["Analysis"]["fps_van"])
            if int(cfg["Analysis"]["fps_van"]) != 0
            else 12
        )
        self.fpsTime_van = 1 / float(self.fps_van) if self.fps_van != 0 else 0
        self.resolution = int(cfg["defaultArgs"]["--width"]), int(
            cfg["defaultArgs"]["--height"]
        )
        self.frame_fail_cnt = 0
        self.frame_fail_cnt_limit = 10
        self.capture_failed = False
        self.thread = None
        self.started = False
        self.grabbed, self.frame = self.stream.read()

    def __str__(self) -> str:
        """Print the video capture context."""
        return str(self.__class__) + ": " + str(self.__dict__)

    def start(self) -> None:
        """Start the thread to read frames from the video stream."""
        if self.verbose == 2:
            print("[INFO] Starting threaded video capturing")
        self.started = True
        # start the thread to read frames from the video stream
        self.thread = threading.Thread(target=self.update, args=())  # type: ignore
        self.thread.start()  # type: ignore

    def waitOnFrameBuf(self) -> None:
        """Wait until the frame buffer is full."""
        while not self.capture_failed and (self.shmem.qsize() < self.shmem.q_size):
            # 1/4 of FPS sleep
            time.sleep(1.0 / (self.fps_van * 4)) if self.fps_van != 0 else time.sleep(
                0.1
            )

    def update_grabbed(self, frame: np.ndarray) -> None:
        """Update context if the frame is grabbed."""
        # resize frame to resolution
        self.frame = self.shmem.resizeFrame(frame, self.resolution)

        # put frame into buffer
        self.shmem.put_Q(self.frame)

        if self.frame_fail_cnt > 0:
            self.frame_fail_cnt = 0  # reset counter

        if not self.capture_failed:
            self.capture_failed = False

    def update_failed(self) -> bool:
        """Update the video capture context if the frame is failed."""
        break_flag = False
        # if the frame is failed, increment the counter
        self.frame_fail_cnt += 1
        # if the frame is failed for more than 10 times, stop the video capture
        if self.frame_fail_cnt > self.frame_fail_cnt_limit:
            self.frame_fail_cnt = 0
            self.capture_failed = True
            break_flag = True
            if self.verbose == 2:
                print("[INFO] Capture failed, exiting")
        return break_flag

    def update(self) -> None:
        """Update the video capture context."""
        # start the FPS timer
        fps_log = FPS()
        fps_log.start()

        # loop over some frames and estimate the FPS
        while self.started:
            # get timestamp
            tic = time.time()

            # Get frame from the video source
            self.grabbed, frame = self.stream.read()

            # If we have successfully grabbed a frame.
            if self.grabbed:
                self.update_grabbed(frame)

            # If we failed to grab a frame
            else:
                break_flag = self.update_failed()
                if break_flag:
                    break

            # Try to keep FPS consistent
            if self.fps_rdg != 0:
                hvio.sleep_fps(tic, self.fpsTime_rdg)

            # update FPS counter
            fps_log.update()

            if self.verbose == 1 and self.frame is not None:
                print(f"[INFO] approx. stream reader  FPS: {fps_log.fps():.2f}")
        # end while

        # stop the FPS timer
        fps_log.stop()

    # get the frame from the buffer
    def read(self) -> Tuple[Optional[np.ndarray], bool, str]:
        """Get the frame from the buffer."""
        return self.shmem.getFrame()

    def stop(self) -> None:
        """Stop the video capture context."""
        if self.verbose == 2:
            print("[INFO] Stopping threaded video capturing")
        self.started = False  # set flag to stop thread
        self.thread.join()  # type: ignore # wait for thread to finish
        self.stream.release()  # release video stream
