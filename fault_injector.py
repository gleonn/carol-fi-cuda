#!/usr/bin/env python3

import argparse
import os
import random
import re
import shutil
import time
import datetime
import signal
import common_functions as cf  # All common functions will be at common_functions module
import common_parameters as cp  # All common parameters will be at common_parameters module
import sys
import signal
import threading
from threading import Thread, Lock
from classes.RunGDB import RunGDB
from classes.SummaryFile import SummaryFile
from classes.Logging import Logging
from classes.SignalApp import SignalApp

"""
[THIS FUNCTION CAN BE EDITED IF DESIRED]
User defined function
this function must return an empty or not string.
The string will be appended in the last collum of summary CSV file
the column will have  'user_defined' as header
if the string is always empty the column will be empty, otherwise it
will contain the returned values for each injection
"""
def receiveSignal(signalNumber, frame):
        global logging
        logging.info("Esperando sincronismo del final")
        try:
          syncro.wait()
        except:	
          syncro.abort()
          logging.info("Breakpoint inicial fuera de tiempo")
        logging.info("Alcanzado el breakpoint, y recibida la señal {}".format(signalNumber));
def receiveEnd(signalNumber, frame):
        global logging
        logging.info("Esperando sincronismo del final")
        try:
          wait_finish.wait()
        except:	
          wait_finish.abort()
          logging.info("Hang timeout execution")
        logging.info("Recibida la señal de final del programa {}".format(signalNumber));
       
def user_defined_function(injection_output_path):
    # This is a temporary example for carol-fi-codes suite
    # it will search for a LOGFILENAME int the benchmark output if it finds
    # then the desired pattern will be returned
    with open(injection_output_path, "r") as fp:
        for l in fp.readlines():
            m = re.match(r"LOGFILENAME:.*/(\S+).*", l)
            if m:
                return m.group(1)
    return ""


"""
CTRL + C event
"""


def signal_handler(sig, frame):
    global kill_strings, exit_injector
    exit_injector = True

    for cmd in kill_strings.split(";"):
        os.system(cmd + " > /dev/null 2>&1")
 
    os.system("rm -f {}/bin/*".format(current_path))
    print("Current_path "+current_path)
    for th in gpus_threads:
      th.join()
    sys.exit(0)


"""
Check if app stops execution (otherwise kill it after a time)
"""


def check_finish(max_wait_time, logging, timestamp_start, process, thread, kill_string):
    is_hang = False

    # Wait maxWaitTimes the normal duration of the program before killing it
    # max_wait_time = int(conf.get(section, "maxWaitTimes")) * end_time
    sleep_time = max_wait_time / cp.NUM_DIVISION_TIMES
    if cp.DEBUG:
        cf.printf("THREAD: {} MAX_WAIT_TIME {} CHECK FINISH SLEEP_TIME {}".format(thread, max_wait_time, sleep_time))

    # Watchdog to avoid hangs
    p_is_alive = process.is_alive()
    now = int(time.time())
    diff_time = now - timestamp_start
    while diff_time < max_wait_time and p_is_alive:
        time.sleep(sleep_time)
        p_is_alive = process.is_alive()
        now = int(time.time())
        diff_time = now - timestamp_start

    # Process finished ok
    if not p_is_alive:
        logging.debug("PROCESS NOT RUNNING")
        if cp.DEBUG:
            cf.printf("THREAD {} PROCESS NOT RUNNING".format(thread))

    # check execution finished before or after waitTime
    if diff_time < max_wait_time:
        logging.info("Execution on thread {} finished before waitTime. {} seconds.".format(thread, diff_time))
    else:
        logging.info("Execution on thread {} finished after waitTime. {} seconds.".format(thread, diff_time))
        is_hang = True

    logging.debug("now: {}".format(now))
    logging.debug("timestampStart: {}".format(timestamp_start))

    # Kill all the processes to make sure the machine is clean for another test
    cf.kill_all(kill_string=kill_string, logging=logging)

    # Also kill the subprocess
    process.kill_subprocess()

    return is_hang


"""
Copy the logs and output(if fault not masked) to a selected folder
"""


def save_output(is_sdc, is_hang, is_crash, is_masked, logging, unique_id, flip_log_file, inj_output_path,
                inj_err_path, diff_log_path, diff_err_path, signal_app_log_path, thread):
    # FI successful
    fi_injected = False
    if os.path.isfile(flip_log_file):
        with open(flip_log_file, "r") as fp:
            content = fp.read()
            if re.search('Fault Injection Successful', content):
                fi_injected = True
            fp.close()

    dt = datetime.datetime.fromtimestamp(time.time())
    ymd = dt.strftime('%Y_%m_%d')
    y_m_d_h_m_s = dt.strftime('%Y_%m_%d_%H_%M_%S')
    y_m_d_h_m_s = unique_id + "-" + y_m_d_h_m_s
    dir_d_t = os.path.join(ymd, y_m_d_h_m_s)

    # Log and create the paths
    if not fi_injected:
        cp_dir = os.path.join(cp.LOGS_PATH, 'failed-injection', dir_d_t)
        logging.summary("Fault Injection Failed")
    elif is_hang:
        cp_dir = os.path.join(cp.LOGS_PATH, 'hangs', dir_d_t)
        logging.summary("Hang")
    elif is_crash:
        cp_dir = os.path.join(cp.LOGS_PATH, 'crashs', dir_d_t)
        logging.summary("Crash")    
    elif is_sdc:
        cp_dir = os.path.join(cp.LOGS_PATH, 'sdcs', dir_d_t)
        logging.summary("SDC")
    elif is_masked:
        cp_dir = os.path.join(cp.LOGS_PATH, 'masked', dir_d_t)
        logging.summary("Masked")
    elif not os.path.isfile(inj_output_path):
        cp_dir = os.path.join(cp.LOGS_PATH, 'no_output_generated', dir_d_t)
        logging.summary("no_output_generated")
    else:
        cp_dir = os.path.join(cp.LOGS_PATH, 'unknown', dir_d_t)
        logging.summary("Unknown")

    if not os.path.isdir(cp_dir):
        os.makedirs(cp_dir)

    # Moving all necessary files
    for file_to_move in [flip_log_file, inj_output_path,
                         inj_err_path, diff_log_path, diff_err_path, signal_app_log_path]:
        try:
            shutil.move(file_to_move, cp_dir)
        except Exception as err:
            if cp.DEBUG:
                cf.printf("THREAD {} ERROR ON MOVING {} -- {}".format(thread, file_to_move, str(err)))


"""
Check output files for SDCs
"""


def check_sdcs_and_app_crash(logging, sdc_check_script, inj_output_path, inj_err_path, diff_log_path, diff_err_path):
    is_sdc = False
    is_masked = False
    is_app_crash = [False]
    if not os.path.isfile(inj_output_path):
        logging.error("outputFile not found: " + inj_output_path)
        is_app_crash = True
    elif not os.path.isfile(cp.GOLD_OUTPUT_PATH):
        logging.error("gold_file not found: " + cp.GOLD_OUTPUT_PATH)
        raise ValueError("GOLD FILE NOT FOUND")
    elif not os.path.isfile(sdc_check_script):
        logging.error("sdc check script file not found: " + sdc_check_script)
        raise ValueError("SDC CHECK SCRIPT NOT FOUND: " + sdc_check_script)
    elif not os.path.isfile(inj_err_path):
        logging.error("possible crash, stderr not found: " + inj_output_path)
        is_app_crash[0] = True
    elif not os.path.isfile(cp.GOLD_ERR_PATH):
        logging.error("gold_err_file not found: " + cp.GOLD_ERR_PATH)
        raise ValueError("GOLD ERR FILE NOT FOUND: " + cp.GOLD_ERR_PATH)

    # Removing the output trash info
    # It automatically overwrite the file in the output path
    cf.remove_useless_information_from_output(output_file_path=inj_output_path)
    cf.remove_useless_information_from_output(output_file_path=inj_err_path)

    if os.path.isfile(cp.GOLD_OUTPUT_PATH) and os.path.isfile(inj_output_path) and os.path.isfile(
            cp.GOLD_ERR_PATH) and os.path.isfile(inj_err_path):
        # Set environ variables for sdc_check_script
        os.environ['GOLD_OUTPUT_PATH'] = cp.GOLD_OUTPUT_PATH
        os.environ['INJ_OUTPUT_PATH'] = inj_output_path
        os.environ['GOLD_ERR_PATH'] = cp.GOLD_ERR_PATH
        os.environ['INJ_ERR_PATH'] = inj_err_path
        os.environ['DIFF_LOG'] = diff_log_path
        os.environ['DIFF_ERR_LOG'] = diff_err_path

        compare_script_result = os.system("sh " + sdc_check_script)

        if compare_script_result != 0:
            raise ValueError("SDC/Crash script returned a value different from 0. Cannot proceed")

        # Test if files are ok
        with open(diff_log_path, 'r') as fi:
            out_lines = fi.readlines()
            if len(out_lines) != 0:
               for carol_fi_signal in cp.SIGNALS:
                    for line in out_lines:
                        if carol_fi_signal in line:
                            #print("FAIL=="+line+"====")
                            is_app_crash[0] = True
                            if len (is_app_crash) == 1:
                               is_app_crash.append(carol_fi_signal)
                            else:
                               is_app_crash[1]=is_app_crash[1]+" "+carol_fi_signal   
                            break
               if (not is_app_crash[0]):
                # Check if NVIDIA signals on output
                  is_masked= True
                  for line in out_lines:
                        if 'FAIL' in line:
                            #print("FAIL=="+line+"====")
                            is_sdc= True
                            is_masked=False
                            break
               else:
                 is_sdc= False
                 is_masked=False                 

                        
                #    if is_app_crash[0]:
                #        break
                #if not is_app_crash:
                #    is_sdc = True

       # with open(diff_err_path, 'r') as fi_err:
       #     err_lines = fi_err.readlines()
       #     if len(err_lines) != 0:
       #       is_app_crash[0] = True
       #       if len (is_app_crash) == 1:
       #         is_app_crash.append('Unknown')
    return is_sdc, is_app_crash, is_masked

"""
Check the carolfi-xxxx logfile
the status of the injected fault
"""


def check_injection_outcome(host_thread, logging, injection_site):
    # Search for set values for register
    # Must be done before save output

    # Check THREAD FOCUS. Check if could change the block and the thread
    register = block = thread = "___"

    # Search for block
    block_focus = logging.search("CUDA_BLOCK_FOCUS")
    if block_focus:
        m = re.search(r"CUDA_BLOCK_FOCUS:.*block[ ]+\((\d+),(\d+),(\d+)\).*", block_focus)
        if m:
            block = "{}_{}_{}".format(m.group(1), m.group(2), m.group(3))
    thread_focus = logging.search("CUDA_THREAD_FOCUS")

    # Search for thread
    if thread_focus:
        m = re.search(r"CUDA_THREAD_FOCUS:.*thread[ ]+\((\d+),(\d+),(\d+)\).*", thread_focus)
        if m:
            thread = "{}_{}_{}".format(m.group(1), m.group(2), m.group(3))
    register_selected = logging.search("SELECTED_REGISTER")

    # Search for the register
    if register_selected:
        m = re.search(r"SELECTED_REGISTER:(\S+).*", register_selected)
        if m:
            register = m.group(1)

    # Was the fault injected?
    try:
        old_value = re.findall(r'old_value:(\S+)', logging.search("old_value"))[0]
        new_value = re.findall(r'new_value:(\S+)', logging.search("new_value"))[0]
        fi_successful = True
        # Check specific outcomes
        # No need to process for RF
        instruction = 'register'
        assm_line = logging.search("ASSM_LINE")
        
        dpc={}
        dpc['absoluto']="0x"+re.match(r".*0x([0-9a-fA-F]+) <.*",assm_line).group(1)
        dpc['relativo']=assm_line.split('<')[1].split('>')[0]
        #print("---PC: "+dpc['absoluto']+ "PC rel"+dpc['relativo'])
        pc=dpc['absoluto']+"<"+dpc['relativo']+">"
        if cp.INJECTION_SITES[injection_site] in [cp.INST_OUT, cp.INST_OUT_ORI,cp.INST_OUT_V1,cp.INST_OUT_V2,cp.INST_ADD]:
            # if fault was injected ASSM_LINE MUST be in the logfile          
            instruction = re.match(r".*:\t(\S+) .*", assm_line).group(1)
           

    except TypeError as te:
        instruction = new_value = old_value = None
        pc = instruction 
        fi_successful = False
        if cp.DEBUG:
            cf.printf("THREAD {} FAULT WAS NOT INJECTED. ERROR {}".format(host_thread, te))

    return block, fi_successful, new_value, old_value, register, thread, instruction, pc
"""
Function to run one execution of the fault injector
return old register value, new register value
"""


def gdb_inject_fault(**kwargs):
    global kill_strings, logging
    # These are the mandatory parameters
    bits_to_flip = kwargs.get('bits_to_flip')
    fault_model = kwargs.get('fault_model')
    unique_id = kwargs.get('unique_id')
    max_time = kwargs.get('max_time')
    end_time = kwargs.get('end_time')
    current_path_local = kwargs.get('current_path')

    # injection site
    injection_site = kwargs.get('injection_site')
    benchmark_args = kwargs.get('benchmark_args')
    benchmark_binary = kwargs.get('benchmark_binary')
    host_thread = kwargs.get('host_thread')
    seq_signals = kwargs.get('seq_signals')
    init_sleep = kwargs.get('init_sleep')
    sdc_check_script = kwargs.get('gold_check_script')
    maxregs=kwargs.get('max_regs')

    # signalCmd
    signal_cmd = kwargs.get("signal_cmd")
    gdb_exec_name = kwargs.get('gdb_path')
    gdb_kernel = kwargs.get('kernel')

    # Define all path to current thread execution
    # Logging file
    flip_log_file = cp.LOG_DEFAULT_NAME.format(unique_id)
    inj_output_path = cp.INJ_OUTPUT_PATH.format(unique_id)
    inj_err_path = cp.INJ_ERR_PATH.format(unique_id)
    signal_app_log = cp.SIGNAL_APP_LOG.format(unique_id)
    diff_log_path = cp.DIFF_LOG.format(unique_id)
    diff_err_path = cp.DIFF_ERR_LOG.format(unique_id)

    # Starting FI process
    if cp.DEBUG:
        cf.printf("THREAD {} STARTING GDB SCRIPT".format(host_thread))

    logging = Logging(log_file=flip_log_file, unique_id=unique_id)
    logging.info("Starting GDB script")


    #init_wait_time = uniform(0, end_time * cp.MAX_SIGNAL_BEFORE_ENDING)
    #time_to_sleep = (max_wait_time - self.__init_wait_time) / seq_signals
    # Generate configuration file for specific test
    gdb_env_string = "  {}|{}|{}|{}|{}|{}|{}|file {}; set args {}|{}".format(gdb_kernel,os.getpid(),maxregs,cp.FILE_PID_PIF,",".join(str(i) for i in bits_to_flip), fault_model, flip_log_file, benchmark_binary, benchmark_args, injection_site)
               

                                                              

    if cp.DEBUG:
        cf.printf("THREAD {} ENV GENERATE FINISHED".format(host_thread))

    # First we have to start the SignalApp thread
    signal_app_thread = SignalApp(max_wait_time=end_time, file_connection=cp.FILE_PID_PIF,
                                  log_path=signal_app_log, unique_id=unique_id,
                                  signals_to_send=seq_signals,
                                  init_sleep=init_sleep,syncro=syncro,waitfinish=wait_finish)

    # Create one thread to start gdb script
    # Start fault injection process
    fi_process = RunGDB(unique_id=unique_id, gdb_exec_name=gdb_exec_name, flip_script=cp.FLIP_SCRIPT,
                        carol_fi_base_path=current_path_local, gdb_env_string=gdb_env_string,
                        gpu_to_execute=host_thread,
                        inj_output_path=inj_output_path, inj_err_path=inj_err_path)

    if cp.DEBUG:
        cf.printf("THREAD {} STARTING PROCESS".format(host_thread))

    # Starting both threads
   
    fi_process.start()
    #if cp.DEBUG:
    #   cf.printf( "Waiting breakpoint.....")

    signal_app_thread.start()
  

    if cp.DEBUG:
        cf.printf("THREAD {} PROCESSES SPAWNED".format(host_thread))


    signal_app_thread.join(timeout=300)
    cf.printf("THREAD {} PROCESS JOINED".format(signal_app_thread))
    # Start counting time
    timestamp_start = int(time.time())

    # Check if app stops execution (otherwise kill it after a time)
    # max_wait_time, logging, timestamp_start, thread, kill_string
  
    is_hang = check_finish(max_wait_time=max_time, logging=logging, timestamp_start=timestamp_start,
                           process=fi_process, thread=host_thread,
                           kill_string=kill_strings) #init_hang=signal_app_thread.ishang)
    if cp.DEBUG:
        cf.printf("THREAD {} FINISH CHECK OK".format(host_thread))

    # finishing and removing thrash
    fi_process.join(timeout=300)
    # fi_process.terminate()
    cf.printf("THREAD {} PROCESS JOINED".format(fi_process))

    # Get the signal init wait time before destroy the thread
    signal_init_wait_time = signal_app_thread.get_int_wait_time()
    print(1)
    del fi_process, signal_app_thread
    print(2)
    if cp.DEBUG:
        cf.printf("THREAD {} PROCESS JOINED".format(host_thread))

    # Change the behavior of this function if any other information
    # needs to be added in the final summary
    user_defined_string = user_defined_function(injection_output_path=inj_output_path)

    # # Check output files for SDCs
    is_sdc, is_crash, is_masked = check_sdcs_and_app_crash(logging=logging, sdc_check_script=sdc_check_script,
                                                inj_output_path=inj_output_path, inj_err_path=inj_err_path,
                                                diff_log_path=diff_log_path, diff_err_path=diff_err_path)
    if cp.DEBUG:
        cf.printf("THREAD {} CHECK SDCs OK".format(host_thread))

    # Check if the carolfi logfile contains the information
    # to confirm the fault injection outcome
    block, fi_successful, new_value, old_value, register, thread, instruction,pc = check_injection_outcome(
        host_thread=host_thread,
        logging=logging,
        injection_site=injection_site
    )

    # Copy output files to a folder
    save_output(is_sdc=is_sdc, is_hang=is_hang,is_crash=is_crash[0],is_masked=is_masked, logging=logging, unique_id=unique_id,
                flip_log_file=flip_log_file, inj_output_path=inj_output_path, inj_err_path=inj_err_path,
                diff_log_path=diff_log_path, diff_err_path=diff_err_path, signal_app_log_path=signal_app_log,
                thread=host_thread)

    if cp.DEBUG:
        cf.printf("THREAD {} SAVE OUTPUT AND RETURN".format(host_thread))

    return_list = [register, old_value, new_value, fi_successful,
                   is_hang, is_crash, is_sdc, is_masked, signal_init_wait_time, block, thread, instruction, pc, user_defined_string]
    return return_list


"""
This function will select the bits that will be flipped
if it is least significant bits it will reduce the starting bit range
"""


def bit_flip_selection(fault_model):
    # Randomly select (a) bit(s) to flip
    # Max double bit flip
    max_size_register_fault_model = cp.SINGLE_MAX_SIZE_REGISTER
    # Max size of bits to flip is 2, max double bit flip
    bits_to_flip = [0]

    # Single bit flip
    if fault_model == cp.FLIP_SINGLE_BIT:
        bits_to_flip[0] = random.randint(0, max_size_register_fault_model - 1)

    # Double bit flip
    elif fault_model == cp.FLIP_TWO_BITS:
        bits_to_flip = [0] * 2
        bits_to_flip[0] = random.randint(0, max_size_register_fault_model - 1)
        # Make sure that the same bit is not going to be selected
        r = [i for i in range(0, bits_to_flip[0])]
        r += [i for i in range(bits_to_flip[0] + 1, max_size_register_fault_model)]
        bits_to_flip[1] = random.choice(r)

    # Random value
    elif fault_model == cp.RANDOM_VALUE:
        bits_to_flip[0] = str(hex(random.randint(0, cp.MAX_INT_32)))

    # Zero value
    elif fault_model == cp.ZERO_VALUE:
        bits_to_flip[0] = 0

    # Least 16 bits
    elif fault_model == cp.LEAST_16_BITS:
        bits_to_flip[0] = random.randint(0, 15)

    # Least 8 bits
    elif fault_model == cp.LEAST_8_BITS:
        bits_to_flip[0] = random.randint(0, 7)

    return bits_to_flip


"""
print the info for each fault
"""


def pretty_print(header, row):
    fault_injected = row[9]
    normal_print = "\033[0;37;49m"
    failed_print = "\033[1;37;41m"
    injected_print = "\033[1;37;42m"

    output_str = "fault status: "
    output_str += injected_print + "Injected" if fault_injected else failed_print + "Failed"
    output_str += normal_print

    cf.printf(output_str)
    output_str = ""
    for name, value in zip(header, row):
        if name != "fault_successful":
            output_str += "{}: {}\n".format(name, value)

    cf.printf(output_str)
    cf.printf()


"""
This injector has two injection options
this function performs fault injection
by sending a SIGINT signal to the application
"""


def fault_injection_by_signal(**kwargs):
    # Global rows list
    global lock, exit_injector,num_rounds,kill_strings,crashsystem,mode
    benchmark_binary = kwargs.get('benchmark_binary')
    #kwargs['signal_cmd'] = "killall -2 {}".format(os.path.basename(benchmark_binary)) 
    kwargs['signal_cmd'] = "pgrep {}".format(os.path.basename(benchmark_binary)) 
    fault_models = kwargs.get('fault_models')
    iterations = kwargs.get('iterations')
    host_thread = kwargs.get('host_thread')
    injection_site = kwargs.get('injection_site')
    summary_file = kwargs.get('summary_file')
    header = kwargs.get('header')
    max_fallos=5
    acc_fault_injected=0
    cf.printf("-----------------------------------------------------------------------------------------------")
    # Execute the fault injector for each one of the sections(apps) of the configuration file
    for fault_model in fault_models:
        # Execute iterations number of fault injection for a specific app
        print("================")
        num_rounds = 1
        try:
             #print("+++".format(num_rounds))
             ret_profiler = cf.load_config_file("tmpxxx/num_rounds.conf")
             num_rounds=int(ret_profiler.get('DEFAULT', 'Ocurrencias')) 
             #print("++++".format(num_rounds))
             
             os.system ("rm tmpxxx/num_rounds.conf")
        except:     
             print("Error al acceso num_rounds.conf")
        print(num_rounds)
        print("================") 
        while num_rounds <= iterations:
            if exit_injector:
                return

            # Generate an unique id for this fault injection
            # Thread is for multi gpu
            unique_id = "{}_{}_{}".format(num_rounds, fault_model, host_thread)
            bits_to_flip = bit_flip_selection(fault_model=fault_model)
            kwargs['unique_id'] = unique_id
            kwargs['bits_to_flip'] = bits_to_flip
            kwargs['fault_model'] = fault_model

            fi_tic = int(time.time())
            [register, old_val, new_val, fault_injected,
             hang, crash, masked,sdc, signal_init_time, block,
             thread, instruction, pc, user_defined_val] = gdb_inject_fault(**kwargs)

	 	
            # Time toc
            fi_toc = int(time.time())

            # FI injection time
            injection_time = fi_toc - fi_tic
            if len(crash)==1:
                   tmp="--"
            else:
                   tmp=crash[1]   
                   
            row = [unique_id, register, num_rounds, fault_model, thread,
                       block, old_val, new_val, injection_site,
                       fault_injected, hang, crash[0], sdc, masked ,tmp,injection_time,
                       signal_init_time, bits_to_flip, instruction, pc, user_defined_val]
                
            if fault_injected:
               # output_str = "THREAD:{}, FAULT NUM:{}".format(host_thread, num_rounds)

               #output_str += " {}: {},".format(name, value)
		#for name, value in zip(header, row):
                # :-1 to remove the last comma
                #cf.printf(output_str[:-1])
                with lock:
                    summary_file.write_row(row)
                num_rounds += 1
                acc_fault_injeted=0
            else:
                 acc_fault_injected+=1      		    	
                 if (acc_fault_injected == max_fallos):
                   exit_injector=True	
                   for cmd in kill_strings.split(";"):
                        os.system(cmd + " > /dev/null 2>&1")

                   for th in gpus_threads:
                     try:
                       th.join(timeout=300)
                     except:
                        nulo=1        
                   f=open("tmpxxx/num_rounds.conf","w")
                   f.write("[DEFAULT] \nOcurrencias = "+str(num_rounds)+"\n")
                   f.close()                

            pretty_print(header=header, row=row)

    return num_rounds
            
"""
Main function
"""

def main():
    global kill_strings, current_path, gpus_threads, lock, syncro, wait_finish,mode
 
    signal.signal(cp.SIGNAL_STOP,receiveSignal);
    signal.signal(cp.SIGNAL_EXIT,receiveEnd);
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conf', dest="config_file", help='Configuration file', required=True)
    parser.add_argument('-i', '--iter', dest="iterations",
                        help='How many times to repeat the programs in the configuration file', required=True, type=int)

    parser.add_argument('-n', '--n_gpus', dest="n_gpus", help="The number of available GPUs to perform FI."
                                                              " Default is 1.", required=False, default=1, type=int)
                                                              
    parser.add_argument('-d', '--device', dest="device", help="The GPU to perform FI."
                                                              " Default is 0.", required=False, default=0, type=int)

    args = parser.parse_args()
    if args.iterations < 1:
        parser.error('Iterations must be greater than zero')
 

    # Start with a different seed every time to vary the random numbers generated
    # the seed will be the current number of second since 01/01/70
    random.seed()

    # Read the configuration file with data for all the apps that will be executed
    conf = cf.load_config_file(args.config_file)
    benchmark_binary_default = conf.get('DEFAULT', 'benchmarkBinary')
   
    cp.LOGS_PATH="{}l_{}_d{}".format(cp.LOGS_PATH,benchmark_binary_default.split('/')[-1],args.device)    
    cp.rewrite_path()
   
   
    cf.printf(cp.FILE_PID_PIF)
    # Connect signal SIGINT to stop the fault injector
    kill_strings = ""
    signal.signal(signal.SIGINT, signal_handler)

    # First set env vars
    current_path = cf.set_python_env()

    cf.printf("2 - Starting fault injection")
    cf.printf("###################################################")
    cf.printf("2 - {} faults will be injected".format(args.iterations))
    cf.printf("###################################################")
    ########################################################################

    # Creating a summary csv file
    csv_file = conf.get("DEFAULT", "csvFile")

    # Csv log
    fieldnames = ['unique_id', 'register', 'iteration', 'fault_model', 'thread', 'block', 'old_value',
                  'new_value', 'inj_site', 'fault_successful', 'hang', 'crash', 'masked', 'sdc', 'Exception','time',
                  'inj_time_location', 'bits_flipped', 'instruction', 'pc', 'user_defined']
    
    if os.path.exists("tmpxxx/num_rounds.conf"):
      mode='a'
    else:
      mode='w'               
    summary_file = SummaryFile(filename=csv_file, fieldnames=fieldnames, mode=mode) #'w'
    # Lock for summary file parallel
    lock = Lock()

    # Define the number of threads tha will execute
    num_gpus = args.n_gpus
    device=args.device
    iterations = args.iterations
    if args.n_gpus > args.iterations:
        num_gpus = args.iterations

    bin_path = current_path + '/bin'
    if not os.path.exists(bin_path):
        os.mkdir(bin_path)
 
    # Create tmp path and clean it if it exists
    tmp_path = current_path + "/" + cp.LOGS_PATH + "/tmp"
    if not os.path.exists(tmp_path):
        raise FileNotFoundError(tmp_path + " path does not exists, run app_profile.py to create it")

    # Set binaries for the injection
   
    gdb_path_default = conf.get('DEFAULT', 'gdbExecName')

    each_thread_iterations = iterations / num_gpus

    gpus_threads = []
    kernel_info_dict = cf.load_file(cp.KERNEL_INFO_DIR)

    for thread_id in range(0+device, num_gpus+device):
        gdb = "{}/bin/{}_{}".format(current_path, os.path.basename(gdb_path_default), thread_id)
        benchmark_binary = "{}/bin/{}_{}".format(current_path, os.path.basename(benchmark_binary_default), thread_id)

        os.system("ln -s {} {}".format(gdb_path_default, gdb))
        os.system("ln -s {} {}".format(benchmark_binary_default, benchmark_binary))
        # These are the mandatory parameters
        kwargs = {
            'injection_site': conf.get('DEFAULT', 'injectionSite'),
            'fault_models': [int(i) for i in str(conf.get('DEFAULT', 'faultModel')).split(',')],
            'max_time': float(kernel_info_dict['max_time']) * float(conf.get('DEFAULT', 'maxWaitTimes')),
            'end_time': float(kernel_info_dict['max_time_kernel']),
            'max_regs': int(kernel_info_dict['max_regs']),
            'iterations': each_thread_iterations,
            'benchmark_binary': benchmark_binary,
            'benchmark_args': conf.get('DEFAULT', 'benchmarkArgs'),
            'host_thread':thread_id,
            'gdb_path': gdb,
            'current_path': current_path,
            'seq_signals': int(conf.get('DEFAULT', 'seqSignals')),
            'init_sleep': float(conf.get('DEFAULT', 'initSleep')),
            'kernel':conf.get('DEFAULT', 'section_begin'),
            'gold_check_script': "{}/{}".format(current_path, conf.get('DEFAULT', 'goldenCheckScript')),
            'summary_file': summary_file,
            'header': fieldnames
        }
        #syncro = threading.Barrier(2, timeout=5*kwargs.get('max_time') )
        syncro = threading.Barrier(2, timeout=80 )
        wait_finish = threading.Barrier(2, timeout=kwargs.get('max_time')) 
        kill_strings += "killall -9 {};killall -9 {};".format(os.path.basename(benchmark_binary), os.path.basename(gdb))

        fi_master_thread = Thread(target=fault_injection_by_signal, kwargs=kwargs)
        gpus_threads.append(fi_master_thread)
    #ret=0
    for thread in gpus_threads:
        thread.start()

    for thread in gpus_threads:
        thread.join()
        #ret += acc_fault_injected
    
    os.system("rm -f {}/bin/*".format(current_path))
    if exit_injector:
        cf.printf("\nKeyboardInterrupt detected, exiting gracefully!( at least trying :) )")
    else:
        cf.printf("Fault injection finished, results can be found in {}".format(csv_file))
    ########################################################################
    #if (iterations==num_rounds):
    #       sys.exit(0)
    #else:
    #       sys.exit(1)       
    return (iterations==num_rounds)
########################################################################
#                                   Main                               #
########################################################################

kill_strings = None
current_path = None
lock = None
exit_injector = False
gpus_threads = []

if __name__ == "__main__":
    main()
