"""Utility functions for the application."""

import os

import redis


def write_pid_file(pid_file):
    """Write the pid file."""
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))


def connect_redis(redis_host, redis_port):
    """Connect to redis server."""
    return redis.Redis(host=redis_host, port=redis_port, db=0)
