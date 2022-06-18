"""Utility functions for the application."""

import os

import redis  # type: ignore
from redis.client import Redis  # type: ignore


def write_pid_file(pid_file: str):
    """Write the pid file."""
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))


def connect_redis(redis_host: str, redis_port: int) -> Redis:
    """Connect to redis server."""
    return redis.Redis(host=redis_host, port=redis_port, db=0)
