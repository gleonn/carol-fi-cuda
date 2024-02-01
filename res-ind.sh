#cut -d, -f 3,4,9,10,11,12,13,14,15  fi_lavaMD_single_bit_RF.csv 
./res-ind-simple.sh $1
reg=2
num_reg=0;
for i in $(seq 0 1 255)
do
ib=$(echo "R"$i)
sib=$(echo "R"$i",")
n=$(cut -f $reg -d, $1|grep -w $ib|wc -l)
if [ "$n" -gt 0 ];
then
echo $ib"="$n
num_reg=$[$num_reg + 1]
fi
done
echo "Registros usados="$num_reg
for i in $(seq 0 1 255)
do
ib=$(echo "R"$i)
sib=$(echo "R"$i",")
n=$(cut -f $reg -d, $1|grep -w $ib|wc -l)
if [ "$n" -gt 0 ];
then
echo "============"$ib"========="
head -1 $1 >filetempreg.csv
grep $sib  $1 >> filetempreg.csv
./res-ind-simple.sh filetempreg.csv
fi
done
