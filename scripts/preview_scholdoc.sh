#!/bin/zsh 

FILE=$1
PD=${scholdoc:-$2}
# CITEPROC=${SCHOLDOC_CITE:-$2}
DOPDF=${0:-$3}

STEM="${FILE:r}"
BASE="$(basename $FILE)"
DIRN="$(dirname $FILE)"
HTML="${STEM}.html"
PDF="${STEM}.pdf"
SCRIPT_NAME="$(basename $0)"
SCILAB=${SCILAB:-$HOME/proj/code/scilab/}
LOG="/tmp/script-${SCRIPT_NAME}.log"


# echo "LOG: $LOG"

echo "" > $LOG
echo "PD: '$PD'"                              > $LOG
echo "FILE: '$FILE'"                          > $LOG
echo "HTML: '$HTML'"                          > $LOG
echo "SCILAB: '$SCILAB'"                      > $LOG

if [ ! -e $FILE  ]; then
  echo "Error no input file in args: " $*
  exit 126
fi

if [ ! -e $SCILAB  ]; then
  echo "Error no SCILAB directory: $HTML"
  exit 127
fi

# cat $LOG| perl -pe 's/\n/<br>\n/'
USERCSS=`perl -ne 'print "$1" if /^css-theme:\s*(.+\.css)\s*$/' < ${FILE}`
BIB=`perl -ne 'print "$1" if /^bibliography:\s*(.+?)\s*$/' < ${FILE}`

echo "USERCSS: '$USERCSS'" > $LOG

CSSTHEME=${USERCSS:-scholmd-heuristically-latest.min.css}
CSS="$SCILAB/scripts/css/${CSSTHEME}"
CSS_REF="file://${CSS// /%20}"
CSS_INCL_FILE=$(mktemp -t temp)

echo "CSS: $CSS" > $LOG
echo "CSS_REF: $CSS_REF" > $LOG
echo "CSS_INCL_FILE: $CSS_INCL_FILE" > $LOG

cat "$CSS" | perl -pe 'BEGIN{print "<style type=\"text/css\">"};END{print "</style>"}' > $CSS_INCL_FILE


echo DIRN: $DIRN > $LOG 
cd "$DIRN" 
echo PWD: $(pwd) > $LOG

$PD \
	-r markdown+yaml_metadata_block+mmd_title_block+definition_lists+footnotes+table_captions+grid_tables+simple_tables \
	-H $CSS_INCL_FILE \
	--self-contained \
	--mathml \
	--section-divs --mathjax -w html5 -s -S "${FILE}" > "${HTML}"

PD_STATUS=$?
		
cat ${HTML}


