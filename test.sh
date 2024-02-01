#!/bin/bash

set -e

#uncomment to a more verbose script
#set -x

FAULTS=1000
#CONFFILE=codes/matrixMul/matrixmul_16K.conf

#CONFFILE=codes/mmElem/matrixmul_16K.conf
CONFFILE=codes/lavaMD/lavaMD.conf
echo "Step 1 - Profiling the application for fault injection"
./app_profiler.py -c ${CONFFILE} $*

echo "Comienzo.." >> tiempos
date >> tiempos

echo "Step 2 - Running ${FAULTS} on ${CONFFILE}"
./fault_injector.py -i ${FAULTS} -c ${CONFFILE} -n 1  $*
while  test -f "tmpxxx/num_rounds.conf" 
do
cat tmpxxx/num_rounds.conf >> tmpxxx/tandas
./fault_injector.py -i ${FAULTS} -c ${CONFFILE} -n 1 $*
echo "==============================="
done

echo "Fault injection finished"
date >> tiempos
echo "Fin..." >> tiempos
exit 
