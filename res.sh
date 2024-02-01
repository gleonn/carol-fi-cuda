    cab="Experimento"
    for j in "fault_successful" "Model" "hang(%)" "crash(%)" "masked(%)" "sdc(%)" "Hang-restart-fi" "Registros"
          do
          cab=$(echo $cab";"$j)

          done
  echo $cab > $1/resumen_total.csv

for i in $(ls $1 | grep  -v -E resumen_* )
do
	echo "res-new-ind.sh" $1/$i  ">" $1"/resumen_"$i
	
	./res-ind.sh $1/$i  > $1/resumen_$i
        row=$(echo $i)
        for j in "fault_successful" "Model" "hang(%)" "crash(%)" "masked(%)" "sdc(%)" "Hang-restart-fi" "Registros"
          do
          campo=$(grep $j $1/resumen_$i|cut -d= -f2|head -1)
          row=$(echo $row";"$campo)
          done
     
       echo $row >> $1/resumen_total.csv  

done	
