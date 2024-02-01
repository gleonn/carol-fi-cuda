#!/usr/bin/env python3
import argparse
import os
import re
import time
import common_functions as cf
import common_parameters as cp


def generate_dict(sm_version, input_file_name):
    with open(input_file_name, "r") as f:
        # dictionary to store the number of allocated registers per static
        kernel_reg = {}

        kernel_name = ""  # temporary variable to store the kernel_name
        check_for_register_count = False

        # process the input file created by capturing the stderr while compiling the
        # application using -Xptxas -v options
        for line in f:  # for each line in the file
            m = re.match(r".*Compiling entry function.*'(\S+)'.*for.*'{}'.*".format(sm_version), line)
            if m:
                kernel_name = m.group(1)
                check_for_register_count = True

            m = re.match(r".*Used[ ]+(\d+)[ ]+registers.*", line)
            if check_for_register_count and m:
                reg_num = m.group(1)  # extract register number
                if kernel_name not in kernel_reg:
                    # associate the extracted register number with the kernel name
                    kernel_reg[kernel_name] = int(reg_num.strip())
                else:
                    print("Warning: {} exists in the kernel_reg dictionary. "
                          "Skipping this register count.".format(kernel_name))
                check_for_register_count = False

    return kernel_reg


"""
Function that calls the profiler based on the injection mode
"""


def profiler_caller(gdb_exec, kernels, benchmark_binary, benchmark_args,device,section,trace):
    acc_time = 0
    acc_time_profiler=0
    script = 'env CUDA_VISIBLE_DEVICES={} {} -ex \'py arg0 = {}\' -n -batch -x {}'
    benchmark_args_striped = benchmark_args.replace('\\n', '').replace('\\', '')
   # print ("KERNEL"+kernels)
    #init_string = '"file {}; set args {}"'.format(benchmark_binary, benchmark_args_striped)
    print ("SECTION {}".format(section))
    init_string = '"{};{};{};{};file {}; set args {}; set cuda break_on_launch application"'.format(False,True,kernels,trace,benchmark_binary, benchmark_args_striped)
    profiler_cmd = script.format(device, gdb_exec, init_string, cp.PROFILER_SCRIPT)
    max_registers=os.system(profiler_cmd) >>8
    os.system("cat tmpxxx/kernels.conf")
    print ("Maximo numero de registros ###################################+++")
    print(max_registers,max_registers>>8)     
   
    if  bool(section):
      init_string = '"{};{};{};{};file {}; set args {}; break {}; break {}"'.format( bool(section),False,kernels,trace,benchmark_binary,benchmark_args_striped,section['begin'],section['end'])
    else:  
      init_string = '"{};{};{};{};file {}; set args {}; break {}"'.format(False,False,kernels,trace,benchmark_binary, benchmark_args_striped,kernels.split(",")[0])
    profiler_cmd = script.format(device, gdb_exec, init_string, cp.PROFILER_SCRIPT)
    print ("Profiler caller")
    if cp.DEBUG:
        print("PROFILER CMD: {}".format(profiler_cmd))

    for i in range(0, cp.MAX_TIMES_TO_PROFILE):
        start = time.time()
        os.system(profiler_cmd)
        end = time.time()
        ret_profiler = cf.load_config_file("tmpxxx/return_profiler.conf")
        acc_time_profiler+=float(ret_profiler.get('DEFAULT', 'Tiempo'))
        acc_time += end - start
        cf.kill_all("killall -9 {}; killall -9 {}".format(
            os.path.basename(gdb_exec), os.path.basename(benchmark_binary)))
    f=open("tmpxxx/return_profiler.conf","w")
    f.write("[DEFAULT] \nMEDIA_TIME_PROFILER= "+str(acc_time_profiler / cp.MAX_TIMES_TO_PROFILE)+"\nMEDIA_TIME= "+
    str(acc_time / cp.MAX_TIMES_TO_PROFILE )+"\nMAX_REGISTERS="+str(max_registers))
    f.close()     
    return acc_time_profiler / cp.MAX_TIMES_TO_PROFILE, acc_time / cp.MAX_TIMES_TO_PROFILE, max_registers




"""cf.load
Function to generate the gold execution
"""


def generate_gold(gdb_exec, benchmark_binary, benchmark_args,device,trace):
    # Create tmp path and clean it if it exists
    tmp_path = os.path.dirname(os.path.realpath(__file__)) + "/" + cp.LOGS_PATH + "/tmp"
    os.system("mkdir -p " + tmp_path)
    os.system("rm -rf " + tmp_path + "/*")

    script = 'env CUDA_VISIBLE_DEVICES={} {} -ex \'py arg0 = {}\' -n -batch -x {} > {} 2> {}'
    init_string = '"{};{};{};{};file  {}; set args {}"'.format(False,False,"",trace,benchmark_binary, benchmark_args)
    profiler_cmd = script.format(device, gdb_exec, init_string, cp.PROFILER_SCRIPT, cp.GOLD_OUTPUT_PATH, cp.GOLD_ERR_PATH)
    if cp.DEBUG:
        print("PROFILER CMD: {}".format(profiler_cmd))

    # Execute and save gold file
    return os.system(profiler_cmd)


def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--conf', dest="config_file", help='Configuration file', required=True)
    parser.add_argument('-d', '--device', dest="device", help="The GPU to perform FI."
                                                              " Default is 0.", required=False, default=0, type=int)
    args = parser.parse_args()
    
   
    # Read the configuration file with data for all the apps that will be executed
    conf = cf.load_config_file(args.config_file)

    
    benchmark_binary = conf.get('DEFAULT', 'benchmarkBinary')
  
    cp.LOGS_PATH="{}l_{}_d{}".format(cp.LOGS_PATH,benchmark_binary.split('/')[-1],args.device)    
    cp.rewrite_path()

    os.system("rm -f {}".format(cp.KERNEL_INFO_DIR))  
    # First set env vars
    cf.set_python_env()

    ########################################################################
    # Profiler step
    # Max time will be obtained by running
    # it will also get app output for golden copy
    # that is,
    print("###################################################\n1 - Profiling application")
    if 'benchmarkBinary_noverificar' in conf['DEFAULT']:
        benchmark_binary = conf.get('DEFAULT', 'benchmarkBinary_noverificar')
    else:
        benchmark_binary = conf.get('DEFAULT', 'benchmarkBinary')
    if 'benchmarkArgs_noverificar' in conf['DEFAULT']:
      benchmark_args = conf.get('DEFAULT', 'benchmarkArgs_noverificar')
    else:
      benchmark_args = conf.get('DEFAULT', 'benchmarkArgs')
 
    section={}
    if ('section_end' in conf['DEFAULT']):    
       section['begin']=conf.get('DEFAULT','section_begin')
       section['end']=conf.get('DEFAULT','section_end')
    gdb_exec = conf.get("DEFAULT", "gdbExecName")
    kernels=conf.get('DEFAULT', 'kernels')
    trace=conf.get('DEFAULT','trace')
    [max_time_kernel,max_time_app,max_regs] = profiler_caller(gdb_exec=gdb_exec,kernels=kernels, benchmark_binary=benchmark_binary, benchmark_args=benchmark_args,device=args.device,section=section,trace=trace)
    print ("Time kernel= "+str(max_time_kernel)+ "Time app "+str(max_time_app))
    # saving gold
    print ("Saving gold");
    os.system("cat tmpxxx/kernels.conf")
    generate_gold_result = generate_gold(gdb_exec=gdb_exec,benchmark_binary=benchmark_binary, benchmark_args=benchmark_args,device=args.device,trace=trace)
    os.system("cat tmpxxx/kernels.conf")
    if generate_gold_result != 0:
      raise EnvironmentError("Gold generation did not finish well, the fault injection will not work")

    # Remove trash GDB info from the std output and the err output
    cf.remove_useless_information_from_output(cp.GOLD_OUTPUT_PATH)
    cf.remove_useless_information_from_output(cp.GOLD_ERR_PATH)

    # Save the kernel configuration txt file
    cf.save_file(file_path=cp.KERNEL_INFO_DIR, data={'max_time': max_time_app,'max_time_kernel': max_time_kernel,'max_regs':max_regs})
    os.system("cat tmpxxx/kernels.conf")
    print("1 - Profile finished\n###################################################")


if __name__ == '__main__':
    main()
