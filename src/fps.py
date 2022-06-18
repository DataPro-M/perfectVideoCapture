"""Compute the frames per second of a video."""

import datetime


class FPS:
    """FPS class."""

    def __init__(self) -> None:
        """Initialize the FPS context."""
        # store the start time, end time, and total number of frames
        # that were examined between the start and end intervals
        self._start = datetime.datetime.now()
        self._end = datetime.datetime.now()
        self._numFrames = 0

    def start(self) -> None:
        """Start the timer."""
        self._start = datetime.datetime.now()

    def stop(self) -> None:
        """Stop the timer."""
        self._end = datetime.datetime.now()

    def update(self) -> None:
        """Update the FPS counter."""
        # increment the total number of frames examined during the
        # start and end intervals
        self._numFrames += 1

    def elapsed(self) -> int:
        """Return the total number of seconds between the start and end."""
        return int((datetime.datetime.now() - self._start).total_seconds())

    def fps(self) -> float:
        """Compute the (approximate) frames per second."""
        return self._numFrames / self.elapsed()
