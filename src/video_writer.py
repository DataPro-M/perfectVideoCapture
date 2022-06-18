"""Video writer class."""

import os
import threading
import time
from collections import deque  # efficient queue data structure
from datetime import datetime
from queue import Queue  # thread safe queue
from typing import Deque, Dict

import ffmpeg
import numpy as np


class ffmpegwriter:
    """Video writer based on ffmpeg-python."""

    def __init__(
        self, fileName: str, vcodec: str, fps: int, frameWidth: int, frameHeight: int
    ) -> None:
        """Initialize the ffmpeg writer."""
        self.process = (
            ffmpeg.input(
                "pipe:",
                framerate=f"{fps}",
                format="rawvideo",
                pix_fmt="bgr24",
                s=f"{frameWidth}x{frameHeight}",
            )
            .output(
                fileName, vcodec=vcodec, pix_fmt="nv21", acodec="n", **{"b:v": 2000000}
            )
            .global_args("-hide_banner", "-nostats", "-loglevel", "panic")
            .overwrite_output()
            .run_async(pipe_stdin=True)
        )

    def write(self, image: np.ndarray) -> None:
        """Convert raw image format to something ffmpeg understands."""
        self.process.stdin.write(image.astype(np.uint8).tobytes())

    def close(self) -> None:
        """Clean up resources."""
        self.process.stdin.close()
        self.process.wait()


class video_writer:
    """Video writer class."""

    def __init__(self, cfg: Dict[str, Dict[str, str]]) -> None:
        """Initialize video writer."""
        self.cfg = cfg
        self.fps = int(self.cfg["record"]["fps_rec"])
        self.frameWidth = int(cfg["defaultArgs"]["--width"])
        self.frameHeight = int(cfg["defaultArgs"]["--height"])
        self.recDir = cfg["record"]["rec_dir"]
        self.cam_name = cfg["APP"]["cam_name"]
        self.file_ext = cfg["record"]["rec_file_ext"]
        self.vcodec = cfg["record"]["vcodec"]
        self.bufSize = int(cfg["record"]["rec_buf_sec"]) * self.fps
        self.verbose = int(cfg["defaultArgs"]["--verbose"])
        self.timeout = 0.01
        self.frame_Q: Deque[np.ndarray] = deque(maxlen=self.bufSize)
        self.Q: Queue[np.ndarray] = Queue()
        self.videoFileName = ""
        self.writer = None
        self.thread = None
        self.recStarted = False

    def qsize(self) -> int:
        """Return the approximate size of the queue."""
        return len(self.frame_Q)

    def makeFileName(self, timestamp: datetime, name: str) -> str:
        """Create file name based on image timestamp."""
        if self.verbose == 2:
            print("[INFO] Creating file name")

        # Construct directory name from camera name, recordDir and date
        dateStr = timestamp.strftime("%Y-%m-%d")
        fileDir = "%s/%s/%s" % (os.path.expanduser(self.recDir), self.cam_name, dateStr)

        # Create dir if it doesn't exist
        if not os.path.exists(fileDir):
            os.makedirs(fileDir)

        # Construct file name from camera name, timestamp and file extension
        fileName = "%s-%s.%s" % (name, timestamp.strftime("%H-%M-%S"), self.file_ext)
        return "%s/%s" % (fileDir, fileName)

    def update(self, frame: np.ndarray) -> None:
        """Write frames to video file."""
        self.frame_Q.appendleft(frame)

        # if we are recording, update the queue as well
        if self.recStarted:
            self.Q.put(frame)

    def recStart(self, timestamp: datetime, name: str) -> None:
        """Start recording video."""
        if self.verbose == 2:
            print("[INFO] Starting recording")

        # Start recording
        self.recStarted = True
        self.Q = Queue()

        # Create file name
        self.videoFileName = self.makeFileName(timestamp, name)

        # Create video writer
        self.writer = ffmpegwriter(
            fileName=self.videoFileName,
            vcodec=self.vcodec,
            fps=self.fps,
            frameWidth=self.frameWidth,
            frameHeight=self.frameHeight,
        )  # type: ignore

        # loop over the frames in the deque structure and add them
        # to the queue
        for i in range(len(self.frame_Q), 0, -1):
            self.Q.put(self.frame_Q[i - 1])

        # Start thread to write frames
        self.thread = threading.Thread(target=self.writeFrames)  # type: ignore
        # like the garbage collection task
        self.thread.daemon = True  # type: ignore
        self.thread.start()  # type: ignore

    def writeFrames(self) -> None:
        """Write frames to video file."""
        if self.verbose == 2:
            print("[INFO] Writing frames")

        while self.recStarted:
            # check to see if there are entries in the queue
            if self.Q.qsize() >= self.bufSize:
                # grab the next frame
                frame = self.Q.get()
                self.writer.write(frame)  # type: ignore
            # otherwise, wait for a bit (not wasting CPU cycles)
            else:
                time.sleep(self.timeout)

    def flush(self) -> None:
        """Flush frames in queue."""
        if self.verbose == 2:
            print(f"[INFO] Flushing {self.Q.qsize()} frames")

        # empty the queue by flushing all remaining frames to file
        while not self.Q.empty():
            frame = self.Q.get()
            self.writer.write(frame)  # type: ignore

    def recStop(self) -> None:
        """Stop recording video."""
        if self.verbose == 2:
            print("[INFO] Stopping recording")

        # indicating that we have completed our recording,
        # Join the thread, then flush all remaining frames
        # in the queue to file and free the writer pointer.
        self.recStarted = False  # reset flag to stop recording thread
        if self.thread is not None:
            self.thread.join()
        if self.writer is not None:
            self.flush()
            self.writer.close()
