import os
import re
import gdb
import time
import common_functions as cf
from classes.BitFlip import BitFlip
from classes.Logging import Logging
import common_parameters as cp

def exit_handler(event):
   global nosalir
   nosalir=False
  
   print(str("event type: exit"))
   try:
        print("exit code: {}".format(str(event.exit_code)))
   except Exception as err:
        err_str = "ERROR: {}".format(str(err))
        print(err_str)


"""
Handler that will put a breakpoint on the kernel after
signal
"""

def selectrd():
  linea= cf.execute_command(gdb=gdb, to_execute="x/1i $pc")
  print (linea)#+"-"+str(len(linea))+"-"+linea[0])
  print ("============")
  lista=re.findall(r"R(\d+)", linea[0])
  #Si no hay nexti 
  listareg=[" R{} ".format(x) for x in lista]
  strlistareg="info registers "
  for x in listareg:
    strlistareg+=x;
  print (strlistareg)  
  valores= cf.execute_command(gdb=gdb, to_execute=strlistareg)  
  print("===========VALORES==========")
  regs={}
  for x in valores:
    print(x)
    m = re.match(r".*R(\d+).*0x([0-9a-fA-F]+).*", x)
    if m:
      regs[m.group(1)]=m.group(2)
      print (str(m.group(0))+"  "+str(m.group(1)))
  #Loop----
  gdb.execute("nexti")
  linea= cf.execute_command(gdb=gdb, to_execute="x/1i $pc")
  valores= cf.execute_command(gdb=gdb, to_execute=strlistareg)
  regdst={}
  for x in valores:
    print(x)
    m = re.match(r".*R(\d+).*0x([0-9a-fA-F]+).*", x)
    if m:
      if (regs[m.group(1)]!=m.group(2)):
        regdst.add(m.group(1))
  
  
  
  print (type(lista))
  print(lista)
def set_event(event):
      global trun,ocurrencias,t
      print("===,casi,casi,casi,=============")
      if (isinstance(event, gdb.BreakpointEvent)):
        print("===,si,si,si,=============")
        t=time.clock()
        ocurrencias=ocurrencias+1
      else:  
        trun=(time.clock()-t)

def kernels():
    data_kernels=BitFlip.read_data_kernels()
    print("DIct {}".format(data_kernels))
    BitFlip.update_data_kernels(data_kernels)
    print("DIct {}".format(data_kernels))
    BitFlip.principiokernel("lud_diagonal")
    BitFlip.principiokernel("lud_internal")
    BitFlip.principiokernel("lud_perimeter")
    BitFlip.principio2kernel("lud_diagonal")
    BitFlip.principio2kernel("lud_internal")
    BitFlip.principio2kernel("lud_perimeter")
    r=BitFlip.kernelnow()
    print(r)
    #[p,f]=BitFlip.rangekernel("lud_diagonal")
    #print (p,f)
    gdb.execute('disas lud_diagonal')
    gdb.execute('disas lud_internal')
    gdb.execute('disas lud_perimeter')
    
def main():      
    global ocurrencias,t,nosalir,trun,bf
    was_hit = False

    ocurrencias=0
    # Initialize GDB to run the appset pagination off
    gdb.execute("set confirm off")
    gdb.execute("set pagination off")
    gdb.execute("set target-async off")
    gdb.execute("set non-stop off")

    # Connecting to a exit handler event
    gdb.events.exited.connect(exit_handler)

    # Connecting to a stop signal event
    gdb.events.stop.connect(set_event)
    
    gdb.execute("file codes/lud/cuda/lud_cuda")
    gdb.execute("set arg -s 10000")
   
    gdb.execute("set cuda break_on_launch application")
    gdb.execute('r')
  
    nosalir=True
    gdb.events.stop.disconnect(set_event)
    g=Logging(log_file="ludv2.conf")
    # Force a create un object, don't care arguments
    bf = BitFlip(bits_to_flip=27, fault_model=0,max_regs=18,
                       logging=g, injection_site=cp.INJECTION_SITES["INST_OUT"])
   
    bf.analisis(["lud_diagonal", "lud_perimeter","lud_internal"])
                     

main()


