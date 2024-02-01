import random
import sys

import gdb
import re
import common_functions as cf  # All common functions will be at common_functions module
import common_parameters as cp  # All common parameters will be at common_parameters module

# from collections import deque

"""
BitFlip class
to implement the bit flip process.
The methods in this class will execute only inside a CUDA kernel
"""


class BitFlip:
    def __init__(self, **kwargs):
        # If kernel is not accessible it must return
        self.__bits_to_flip = kwargs.get('bits_to_flip')
        self.__fault_model = kwargs.get('fault_model')
        self.__logging = kwargs.get('logging')
        self.__injection_site = kwargs.get('injection_site')
        self.__maxregs=int(kwargs.get('max_regs'))
        self.fault_injected = False
        
    @staticmethod         
    def principiokernel(kernel):
       #Obtiene la direccion de comienzo de un kernel dado
       try:
         l=cf.execute_command(gdb=gdb, to_execute="print {}".format(kernel))
         inicio=l[0].split("}")[1].split("<")[0]
         return inicio
       except:
         l=BitFlip.principio2kernel(kernel)
         inicio=l.split(":")[0].split("<")[0]
         return inicio
    @staticmethod         
    def principio2kernel(kernel):
         #Obtiene la direccion de comienzo de un kernel dado de una forma mas lenta y mas segura
         l=BitFlip.disas(kernel)
         return(l[1])    
    @staticmethod         
    def lenkernel(kernel):
         #Obtiene la longitud (numero de instruccion) de un kernel
         l=BitFlip.disas(kernel)
         i= len(l) - 2
         while  ("NOP" in l[i]):
             i=i-1   
         fin=(l[i].split("<")[1])
         fin=(fin.split(">")[0])#.split("+")[1]
         return fin     
   
    @staticmethod
    def address_random(d):
      # Proporciona una direccion aleatorio, para realizar un breakpoint
      # De la informacion que tiene de los nkernel Principio y Tamano
      
      ky=random.choice(list(d.keys()))
      dir=random.randint(0, (d[ky]['Tamano']/16)-1)
      dir=d[ky]['Principio']+(dir*16)
      return (" *{} ".format(hex(dir)))  
    def readtraza(self,file):
       self.__traza=cf.load_config_file(file)
    def read_data_kernels(self,readtrace):
      #Leer la informacion de los kernels a trabajar
      conf =cf.load_config_file("tmpxxx/kernels.conf")
      lista= conf.get('Kernels', 'Nombres')
      if readtrace:
         self.readtraza(conf.get('DEFAULT',trace))
      datoskernels={}
      for i in lista.split(","):
        elem={}
        elem['Principio']=int(conf.get(i,'Principio'),16)
        #elem['Principio']=int(BitFlip.principiokernel(i),16)
        elem['Tamano']=int(conf.get(i,'Tamano'))
        datoskernels[i]=elem
      return datoskernels
    @staticmethod
    def update_data_kernels(dict):
      #Rellenar un diccionario con la direccion de comienzo.
      for i in dict:  
        dict[i]['Principio']=int(BitFlip.principiokernel(i),16)

    @staticmethod
    def __exception_str():
        exc_type, exc_obj, exc_tb = sys.exc_info()
        return "Exception type {} at line {}".format(exc_type, exc_tb.tb_lineno)
    @staticmethod
    def disas(kernel):
      #Desensamblando de un kernel 
      try:
        disassemble_array = cf.execute_command(gdb=gdb, to_execute="disassemble {}".format(kernel))
        
      except:
        #si no ha funcionado la forma general, es que solo habra uno y es el que es el activo.
        disassemble_array = cf.execute_command(gdb=gdb, to_execute="disassemble")
      return disassemble_array
    @staticmethod
    def numreg (kernel):
      #Calculo del numero de registro usados en un kernel 
      disassemble_array=BitFlip.disas(kernel)
      listareg=set()
      listaregdst=set()
      listaregcond=set()
      for i in range(0, len(disassemble_array) - 1):
        line = disassemble_array[i]
        #m=re.match(r".*:\t(\S+) .*",line)#Para que es m
        todacadena="ASSM_LINE:{}".format(line)
        lista=re.findall(r"R(\d+)", line)
        if (len(lista) > 0):   	
           listareg.update(lista)
        lista=re.findall(r" P(\d+)", line)
        if (len(lista) > 0): 
           listaregcond.update(lista)

      print ("Registros Visibles ({})".format(len(listareg)))
      print (listareg)
      print ("Registros destino ({})".format(len(listaregdst)))
      print (listaregdst)
      print ("Registros condicionales ({})".format(len(listaregcond)))
      print (listaregcond)
      return (listareg)
    """
    TODO: Describe the method
    """
    @staticmethod
    def kernelnow():
      #Obtiene el kernel enfocado,
      str=gdb.execute(" info cuda kernels",to_string=True)
      str=str.splitlines()
      index=str[0].find("Invocation")
      for i in range(1, len(str) ):
          if "* " in str[i] :
             ret=(str[i][index:]).split("(")[0]
      return ret     
      
 

    def asmline(self):
      #Leo la instruccion en ensamblador a ejecutar.
      linea=cf.execute_command(gdb=gdb, to_execute="x/1i $pc")
      self.__logging.info("ASSM_LINE:{}".format(linea[0]))
      return linea
      
    
    def asmline2(self):
      #Difiere de asmline donde visualiza la informacion
      linea=cf.execute_command(gdb=gdb, to_execute="x/1i $pc")
      print("ASSM_LINE:{}".format(linea[0]))
      return linea

    def reg_asmline( self):
      #Obtengo los registros de la instruccion a ejecutar y los devuelvo una lista
      linea= self.asmline()
      lista=re.findall(r"R(\d+)", linea[0])
      setlista=set()
      setlista.update(lista)
      return setlista
    def LoadValuesRegsInst(self):  
      lista=self.reg_asmline()
      listareg=[" R{} ".format(x) for x in lista]
      strlistareg="info registers " 
      for x in listareg:
        strlistareg+=x;
      self.__stringregs=strlistareg
    def ValueRegsInst (self):
       valores= cf.execute_command(gdb=gdb, to_execute=self.__stringregs)
       return valores
      
    def regmod (self):
      lista=self.reg_asmline()
      while len(lista) == 0: #Habria que poner un limite. 
        #Busco una instruccion que referiencia algun registro 
        self.__logging.info("INSTRUCTION WITHOUT DESTINATION REGISTER")              
        self.nextinstr()
      self.LoadValuesRegsInst()
      #Obtengo el valor de los registro referenciados
      return self.ValueRegsInst()
    def nextinstr(self):
         
          x=cf.execute_command(gdb=gdb, to_execute="nexti") 
         
    def dictreg(self,valores):
      
      #Almaceno en un dictionario los valores de los registros obtenido de un info registers
      regs={}
      for x in valores:
        m = re.match(r".*R(\d+).*0x([0-9a-fA-F]+).*", x)
        if m:
          regs[m.group(1)]=m.group(2)
        
      return regs    
    def cmpregdst (self,valores,regs):
     regdst=set()
     for x in valores:
        m = re.match(r".*R(\d+).*0x([0-9a-fA-F]+).*", x)
        if m:
          #print("El registro {} tiene {} y tenia{}".format(m.group(1),m.group(2),regs[m.group(1)]))
          if (regs[m.group(1)]!=m.group(2)):
            #print("Diferente")
            regdst.add(m.group(1))  
     return regdst
    def mypcis(self):
        #Obtiene el pc relativo
        valores= cf.execute_command(gdb=gdb, to_execute="info registers pc")
        pc=int((valores[0].split("+")[1]).split(">")[0])       
        return pc
    def RegDstInst(self,despl):
        #Obtiene registro destino de la instruccion -despl
        linea=cf.execute_command(gdb=gdb, to_execute="x/1i $pc-"+str(despl))
        rd=re.findall(r"R(\d+)",linea[0])
        if (len(rd) >0):
           rd=rd [0]
        return  rd
    def isfininstruction(self):
        linea=cf.execute_command(gdb=gdb, to_execute="x/1i $pc")
        lista=linea[0].find("EXIT")
        return (lista!=-1)
    def regdst(self):
        #Regsitro modificados en la ejecuccion de una instrucciones. varios si no hace referencia
        # a ningun registro.
        regs=self.dictreg(self.regmod())
        self.nextinstr()
        self.LoadValuesRegsInst()
        valores=self.ValueRegsInst()
        r=self.cmpregdst(valores,regs)
        self.__logging.info ("Registros Modificados: {}".format(r))
    def CalculateRegDestInst(self,despl):
       r=self.RegDstInst(despl)  
       if cp.HIGHPRECISION:
          if (len(r)>0):
             print ("=========HP+++++++++++++================")
             valores=self.ValueRegsInst()
             print ("Valores:...{}".format(valores))
             r=self.cmpregdst(valores,self.__regs)
             
             if (len(r)>0):
                r=r.pop()
                print ("Registros modificados:...{}".format(r))
             self.__regs=self.dictreg(valores)
             print ("Regs:...{}".format(self.__regs))
    
           
       return r  
          
    def analisis(self,kernels):
      gdb.execute("set cuda break_on_launch none")
      for kernel in kernels:
        self.asmline2()
        #self.__logging.raw("Kernel {}".format(kernel))
        #gdb.execute()
        gdb.execute("delete breakpoints")
        str=gdb.execute("break "+kernel,to_string=True)
        #self.__logging.raw("====".format(str))
        gdb.execute("c")
        self.asmline2()
        self.__logging.raw("["+kernel+"]\n")
        pcold=0

        dict={}
        fin=self.isfininstruction()
        rold=self.RegDstInst(0) 
        print("Rold={}".format(rold))
        pcold=self.mypcis()
        self.LoadValuesRegsInst()
        self.__regs=self.dictreg(self.ValueRegsInst())
        print ("Regs:...{}".format(self.__regs))
        self.nextinstr()
        #Y si la primera instruccion no tiene argumentos?
        i=0
        while not fin:
         # regs=self.dictreg(self.regmod()) # Igual solo tendriamos que mirar el regfdst de la instruccion      
         # r=self.cmpregdst(valores,regs)
          pc=self.mypcis()
          print("====")
          self.asmline2()
          #r=self.RegDstInst(16) #
          r=self.CalculateRegDestInst(16)
          if (pc!=pcold+16) or (len(r)==0) :
              if not (pc in dict):
                 print("Rold={}".format(rold))
                 a={rold:1}
                 dict[pc]={rold:1}
              else: 
                 if not (rold in dict[pc] ):
                     (dict[pc]) [rold]=1
                 else:
                     a=(dict[pc])[rold]
                     (dict[pc]) [rold]=a+1  
              print ("++++Instruccion cuyo pc {} tiene estos valores {}".format(pc,dict[pc]))          
              if (pc!=pcold+16):     
                print ("++++Ruptura de secuencia desde {}".format(pcold)) 
              else:
                print("++++Sin operandos la instruccion anterior")
          else:           
              rold=r
              print("Registro {}".format(r))
          pcold=pc   
          self.nextinstr()
          
          fin= self.isfininstruction()
          
          
          
          i=i+1
         
        for k in dict:
           print("Clave: {} {} ".format(k,type(k)))
           #cad= str(key)+ "="
        for key in dict:   
      
           cad="{} =".format(key)
           sep=" "
           for key2 in dict[key]:
             #cad=cad+sep+str(key2)+ "x"+str(( dict[key]) [key2])
             cad="{}{}{}x{}".format(cad,sep,key2,(dict[key]) [key2])
             sep=","
           self.__logging.raw(cad+"\n")  
      

       
    def LastRegDest(self):
        #Obtiene el ultimo registro destino modificado, se consulta la traza
        # si el pc no esta en la traza, es que la anterior instruccion indica
        # el ultimo registro destino.
        kernel=self.kernelnow()
        pc=str(self.mypcis())
        traza=self.__traza
        self.__logging.info("kernel {} pc {} pcespeciales{} \n".format(kernel,pc,traza.options(kernel)))
        
        if (pc in traza.options(kernel)):
          self.__logging.info("Si es especial {}".format(traza.get(kernel,pc)))
          a= (traza.get(kernel,pc)).split(",")
          ac=0
          self.__logging.info(" Valor {}".format(a))
          for x in a:
            ac=ac+int(x.split("x")[1])
          self.__logging.info("Total {}".format(ac))  
          rd=0
          iac=(random.randint(0, ac-1))
          self.__logging.info("Elegido {}".format(iac))  
          for x in a:
            t=x.split("x")
            if (int(t[1]) >=iac):
                   rd=t[0]
                   break
            else:
               iac=iac-int(t[1])            
          #print("Registro Destino es {}".format(rd))
        else:          
         rd=self.RegDstInst(16)
         self.__logging.info("Es normal {}".format(rd))
        self.__logging.info("Registro es {}".format(rd)) 
        return rd    
    def  __inst_generic_injector(self):
  
        r=self.regdst()    
        while (len(r) ==0):
             self.__logging.info("INSTRUCTION WITHOUT OPERANDS")
             gdb.execute("nexti")
             r=self.regdst()
             
                    
        self.__register="R{}".format(r.pop())
        self.__logging.info("SELECTED_REGISTER:{}".format(self.__register))
        
        
                # __rf_generic_injector will set fault_injected attribute
        self.__rf_generic_injector()
     
    def single_event(self):
        # fault_injected attribute will be set by the methods that perform fault injection
        # Focusing the thread. If focus succeed, otherwise not
        if self.__thread_focus():
            # Do the fault injection magic

            # Register File mode
            if cp.RF == self.__injection_site:
                # Select the register before the injection
                #self.__logging.info("select-register")
                self.__select_register()
                # RF is the default mode of injection
                #self.__logging.info("rf-genera")
                self.__rf_generic_injector()
                #self.__logging.info("rf-genera-fin")
            # Instruction Output mode
            elif cp.INST_OUT == self.__injection_site:
               self.__inst_generic_injector()()
            elif cp.INST_OUT_ORI == self.__injection_site:
               self.__inst_generic_injector_old()
            elif cp.INST_V1 == self.__injection_site:   
                self.__inst_generic_injector_preliminar()
            # Instruction Address mode
            elif cp.INST_ADD == self.__injection_site:
                self.__logging.exception("INST_ADD NOT IMPLEMENTED YET")
                self.__logging.exception(self.__exception_str())
                self.fault_injected = False

            # Test fault injection result
            self.__logging.info("Fault Injection " + ("Successful" if self.fault_injected else "Went Wrong"))

    """
    Selects a valid thread for a specific
    kernel
    return the coordinates for the block
    and the thread
    """

    def __thread_focus(self):
        try:
            # Selecting the block, it must be a valid block
            blocks = cf.execute_command(gdb=gdb, to_execute="info cuda blocks")
            # empty lists are always false
            while blocks:
                chosen_block = random.choice(blocks)
                # remove it from the options
                blocks.remove(chosen_block)

                m = re.match(r".*\(.*\).*\((\d+),(\d+),(\d+)\).*", chosen_block)
                # Try to focus
                if m:
                    change_focus_block_cmd = "cuda block {},{},{}".format(m.group(1), m.group(2), m.group(3))
                    block_focus = cf.execute_command(gdb=gdb, to_execute=change_focus_block_cmd)
                    # empty lists are always false
                    if block_focus:
                        # Thread focus return information
                        self.__logging.info("CUDA_BLOCK_FOCUS:{}".format(block_focus))
                        # No need to continue to seek
                        break

            # Selecting the thread
            threads = cf.execute_command(gdb=gdb, to_execute="info cuda threads")
            while threads:
                chosen_thread = random.choice(threads)
                # remove it from the options
                threads.remove(chosen_thread)

                m = re.match(r".*\(.*\).*\(.*\).*\(.*\).*\((\d+),(\d+),(\d+)\).*", chosen_thread)
                # Try to focus
                if m:
                    change_focus_thread_cmd = "cuda thread {},{},{}".format(m.group(1), m.group(2), m.group(3))
                    thread_focus = cf.execute_command(gdb=gdb, to_execute=change_focus_thread_cmd)

                    # empty lists are always false
                    if thread_focus:
                        # Thread focus return information
                        self.__logging.info("CUDA_THREAD_FOCUS:{}".format(thread_focus))
                        # No need to continue to seek
                        break

        except Exception as err:
            err_str = str(err)
            self.__logging.exception("CUDA_FOCUS_CANNOT_BE_REQUESTED, ERROR:" + err_str)

            # No need to continue if no active kernel
            if err_str == cp.FOCUS_ERROR_STRING:
                return False

        # If we are inside the kernel return true
        return True

    """
    Flip a bit or multiple bits based on a fault model
    """

    def __rf_generic_injector(self):
        try:
            # get register content
            self.asmline()
            reg_cmd = cf.execute_command(gdb, "p/t ${}".format(self.__register))
            m = re.match(r'\$(\d+)[ ]*=[ ]*(\S+).*', reg_cmd[0])

            reg_content_old = str(m.group(2))
            # Make sure that binary value will have max size register
            reg_content_full_bits = str(
                '0' * (cp.SINGLE_MAX_SIZE_REGISTER - len(reg_content_old))) + reg_content_old

            reg_content_new = ''

            # Single or double bit flip or Least significant bits
            if self.__fault_model in [cp.FLIP_SINGLE_BIT, cp.FLIP_TWO_BITS, cp.LEAST_16_BITS, cp.LEAST_8_BITS]:
                # single bit flip or Double bit flip
                reg_content_new = reg_content_full_bits
                for bit_to_flip in self.__bits_to_flip:
                    reg_content_new = self.__flip_a_bit(int(bit_to_flip), reg_content_new)
                reg_content_new = hex(int(reg_content_new, 2))

            # Random value or Zero value
            elif self.__fault_model == cp.RANDOM_VALUE or self.__fault_model == cp.ZERO_VALUE:
                # random value is stored at bits_to_flip[0]
                reg_content_new = self.__bits_to_flip[0]

            # send the new value to gdb
            flip_command = "set ${} = {}".format(self.__register, reg_content_new)
            reg_cmd_flipped = cf.execute_command(gdb, flip_command)

            # ['$2 = 100000000111111111111111']
            modify_output = cf.execute_command(gdb, "p/t ${}".format(self.__register))[0]

            # With string split it is easier to crash
            reg_modified = re.match(r"(.*)=(.*)", modify_output).group(2).strip()

            # Return the fault confirmation
            self.fault_injected = reg_content_old != reg_modified

            # Log the register only if the fault was injected, reduce unnecessary file write
            if self.fault_injected:
                # LOGGING
                self.__logging.info("SELECTED_REGISTER:{}".format(self.__register))
                # Logging info result extracted from register
                self.__logging.info("old_value:{}".format(reg_content_old))
                # Also logging the new value
                self.__logging.info("new_value:{}".format(reg_modified))

                # Log if something was printed
                # empty list is always false
                if reg_cmd_flipped:
                    self.__logging.info("flip command return:{}".format(reg_cmd_flipped))

        except Exception as err:
            self.__logging.exception("fault_injection_python_exception: {}".format(err))
            self.__logging.exception(self.__exception_str())
            self.fault_injected = False

    """
    Flip only a bit in a register content
    """

    @staticmethod
    def __flip_a_bit(bit_to_flip, reg_content):
        return reg_content[:bit_to_flip] + ('0' if reg_content[bit_to_flip] == '1' else '1') + reg_content[
                                                                                               bit_to_flip + 1:]

    """
    Runtime select register
    """

    def __select_register(self):
        # Start on 1 to consider R0
        #max_num_register = 
        # registers_list.popleft()
        #registers_list = cf.execute_command(gdb=gdb, to_execute="info registers")
        #for line in registers_list:
        #    m = re.match(r".*R.*0x([0-9a-fA-F]+).*", line)
        #    if m and m.group(1) != '0':
                #self.__logging.info ("LIne salida:{}".format(m.group(1))
        #         max_num_register += 1
                #self.__logging.info("LIne entrada {}--max{}".format(line,max_num_register))
        #self.__logging.info("MAX_NUM_REGISTER:{}".format(self.__maxregs))        
        self.__register = "R{}".format(random.randint(0, (self.__maxregs)-1))
       
    """
    Instruction injector    
    """
    def __inst_generic_injector_preliminar(self):
        self.__register="R{}".format(self.LastRegDest())
        self.__logging.info("SELECTED_REGISTER:{}".format(self.__register))
        self.__rf_generic_injector()
    def __inst_generic_injector_old(self):
        disassemble_array = cf.execute_command(gdb=gdb, to_execute="disassemble")
        # Search the line to inject
        # -1 will use the next instruction after program counter
        for i in range(0, len(disassemble_array) - 1):
            next_line = disassemble_array[i] # He modifico i+1 por i

            # => defines where the program counter is
            # There is an instruction on this line
            # then inject in the output register
            if "=>" in disassemble_array[i] and re.match(r".*:\t(\S+) .*", next_line):
                # If it gets the PC + 1 then I must inject in the input of the next instruction
                # Which is the most right register (-1 index)
                self.__register = "R{}".format(re.findall(r"R(\d+)", next_line)[-1])
                self.__logging.info("SELECTED_REGISTER:{}".format(self.__register))
                self.__logging.info("ASSM_LINE:{}".format(next_line))

                # __rf_generic_injector will set fault_injected attribute
                self.__rf_generic_injector()
                break  # avoid execute the else
        else:
            self.__logging.exception("SEARCH_FOR_PC_INDICATOR_FAILED")
            self.fault_injected = False
