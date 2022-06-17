"""Compute the frames per second of a video."""

import datetime


class FPS:
    """FPS class."""

    def __init__(self):
        """Initialize the FPS context."""
        # store the start time, end time, and total number of frames
        # that were examined between the start and end intervals
        self._start = None
        self._end = None
        self._numFrames = 0

    def start(self):
        """Start the timer."""
        self._start = datetime.datetime.now()
        return self

    def stop(self):
        """Stop the timer."""
        self._end = datetime.datetime.now()

    def update(self):
        """Update the FPS counter."""
        # increment the total number of frames examined during the
        # start and end intervals
        self._numFrames += 1

    def elapsed(self):
        """Return the total number of seconds between the start and end."""
        return (datetime.datetime.now() - self._start).total_seconds()

    def fps(self):
        """Compute the (approximate) frames per second."""
        return self._numFrames / self.elapsed()
