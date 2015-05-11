#!/bin/zsh 

SD_SCRIPT="$(dirname $0)/run_scholdoc.sh"

FILE=$1
PD=${SCHOLDOC:-$2}


STEM="${FILE:r}"
BASE="$(basename $FILE)"
HTML="${STEM}.html"
PDF="${STEM}.pdf"
DEFMARGINS="--margin-top 2cm --margin-left 2cm --margin-right 2cm --margin-bottom 2cm "
DOCMARGINS=`perl -ne 'print "$1" if /^css-print-margins:\s*(.+)\s*$/' < ${FILE}`
_MARGINS=[${DOCMARGINS:-"$DEFMARGINS"}]
# MARGINS=(${(@s/ /)MARGINS})
MARGINS=${(@s/ /)_MARGINS}

zsh $SD_SCRIPT $* 1> /dev/null 2>> /tmp/process_scholdoc.log  


open "$PDF"

