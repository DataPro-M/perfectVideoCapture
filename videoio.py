"""
Usage:
  videoio.py [--src=<RTSP-url or file-path>] 
             [--width=<pixel>] [--height=<pixel>] 
             [--fps_rdg=<int reading-frames-fps>]
             [--verbose=<verbose mode>] 
  videoio.py -h | --help | --version

"""
from docopt import docopt
import time
import socket
import sys
import os
import datetime
import threading
import cv2
import numpy as np
import src.helpers_vio as hvio
import src.utils as utils 
from src.fps import FPS
from docs import config as cfg
from src.redis_shmem import RedisShmem
from src.video_writer import video_writer
import faulthandler

# ==================================
faulthandler.enable()
config_path = os.path.dirname(os.path.abspath(cfg.__file__))

# RedisVideoCapture class
class RedisVideoCapture:
    def __init__(self, cfg):
        if int(cfg['defaultArgs']['--verbose']) == 1:
            print('\n[INFO] Initializing VideoCapture context') 
        self.src                  = cfg['defaultArgs']['--src']
        self.stream               = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
        self.shmem                = RedisShmem(cfg)
        self.verbose              = int(cfg['defaultArgs']['--verbose'])        
        self.writer               = video_writer(cfg)
        self.rec_permit           = cfg['record']['rec_permit']                      
        self.fps_rdg              = int(cfg['defaultArgs']['--fps_rdg'])
        self.fpsTime_rdg          = 1 / float(self.fps_rdg) if self.fps_rdg != 0 else 0
        self.fps_van              = int(cfg['Analysis']['fps_van']) if int(cfg['Analysis']['fps_van']) != 0 else 12
        self.fpsTime_van          = 1 / float(self.fps_van) if self.fps_van != 0 else 0
        self.resolution           = int(cfg['defaultArgs']['--width']), int(cfg['defaultArgs']['--height'])                
        self.frame_fail_cnt       = 0
        self.frame_fail_cnt_limit = 10     
        self.capture_failed       = False
        self.thread               = None
        self.started              = False                       
        self.grabbed, self.frame  = False, None
        
        
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

    def start(self): 
        if self.verbose == 2:
            print('[INFO] Starting threaded video capturing')       
        self.started = True        
        # start the thread to read frames from the video stream         
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = False # thread will stop when main thread stops
        self.thread.start()
        return self

    def waitOnFrameBuf(self):
        """Wait until the frame buffer is full """
        while(not self.capture_failed and (self.shmem.qsize() < self.shmem.q_size)):
            # 1/4 of FPS sleep
            time.sleep(1.0 / (self.fps_van * 4)) if self.fps_van != 0 else time.sleep(0.1)
        

    def update(self):
        # start the FPS timer         
        fps_log = FPS().start()

        # loop over some frames and estimate the FPS
        while self.started:			

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

                if not self.capture_failed:
                    self.capture_failed = False  

            # If we failed to grab a frame, increment the counter.
            else: 
                self.frame_fail_cnt += 1
                if self.frame_fail_cnt > self.frame_fail_cnt_limit:
                    self.frame_fail_cnt = 0
                    self.capture_failed = True

                    if self.verbose == 2:
                        print('[INFO] Capture failed, exiting') 
                    break          
                        
            # Try to keep FPS consistent
            if self.fps_rdg != 0:
                hvio.sleep_fps(tic, self.fpsTime_rdg)

            # update FPS counter
            fps_log.update() 

            if self.verbose == 1 and self.frame is not None:
                print("[INFO] approx. stream reader  FPS: {:.2f}".format(fps_log.fps()))
        # end while

        # stop the FPS timer 
        fps_log.stop()
                
    # get the frame from the buffer
    def read(self):        
        return self.shmem.getFrame()          

    def stop(self):
        # indicate that the thread should be stopped
        if self.verbose == 2:
            print('[INFO] Stopping threaded video capturing') 
        self.started = False        
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

        # # write the pid file
        # pid_path = config['process']['pidfilepath'] + config['process']['pidfilename'] + '.pid'
        # utils.write_pid_file(pid_path)

        # set variables
        import itertools
        c = itertools.count(0)
        frameID = next(c)
        stop_bit = True
        rec_event = False        

        # start the service
        if verbose == 2:
            print('[INFO] Starting service')       
        
        while stop_bit: 
            
            # initialize the video capture and start the thread 
            cap = RedisVideoCapture(config)                  
            cap.start()

            # start the FPS logger
            fps_log = FPS().start()
            
            # start the video reader main loop
            while cap.stream.isOpened(): 
                tic = time.time()

                if cap.capture_failed:
                    break

                # get the frame from the buffer                
                frame, grabbed, timestamp = cap.read()  

                # Wait until the frame buffer is full 
                cap.waitOnFrameBuf()

                if grabbed:
                    frameID = next(c) # increment frame ID
                    if verbose == 2:
                        print(f'{frameID}-th frame grabbed @ {timestamp} and Q_size: {cap.shmem.qsize()}')

                # if permited to record
                if cap.rec_permit:
                    # fill the buffer of the video writer 
                    cap.writer.update(frame)

                    # if we are not recording, start recording
                    if not cap.writer.recStarted and rec_event:                        
                        now = datetime.datetime.now()
                        cap.writer.recStart(now, 'test_rec')

                    # if we are recording, stop recording
                    elif cap.writer.recStarted and not rec_event:
                        cap.writer.recStop() 

                # Try to keep FPS consistent
                if cap.fps_van != 0:
                    hvio.sleep_fps(tic, cap.fpsTime_van)

                # update the FPS logger
                fps_log.update()
                if verbose == 1:
                    print("[INFO] approx. video analitic FPS: {:.2f}".format(fps_log.fps()))

                # Some dummy conditions!
                ## recording event
                if frameID in range(100, 200):
                    if not rec_event:
                        rec_event = True

                ## recording event finished
                elif rec_event and frameID > 200:
                    rec_event = False

                ## Loop exiting condition         
                elif frameID >= 300:                    
                    stop_bit = False
                    break
            # end while

            # stop the services
            cap.writer.recStop()
            cap.stop()
            fps_log.stop()            
            time.sleep(1)
            cap = None
            

        print("[INFO] Exiting service")      
        time.sleep(3)
        print('By')

    except:
        print("Process already running. Exiting")
        time.sleep(1)
        sys.exit(0)


if __name__ == '__main__':
    main()