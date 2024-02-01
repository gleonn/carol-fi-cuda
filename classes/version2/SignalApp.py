import time
from classes.Logging import Logging
from threading import Thread
from random import uniform

import common_parameters as cp  # All common parameters will bet at common_parameters module
import os
import sys
import signal
"""
Signal the app to stop so GDB can execute the script to flip a value
"""


class SignalApp(Thread):
    def __init__(self, signal_cmd, max_wait_time, log_path, unique_id, signals_to_send, init_sleep):
        super(SignalApp, self).__init__()
        self.__signal_cmd = signal_cmd
        self.__noterminado = True
        os.system("rm -f {}".format(log_path))
        self.__log = Logging(log_file=log_path, unique_id=unique_id)

        # Most of the benchmarks we cannot wait until the end of the processing
        # Considering most of 90% of the time
        self.__init_wait_time = uniform(init_sleep, max_wait_time * cp.MAX_SIGNAL_BEFORE_ENDING)
        self.__signals_to_send = signals_to_send
        self.__time_to_sleep = (max_wait_time - self.__init_wait_time) / self.__signals_to_send
    def receiveSignal(signalNumber, frame):
        print ("Alcanzado el breakpoint, y recevida la señal",signalNumber);
        os.system("{} > /dev/null 2>/dev/null".format(self.__signal_cmd))
        self.__log.info(log_string)
        for signals in range(0, self.__signals_to_send):
            os.system("{} > /dev/null 2>/dev/null".format(self.__signal_cmd))
            self.__log.info("sending signal {}".format(signals))
            time.sleep(self.__time_to_sleep)
        self.__noterminado=False  
        return
    def run(self):
        # Send a series of signal to make sure gdb will flip a value in one of the interrupt signals
        log_string = "Sending a signal using command: {} after {}s.".format(self.__signal_cmd, self.__init_wait_time)

        if cp.DEBUG:
            print(log_string)
        print ("Esperando breakpoint.....")
        signal.signal(signal.SIGINT,self.receiveSignal);
        # Sleep for a random time
#        time.sleep(self.__init_wait_time)
        while self__noterminado:
          printf("Waiting....")
          time.sleep(3)
        printf ("Terminado")


    def get_int_wait_time(self):
        return self.__init_wait_time