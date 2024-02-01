#cut -d, -f 3,4,9,10,11,12,13,14,15  fi_lavaMD_single_bit_RF.csv 

fi_field=10
model=$[$fi_field - 1]
hang=$[$fi_field + 1]
crash=$[$hang + 1]
masked=$[$crash +1 ]
sdc=$[$masked +1 ]
for i in $fi_field  $crash $sdc
do
cab=$(cut -d, -f$i $1|head -1)
trues=$(cut -d, -f$i $1|grep "True"|wc -l)
campos[$i]=$trues
echo $cab "=" ${campos[$i]}

done 
for i in $masked 
do
cab=$(cut -d, -f$i $1|head -1)
trues=$(cut -d, -f$hang,$i $1|grep "False,True"|wc -l)
echo $cab "=" $trues
campos[$i]=$trues
done
cab=$(cut -d, -f$hang $1|head -1)
trues=$(cut -d, -f$hang,$crash $1|grep "True,False"|wc -l)
echo $cab "=" $trues
campos[$hang]=$trues

for i in  $hang $crash $masked $sdc
do

tantoporcien=$(printf %.3f "$(( campos[$i] * 10**5/${campos[$fi_field]} ))e-3")
cab=$(cut -d, -f$i $1|head -1)
echo $cab"(%)="$tantoporcien
done
interrupciones=$(grep unique $1| wc -l)
interrupciones=$[ $interrupciones -1]
echo "Hang-restart-fi="$interrupciones
echo "Model="$(cut -d, -f$model $1|head -2|tail -1)
excep=$[$sdc +1]

for i in $(seq 1 1 15)
do
ib=$(echo "_"$i$)
n=$(cut -f $excep -d, $1 | sed "s/CUDA_EXCEPTION_1 CUDA_EXCEPTION_1/CUDA_EXCEPTION_1/"| sed "s/SIGKILL CUDA_EXCEPTION//"|grep $ib | wc -l )
if [ "$n" -gt 0 ];
then
echo "CUDA_EXCEPTION_"$i"="$n 
fi
done

