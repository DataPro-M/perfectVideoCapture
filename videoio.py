"""
Usage:
  config.py [--file=<file_path-path>] [--width=<pixel>] 
            [--height=<pixel>] [--fps=<int-fps>]
            [--stream_name=<stream-name>] [--service_name=<service-name>] 
  config.py -h | --help | --version

"""
from docopt import docopt
import time
import socket
import sys
import os
import threading
import cv2
import numpy as np
import src.helpers_vio as hvio
import src.utils as utils 
from src.fps import FPS
from docs import config as cfg
from src.redis_shmem import RedisShmem

config_path = os.path.dirname(os.path.abspath(cfg.__file__))


class RedisVideoCapture:
    def __init__(self, config):
        print('\n[*] Initializing VideoCapture context') if int(config['defaultArgs']['--verbose']) == 2 else None
        self.config               = config        
        self.src                  = config['defaultArgs']['--src']
        self.stream               = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
        self.stopped              = False                       
        self.grabbed, self.frame  = False, None              
        self.fps                  = int(config['defaultArgs']['--fps'])
        self.resolution           = int(config['defaultArgs']['--width']), int(config['defaultArgs']['--height'])
        self.fpsTime              = 1 / float(self.fps) if self.fps != 0 else 0        
        self.frame_fail_cnt       = 0
        self.frame_fail_cnt_limit = 10     
        self.capture_failed       = False
        self.thread               = None
        self.shmem                = RedisShmem(config)
        self.verbose              = int(config['defaultArgs']['--verbose'])
        
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def start(self): 
        if self.verbose == 2:
            print('[*] Starting threaded video capturing')       
        self.stopped = False        
        # start the thread to read frames from the video stream         
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.start()
        return self


    def update(self):          
        fps_log = FPS().start()
        while not self.stopped:			

            tic = time.time()  

            # Get frame from the video source
            self.grabbed, frame = self.stream.read()
            
            # If we have successfully grabbed a frame.
            if self.grabbed: 

                # resize frame to resolution
                self.frame = self.shmem.resizeFrame(frame, self.resolution) 

                # put frame into buffer                
                self.shmem.put_Q(self.frame)                

                if self.frame_fail_cnt > 0:
                    self.frame_fail_cnt = 0 # reset counter

                if self.capture_failed == False:
                    self.capture_failed = True  

            # If we failed to grab a frame, increment the counter.
            else: 
                self.frame_fail_cnt += 1
                if self.frame_fail_cnt > self.frame_fail_cnt_limit:
                    self.frame_fail_cnt = 0
                    self.capture_failed = True

                    if self.verbose == 2:
                        print('[*] Capture failed, exiting') 
                    break          
                        
            # Try to keep FPS consistent
            hvio.sleep_fps(tic, self.fpsTime) if self.fpsTime != 0 else 0
            fps_log.update() 
            if self.verbose == 1 and self.frame is not None:
                print("[INFO] approx. stream reader  FPS: {:.2f}".format(fps_log.fps()))
        # end while

        # release the video source
        self.stream.release()
        fps_log.stop()
                
    # get the frame from the buffer
    def read(self):        
        return self.shmem.getFrame()          

    def stop(self):
        # indicate that the thread should be stopped
        if self.verbose == 2:
            print('[*] Stopping threaded video capturing') 
        self.stopped = True        
        self.stream.release()
        self.thread.join() 

# ==================================
## main function
# ==================================
def main():
    arguments = docopt(__doc__, version='0.1.1rc')

    # read the config file
    initfile = os.path.join(config_path, 'config.ini')
    config, default_args = cfg.read_ini(initfile)

    # merge the arguments with the config file
    args = cfg.merge(arguments, default_args)    
    verbose = int(args.verbose)

    try:

        # make the module unique to run on the same machine
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind('\0' + config['process']['processname'])

        # write the pid file
        pid_path = config['process']['pidfilepath'] + config['process']['pidfilename'] + '.pid'
        utils.write_pid_file(pid_path)

        # start the service
        if verbose == 2:
            print('[*] Starting service')
    
        import itertools
        c = itertools.count(0)
        frameID = next(c)
        
        stop_bit = True
        
        fps_van = config['stream']['fps_van']
        fpsTime = 1 / float(fps_van) if fps_van != 0 else 0        

        while stop_bit: 
            
            # initialize the video capture and start the thread 
            capture = RedisVideoCapture(config)                  
            capture.start()

            # start the FPS logger
            fps_log = FPS().start()
            
            while capture.stream.isOpened(): 
                tic = time.time()
                # get the frame from the buffer                
                _, grabbed, timestamp = capture.read()
                if grabbed == True:
                    frameID = next(c)
                    if verbose == 2:
                        print(f'{frameID}-th frame grabbed @ {timestamp} and Q_size: {capture.shmem.qsize()}')

                if frameID >= 2000:
                    capture.stop()
                    stop_bit = False
                    break

                # Try to keep FPS consistent
                hvio.sleep_fps(tic, fpsTime)

                # update the FPS logger
                fps_log.update()
                if verbose == 1:
                    print("[INFO] approx. video analitic FPS: {:.2f}".format(fps_log.fps()))

            # end while

            # stop the services
            capture.stop()
            fps_log.stop()
            time.sleep(1)
            capture = None
            

        print("[*] Exiting service")      
        time.sleep(3)
        print('By')

    except:
        print("Process already running. Exiting")
        time.sleep(1)
        sys.exit(0)

if __name__ == '__main__':
    main()

  