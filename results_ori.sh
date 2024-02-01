cd $1
fi=$(find failed-injection -name "carol_fi_inj_bench_output*"| wc -l)
crash=$(find masked -name "carol_fi_inj_bench_output*"| wc -l)
hangs=$(find hangs -name "carol_fi_inj_bench_output*"| wc -l)
noexcep=$(find sdcs -name "carol_fi_inj_bench_output*"| wc -l)
cd sdcs
masked=$(grep -R PASS| grep carol| wc -l)
sdcs=$(grep -R FAIL| grep carol| wc -l)
crash_nodoc=$[ $noexcep - $masked - $sdcs]
crash=$[ $crash + $crash_nodoc ]
echo $1";"$fi";"$crash";"$crash_nodoc";"$hangs";"$noexcep";"$masked";"$sdcs
