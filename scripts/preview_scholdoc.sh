#!/bin/zsh 

FILE=$1
PD=${scholdoc:-$2}
# CITEPROC=${SCHOLDOC_CITE:-$2}

OUTPUT="${FILE:r}.html" 
OUTPUT_DOC="${FILE:r}.docx" 
FILEDIR="$(dirname ${FILE})" 

LOG="/tmp/preview_scholdoc.log"

echo "" > $LOG 
echo "PD: '$PD'"                              >> $LOG 
echo "FILE: '$FILE'"                          >> $LOG 
echo "OUTPUT: '$OUTPUT'"                      >> $LOG 
echo "SCILAB: '$SCILAB'"                      >> $LOG 
echo "SCILAB: <base href='file://${TM_FILEPATH// /%20}'>" >> $LOG 

# cat $LOG | perl -pe 's/\n/<br>\n/'
USERCSS=`perl -ne 'print "$1" if /^css-theme:\s*(.+\.css)\s*$/' < ${FILE}`
BIB=`perl -ne 'print "$1" if /^bibliography:\s*(.+?)\s*$/' < ${FILE}`

echo "USERCSS: '$USERCSS'" >> $LOG 

CSSTHEME=${USERCSS:-scholmd-heuristically-latest.min.css}
CSS="$SCILAB/scripts/css/${CSSTHEME}"
# CSS="$SCILAB/scripts/css/scholdoc-style.css"
# CSS_REF="file://${CSS// /%20}"

echo CSS: $CSS
echo CSS_REF: $CSS_REF
echo '<br>'

# cat - > /tmp/run_pandoc.input.txt
echo "CSS_REF: $CSS_REF" >> /tmp/preview_scholdoc.log 

$PD \
	# --css="$CSS_REF" \
	-H pandoc.css
	# -w docx -o "$OUTPUT_DOC" \
	-w html5 -s -S -o $OUTPUT < "$FILE" \
	# --citeproc --bibliography="${FILEDIR}/${BIB}" \
		2>&1 > /tmp/preview_scholdoc.log 
		
cat $OUTPUT
