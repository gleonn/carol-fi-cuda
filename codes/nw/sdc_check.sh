#!/usr/bin/sh
# SDC checking diff
# Must compare all things here
# Any particular output comparison must be made here
# To be considered as an SDC or CRASH the
# DIFF_LOG and DIFF_ERR_LOG files must not be empty

# INJ_OUTPUT_PATH, INJ_ERR_PATH, GOLD_OUTPUT_PATH, GOLD_ERR_PATH
# are environment variables defined by the fault_injector.py

# diff stdout

# Special comparison like the following one can be done in this script
grep -q "Result = FAIL" ${INJ_OUTPUT_PATH} >> ${DIFF_LOG}

# diff stderr
diff -B ${INJ_ERR_PATH} ${GOLD_ERR_PATH} > ${DIFF_ERR_LOG}
echo $pwd

diff ./result.txt codes/nw/gold/result.1.txt >> ${INJ_OUTPUT_PATH}

#diff ./result.txt ~/rodinia_3.1/cuda/nw/gold/result.1.txt #>> ${INJ_OUTPUT_PATH}
if [ $? -ne 0 ]
then
       	echo "Result = FAIL" >> ${INJ_OUTPUT_PATH}
else
	echo "Result = PASS" >> ${INJ_OUTPUT_PATH}
fi	
rm result.txt
# Must exit 0
p
diff -B ${INJ_OUTPUT_PATH} ${GOLD_OUTPUT_PATH} > ${DIFF_LOG}
exit 0
