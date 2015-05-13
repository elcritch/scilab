#!/bin/zsh 

FILE=$1

STEM="${FILE:r}"
BASE="$(basename $FILE)"
HTML="${STEM}.html"
PDF="${STEM}.pdf"
SD_SCRIPT="$(dirname $0)/run_scholdoc.sh"

LOG="/tmp/process_scholdoc.log"

DEFMARGINS="--margin-top 2cm --margin-left 2cm --margin-right 2cm --margin-bottom 2cm "
DOCMARGINS=`perl -ne 'print "$1" if /^css-print-margins:\s*(.+)\s*$/' < ${FILE}`
_MARGINS=[${DOCMARGINS:-"$DEFMARGINS"}]
# MARGINS=(${(@s/ /)MARGINS})
MARGINS=${(@s/ /)_MARGINS}


echo "" > $LOG 
echo "STEM: '$STEM'"                      >> $LOG 
echo "BASE: '$BASE'"                      >> $LOG 
echo "HTML: '$HTML'"                      >> $LOG 
echo "PDF:  '$PDF'"                       >> $LOG 
echo "\$0:  '$0'"                         >> $LOG 
echo "SD_SCRIPT: '$SD_SCRIPT'"            >> $LOG 


zsh $SD_SCRIPT $*  1>> /dev/null 2>> $LOG 

SD_STATUS=$?

if [ $SD_STATUS -eq 0 ]
then
  echo "Successfully created processed md file: $HTML"
else
  echo "Error processing md file"
  exit $SD_STATUS
fi



open "$PDF"

exit $STATUS

