import time


"""
sleep elapsed time based on fps
"""


def sleep_fps(start, fpsTime):
    curTime = time.time()
    elapsed = curTime - start
    # Try to keep FPS for files consistent otherwise frameBufMax will be reached
    if elapsed < fpsTime:
        time.sleep(fpsTime - elapsed)
