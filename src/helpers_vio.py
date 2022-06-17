"""VideoIO helper functions."""

import time


def sleep_fps(start, fpsTime):
    """Sleep elapsed time based on fps."""
    curTime = time.time()
    elapsed = curTime - start
    # Try to keep FPS for files consistent otherwise frameBufMax will be reached
    if elapsed < fpsTime:
        time.sleep(fpsTime - elapsed)
