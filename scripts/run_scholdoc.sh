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


echo "LOG: $LOG"

echo "" > $LOG
echo "PD: '$PD'"                              | tee $LOG
echo "FILE: '$FILE'"                          | tee $LOG
echo "HTML: '$HTML'"                          | tee $LOG
echo "SCILAB: '$SCILAB'"                      | tee $LOG

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

echo "USERCSS: '$USERCSS'" | tee $LOG

CSSTHEME=${USERCSS:-scholmd-heuristically-latest.min.css}
CSS="$SCILAB/scripts/css/${CSSTHEME}"
CSS_REF="file://${CSS// /%20}"
CSS_INCL_FILE=$(mktemp -t temp)

echo "CSS: $CSS" | tee $LOG
echo "CSS_REF: $CSS_REF" | tee $LOG
echo "CSS_INCL_FILE: $CSS_INCL_FILE" | tee $LOG

cat "$CSS" | perl -pe 'BEGIN{print "<style type=\"text/css\">"};END{print "</style>"}' > $CSS_INCL_FILE


echo DIRN: $DIRN
cd "$DIRN"
echo PWD: $(pwd)

$PD \
	-r markdown+yaml_metadata_block+mmd_title_block+definition_lists+footnotes+table_captions+grid_tables+simple_tables \
	-H $CSS_INCL_FILE \
	--self-contained \
	--mathml \
	--section-divs --mathjax -w html5 -s -S "${FILE}" > "${HTML}"

PD_STATUS=$?

if [ $PD_STATUS -eq 0 ]
then
  echo "Successfully created processed md file: <br>"
else
  echo "Error processing md file: `$HTML`"
  exit $PD_STATUS
fi

if [ ! -z $DOPDF ]; then
   echo "No pdf. Exiting<br>"
	exit $[$PD_STATUS + 0]
fi;


echo '<h2>ENV:</h2><pre>'
cat $LOG | perl -pe 's/\n/<br>/'
echo '</pre>'

echo "HTML: $HTML" | tee $LOG
echo "PDFs: $PDF" | tee $LOG


echo '<h2>wkhtmltopdf:</h2><pre>'
wkhtmltopdf  \
				--print-media-type \
	          --page-size letter \
	          --header-right '[page]/[toPage]' \
				 --margin-top 2cm --margin-bottom 2cm \
	          --header-spacing 3 \
	          "${HTML}" "${PDF}" \
            2>&1 | perl -pe 's/\n/\n<br>/'

                       # --header-left "${BASE}" \
                       # --header-line \

HTML_STATUS=$?

echo '</pre>'


if [ $HTML_STATUS -ne 0 ]
then
  echo "Error processing pdf from html file: $PDF"
  exit $HTML_STATUS
fi


exit $[$PD_STATUS + $HTML_STATUS]
