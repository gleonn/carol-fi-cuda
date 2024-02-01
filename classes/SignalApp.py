import time
from classes.Logging import Logging
from threading  import Thread
from random import uniform

import common_parameters as cp  # All common parameters will bet at common_parameters module
import os,signal
import sys

"""
Signal the app to stop so GDB can execute the script to flip a value
"""


class SignalApp(Thread):
    def __init__(self,file_connection, max_wait_time, log_path, unique_id, signals_to_send, init_sleep, syncro,waitfinish):
        global crashsystem,hang
        hang=False
        super(SignalApp, self).__init__()
        self.__file_connection = file_connection
        os.system("rm -f {}".format(log_path))
        self.__log = Logging(log_file=log_path, unique_id=unique_id)

        # Most of the benchmarks we cannot wait until the end of the processing
        # Considering most of 90% of the time
        #self.__init_wait_time = uniform(init_sleep, max_wait_time * cp.MAX_SIGNAL_BEFORE_ENDING)
        self.__init_wait_time = uniform(0, max_wait_time * cp.MAX_SIGNAL_BEFORE_ENDING)
        self.__signals_to_send = signals_to_send
        self.__time_to_sleep = (max_wait_time - self.__init_wait_time) / self.__signals_to_send
       # self.__time_to_sleep = (max_wait_time) / self.__signals_to_send
        self._syncro=syncro
        self._waitfinish=waitfinish
    def run(self):
        # Send a series of signal to make sure gdb will flip a value in one of the interrupt signals
        #log_string = "Sending a signal using command: {} after {}s and each {}s.".format(self.__signal_cmd, self.__init_wait_time,self.__time_to_sleep)
        log_string = "Sending a signal  each {}s of {} times.".format(self.__time_to_sleep,self.__signals_to_send )
        if cp.DEBUG:
            self.__log.info(log_string)
        crashsystem=False
        try:
           (self._syncro).wait()
        #except threading.BrokenBarrierError:
        except:	
          (self._syncro).abort()
          self.__log.info("Breakpoint inicial fuera de tiempo")
          #(self._waitfinish).wait()
          (self._syncro).reset()   
          crashsystem=True
          return 
          #self.__log.info("Timeout syncron of breakpoint\n")
           
        pidf=open(self.__file_connection,"r")
        pid=int(pidf.read())
        pidf.close()
        
        time.sleep(self.__init_wait_time)	
        self.__log.info("Begin injection")   
        crash=False
        for signals in range(0, self.__signals_to_send):
            #os.system("{} > /dev/null 2>/dev/null".format(self.__signal_cmd))
            try:
              os.kill(pid,signal.SIGINT)
              self.__log.info("sending signal {}".format(signals))
            except:
              self.__log.info("Crash? o DeadLock")  
          
              print ("Voy por aqui")    
              (self._waitfinish).abort()
              (self._waitfinish).reset()
              (self._syncro).abort()
              (self._syncro).reset()  
              try:
                os.kill(pid,signal.SIGKILL)
              except:
                 self.__log.info("Process is dead")     
              crash=True
              break
            
#            try:
#               (self._syncro).wait()
#            except:	
#               (self._syncro).abort()
               #break
#            (self._syncro).reset()   
            time.sleep(self.__time_to_sleep)
        #(self._syncro).reset() 
        if not crash:
         try:
           (self._waitfinish).wait()
          #except  threading.BrokenBarrierError:
         except:	
           (self._waitfinish).abort()
           self.__log.info("Hang timeout execution")
           hang=True
           self.__log.info("Timeout execution programa")  
        else:
           print ("He salido por aqui")    
        (self._waitfinish).reset()

    def ishang (self):
        return hang
    def get_int_wait_time(self):
        return self.__init_wait_time
