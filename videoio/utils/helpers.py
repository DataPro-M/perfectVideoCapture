"""VideoIO helper functions."""

import os
import time

import redis  # type: ignore
from redis.client import Redis  # type: ignore


def write_pid_file(pid_file: str) -> None:
    """Write the pid file."""
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))


def connect_redis(redis_host: str, redis_port: int) -> Redis:
    """Connect to redis server."""
    return redis.Redis(host=redis_host, port=redis_port, db=0)


def sleep_fps(start: float, fpsTime: float) -> None:
    """Sleep elapsed time based on fps."""
    curTime = time.time()
    elapsed = curTime - start
    # Try to keep FPS for files consistent otherwise frameBufMax will be reached
    if elapsed < fpsTime:
        time.sleep(fpsTime - elapsed)
