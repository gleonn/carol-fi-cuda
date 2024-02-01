import os,signal
import gdb
import time
from classes.BitFlip import BitFlip
from classes.Logging import Logging
import common_parameters as cp
import common_functions as cf  # All common functions will be at common_functions module
"""
Handler attached to exit event
"""
def sendsignal (signal):
   os.kill(int(pid),signal)
def exit_handler(event):
    global global_logging
    sendsignal(cp.SIGNAL_EXIT)
    global_logging.info(str("event type: exit"))
  
    try:
        global_logging.info("exit code: {}".format(str(event.exit_code)))
    except Exception as err:
        err_str = "ERROR: {}".format(str(err))
        global_logging.exception(err_str)


"""
Handler that will put a breakpoint on the kernel after
signal
"""




def set_event_normal(event):
    # Accessing global vars
    global global_logging, was_hit, bit_flip,bp,t,primero

    if (isinstance(event, gdb.SignalEvent)):
      gdb.events.stop.disconnect(set_event_normal)
      try:        
        # Just checking if it was hit
         if bit_flip.fault_injected is False:
            bit_flip.single_event()
            global_logging.info("BIT FLIP SET ON SIGNAL {}".format(event.stop_signal))
         #global_logging.info ("Enviado senal a "+ str(pid))
         #sendsignal(cp.SIGNAL_STOP)    
         gdb.events.stop.connect(set_event_normal)
      except Exception as err:
        global_logging.exception("EVENT DIFFERENT FROM STOP SIGNAL: {}".format(str(err)))    
    else:    
    	 global_logging.exception("EVENT DIFFERENT SignalEvent FROM STOP SIGNAL: {}".format(isinstance(event, gdb.BreakpointEvent))) 

def set_event_inst_adr(event):
    # Accessing global vars
    global global_logging, was_hit, bit_flip,bpia,t,primero,data_kernels
    if (isinstance(event, gdb.SignalEvent)):
      try:     
        # Just checking if it was hit
        #Generar una direccion aleatoria a un kernel y almacenarlo en checkpointkernel
        #checkpointkernel=" *0x555555c71ed0 "
        gdb.events.stop.disconnect(set_event_inst_adr)
        BitFlip.update_data_kernels(data_kernels)
       # global_logging.info(BitFlip.principiokernel("lud_diagonal"))
       #global_logging.info(BitFlip.principiokernel("lud_internal"))
       # global_logging.info(BitFlip.principiokernel("lud_perimeter"))
       # global_logging.info(BitFlip.principio2kernel("lud_diagonal"))
       # global_logging.info(BitFlip.principio2kernel("lud_internal"))
       # global_logging.info(BitFlip.principio2kernel("lud_perimeter"))
        checkpointkernel=BitFlip.address_random(data_kernels)
    
        global_logging.info("BREAK {} \n".format(checkpointkernel))
        bpia=gdb.Breakpoint(checkpointkernel)
        
        gdb.events.stop.connect(set_event_break_instr_adr)
      except Exception as err:
        global_logging.exception("EVENT DIFFERENT FROM STOP SIGNAL: {} IN set_event_inst_adr ".format(str(err)))      
        
def set_event_break_instr_adr(event):
    # Accessing global vars
    global global_logging, was_hit, bit_flip,bpia,t,primero
    if (isinstance(event, gdb.BreakpointEvent)):
      try: 
        gdb.events.stop.disconnect(set_event_break_instr_adr)
        global_logging.info("RUN BREAK {} \n")
        bpia.delete()
        # Just checking if it was hit
        if bit_flip.fault_injected is False:
            bit_flip.single_event()
            global_logging.info("BIT FLIP SET ON SIGNAL {}".format(event.stop_signal))
        #global_logging.info ("Enviado senal a "+ str(pid))
        #bpia.enabled=False
        
        
        gdb.events.stop.connect(set_event_inst_adr)
        #sendsignal(cp.SIGNAL_STOP)
        gdb.execute('c')     
      except Exception as err:
        global_logging.exception("EVENT DIFFERENT FROM STOP SIGNAL: {} IN set_event_break_instr_adr".format(str(err)))     
             

#De esta forma, si llega un event por nexti (event.stop), no realiza nada.
"""
Main function
"""


def main():
    global global_logging, register, injection_site, bits_to_flip, fault_model, was_hit, bit_flip, arg0,t,kernel,pid,bp,data_kernels,rsi,traza
   
    was_hit = False
    indirect= cp.INDIRECT_KERNEL 
    pruebaDebug=True
    # Initialize GDB to run the app
    gdb.execute("set confirm off")
    gdb.execute("set pagination off")
    gdb.execute("set target-async off")
    gdb.execute("set non-stop off")

    # Connecting to a exit handler event
    gdb.events.exited.connect(exit_handler)

   
                           
    # Get variables values from environment
    # Firsn parse line
    [kernel,pid,max_regs,file_connect,bits_to_flip, fault_model, flip_log_file,
     gdb_init_strings, injection_site] = arg0.split('|')
    
   
    pruebaDebug=(cp.INJECTION_SITES[injection_site]==cp.INST_OUT_V1)
    # Logging
    global_logging = Logging(log_file=flip_log_file)
    global_logging.info("Starting flip_value script "+" called by " + str(pid) + " for stop kernel " + str(kernel)+". This kernel has"+str(max_regs)+".");
    try:
        for init_str in gdb_init_strings.split(";"):
            gdb.execute(init_str)
            global_logging.info("initializing setup: " + str(init_str))

    except gdb.error as err:
        global_logging.exception("ERROR on initializing setup: {}".format(str(err)))

    # Set Breakpoint attributes to be use
    bits_to_flip = [i for i in bits_to_flip.split(",")]
    fault_model = int(fault_model)
    bit_flip = BitFlip(bits_to_flip=bits_to_flip, fault_model=fault_model,max_regs=max_regs,
                       logging=global_logging, injection_site=cp.INJECTION_SITES[injection_site])
    data_kernels=bit_flip.read_data_kernels(pruebaDebug)                    
           
    # Start app execution
    t=time.clock();
    gdb.Breakpoint('main')
    #gdb.execute("break "+kernel)
    
    
   
   
   
    global_logging.info("Put Break "+kernel+" "+ str(time.clock()-t))
    gdb.execute("r")

    try:
       pid_bench=gdb.execute ("info proc", to_string=True).splitlines()[0].split(' ')[1]
    except:
      global_logging.info("problema solictando info proc")
  
    global_logging.info("PID: {}".format(pid_bench)) 
       
    fp= open(file_connect,"w")
    fp.write(pid_bench)
    fp.close()
    # Connecting to a stop signal event
    if indirect:
      print ("Indirecto")
      gdb.execute("set cuda break_on_launch application")  
    else: 
      bp=gdb.Breakpoint(kernel)  
    gdb.execute('c')  
   

    #bp.enabled=False
    if indirect:
      gdb.execute("set cuda break_on_launch none")
      gdb.events.stop.connect(set_event_inst_adr)
    else:
      bp.delete()
      gdb.events.stop.connect(set_event_normal)
    global_logging.info("Before breakpoint"+ str(time.clock()-t))
    global_logging.info ("Enviado senal a "+ str(pid))
    sendsignal(cp.SIGNAL_STOP)
    gdb.execute('c')
    
    print("4")
    i = 0
    try:
        while 'The program' not in gdb.execute('c', to_string=True):
            i += 1
    except Exception as err:
        global_logging.info("CONTINUED {} times".format(i))
        err_str = str(err).rstrip()
        global_logging.exception("IGNORED CONTINUE ERROR: {}".format(err_str))

        # Make sure that it is going to finish
        if 'Failed' in err_str:
            gdb.execute('quit')
            global_logging.exception("QUIT REQUIRED")
    print("6")

# Call main execution
global_logging = None
register = None
bits_to_flip = None
fault_model = None
was_hit = False
injection_site = None
bit_flip = None

main()






