"""Redis Shared memory video capture module."""

import datetime
import struct

import cv2
import numpy as np

import src.utils as utils


class RedisShmem(object):
    """RedisShmem class."""

    def __init__(self, cfg):
        """Initialize the RedisShmem context."""
        self.__db = utils.connect_redis(cfg["redis"]["host"], int(cfg["redis"]["port"]))
        self.Q_name = cfg["APP"]["cam_name"]
        self.key = "%s:%s" % ("namespace", self.Q_name)
        self.fps_van = (
            int(cfg["Analysis"]["fps_van"])
            if int(cfg["Analysis"]["fps_van"]) != 0
            else 12
        )
        self.q_size = int(cfg["Analysis"]["buf_sec"]) * self.fps_van

    def qsize(self):
        """Return the approximate size of the queue."""
        return self.__db.llen(self.key)

    def empty(self):
        """Return True if the queue is empty, False otherwise."""
        return self.qsize() == 0

    def put_Q(self, item):
        """Put item into the queue."""
        encoded = self.encodeFrame(item)
        self.__db.rpush(self.key, encoded)
        if self.qsize() > self.q_size:
            self.__db.lpop(self.key)

    def get_Q(self, timeout=None):
        """Get item from the queue."""
        item = self.__db.blpop(self.key, timeout=timeout)
        if item:
            item = item[1]
        return item

    def resizeFrame(self, frame, resolution=(860, 480)):
        """Resize frame to resolution."""
        return cv2.resize(frame, resolution)

    @staticmethod
    def separate_image_timestamp(image_byte):
        """Separate image timestamp from image bytes."""
        timestamp = ""
        s = False if image_byte is None else True
        if s:
            timestamp = image_byte[:26].decode()
            image_byte = image_byte[26:]
        return timestamp, image_byte, s

    @staticmethod
    def encodeFrame(img):
        """Encode frame to bytes."""
        h, w = img.shape[:2]
        shape = struct.pack(">II", h, w)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")
        img_tobytes = img.tobytes()
        encoded = str(timestamp).encode() + shape + img_tobytes
        return encoded

    @staticmethod
    def decodeFrame(encoded):
        """Decode frame from bytes."""
        h, w = struct.unpack(">II", encoded[:8])
        decoded_image = np.frombuffer(encoded, dtype=np.uint8, offset=8).reshape(
            h, w, 3
        )
        return decoded_image

    def getFrame(self):
        """Get frame from the queue."""
        time_img_bytes = self.get_Q(1)
        timestamp, img_bytes, grabbed = self.separate_image_timestamp(time_img_bytes)

        if grabbed:
            frame = self.decodeFrame(img_bytes)
        else:
            frame = None
        return frame, grabbed, timestamp
