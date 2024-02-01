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
echo "Program;fallos-injeccion;Crash;(Crash especiales);Hang; Sin excepciones;SDC; Masked"> ../results.csv
echo $1";"$fi";"$crash";"$crash_nodoc";"$hangs";"$noexcep";"$sdcs";"$masked >> ../results.csv
echo "Program="$1
echo "Fallos-injeccion="$fi
echo "Crash="$crash
echo "Noexcep="$noexec"            No ha habido ningun excepcion, incluido masked y sdc"
echo "Crash especiales="$crash_nodoc"     noexcep-masked-sdcs, estan incluidos en crash"
echo "Hangs="$hangs
echo "SDC="$sdcs
echo "Masked="$masked

