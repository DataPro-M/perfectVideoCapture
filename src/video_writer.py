"""
Created on Apr 12, 2017
@author: sgoldsmith
Copyright (c) Steven P. Goldsmith
All rights reserved.
"""

import numpy
import ffmpeg
import threading
import os


class ffmpegwriter():
    """Video writer based on ffmpeg-python.
    
    Encode single numpy image as video frame.
    """
    
    def __init__(self, fileName, vcodec, fps, frameWidth, frameHeight):
        self.process = (
            ffmpeg
            .input('pipe:', framerate='{}'.format(fps), format='rawvideo', pix_fmt='bgr24', s='{}x{}'.format(frameWidth, frameHeight))
            .output(fileName, vcodec=vcodec, pix_fmt='nv21', acodec='n', **{'b:v': 2000000})
            .global_args('-hide_banner', '-nostats', '-loglevel', 'panic')            
            .overwrite_output()
            .run_async(pipe_stdin=True)
        )
       
    
    def write(self, image):
        """ Convert raw image format to something ffmpeg understands """
        self.process.stdin.write(
            image
            .astype(numpy.uint8)
            .tobytes()
        )        
   
    def close(self):
        """Clean up resources"""
        self.process.stdin.close()
        self.process.wait()

class video_writer():
    """Video writer class."""
    def __init__(self, config):       
        self.config         = config
        self.fps            = int(self.config['record']['fps_rec'])
        self.frameWidth     = int(config['defaultArgs']['--width'])
        self.frameHeight    = int(config['defaultArgs']['--height']) 
        self.recDir         = config['record']['recordDir']
        self.cam_name       = config['APP']['cam_name']
        self.file_ext       = config['record']['recordFileExt']
        self.vcodec         = config['record']['vcodec']
        self.videoFileName  = None
        self.writerInstance = None


    def makeFileName(self, timestamp, name):
        "Create file name based on image timestamp"

        # Construct directory name from camera name, recordDir and date
        dateStr = timestamp.strftime("%Y-%m-%d")
        fileDir = "%s/%s/%s" % (os.path.expanduser(self.recDir), 
                                self.cam_name, 
                                dateStr)

        # Create dir if it doesn"t exist
        if not os.path.exists(fileDir):
            os.makedirs(fileDir)

        # Construct file name from camera name, timestamp and file extension
        fileName = "%s-%s.%s" % (name, 
                                timestamp.strftime("%H-%M-%S"), 
                                self.file_ext)
        return "%s/%s" % (fileDir, fileName)

    def recordingStart(self, timestamp, name):
        "Start recording video"
        
        # Create file name
        self.videoFileName = self.makeFileName(timestamp, name)

        # Create video writer
        self.writerInstance = ffmpegwriter(fileName=self.videoFileName, 
                                vcodec=self.vcodec, 
                                fps=self.fps, 
                                frameWidth=self.frameWidth, 
                                frameHeight=self.frameHeight)

        # Start recording
        thread = threading.Thread(target=self.writeFrames)
        thread.start()