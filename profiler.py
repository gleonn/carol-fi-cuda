import gdb
import os
import time
import re
import sys
import copy
import common_functions as cf 
from classes.BitFlip import BitFlip

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

def set_event(event):
      global trun,ocurrencias,t,primera
      
      print ("Es mi primera vez"+ str(primera)+"  "+str(ocurrencias))
      if (isinstance(event, gdb.BreakpointEvent)):
        if (primera):
          
          t=time.time()
          print ("Tomo tiempo " + str (t))
          ocurrencias=ocurrencias+1
        else:  
          print ("Para tiempo " + str (time.time()))
          trun=(time.time()-t)
        primera=not primera  
    #  else:  
    #      trun=(time.clock()-t)  
"""
Main function
"""
def main():
  global ocurrencias,t,nosalir,trun,primera
  primera=True	;
  ocurrencias=0;


  # Initialize GDB to run the app
  gdb.execute("set confirm off")
  gdb.execute("set pagination off")
  gdb.execute("set target-async off")
  gdb.execute("set non-stop off")

  # Connecting to a exit handler event
  gdb.events.exited.connect(exit_handler)

  # Connecting to a stop signal event
  gdb.events.stop.connect(set_event)

  # gdb_init_strings = str(os.environ["CAROL_FI_INFO"])
  gdb_init_strings = arg0
  cadena=gdb_init_strings.split(";",4)
 
  print >>sys.stderr, (gdb_init_strings+"---0:"+cadena[0]+"\n-1:"+cadena[1],"\n-2:",cadena[2],"\n-3:", cadena[3],"\n-4:", cadena[4])
  section =cadena[0]=="True" 
  onlycount=cadena[1]=="True" 
  #print ("B "+section+"ke "+kernel_end+" ....")
  print (cadena[3].split(";"))
  print("INIT_str {}".format(cadena[4].split(";")))
  for init_str in  cadena[4].split(";"):
     gdb.execute(init_str)
  maxi=0.  
  gdb.execute("r")
  if (onlycount):     
   
    ks=cadena[2].split(",") 
    #print >>sys.stderr, ("=====================Kernels ")
    #print ("=====================Kernels {}".format(cadena[2]))
    listreg=set ()
    f=open("tmpxxx/kernels.conf","w")
    f.write("[Kernels]\n")
    print(cadena[2])
    f.write("Nombres={}\n".format(cadena[2]))
    f.write("trace={}\n".format(cadena[3]))    
    for x in ks:
      f.write("[{}] \n".format(x))
      nm=BitFlip.numreg(x)
      listreg.update(nm) 
      f.write("Registro={}\n".format(len(nm)))
      f.write("Principio={}\n".format(BitFlip.principiokernel(x)))
      f.write("Tamano={}\n".format(BitFlip.lenkernel(x)))
      
    f.close()
    print(listreg)
    maxi=len(listreg)
    print("Maximo..."+str (maxi)+" o  "+str(max([int(x) for x in listreg] ) ))
    #os.system("chmod 444 tmpxxx/kernels.conf")
  else:
     if (section):
       print("Break & continue");
       gdb.execute("c")
     else:
       print("Finish.........");
       if( len (cadena[2])==0):
         gdb.execute("quit")
       else:
         gdb.execute("finish")
  
     f=open("tmpxxx/return_profiler.conf","w")
     f.write("[DEFAULT] \nOcurrencias = "+str(ocurrencias)+"\nTiempo = "+str(trun)+"\n")
     
     f.close()	
  sys.exit(maxi)  

main()
