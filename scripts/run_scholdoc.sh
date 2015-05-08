#!/bin/zsh 

FILE=$1
PD=${SCHOLDOC:-$2}
# CITEPROC=${SCHOLDOC_CITE:-$2}

OUTPUT="${FILE:r}.html" 
OUTPUT_DOC="${FILE:r}.docx" 
FILEDIR="$(dirname ${FILE})" 

echo "" > /tmp/run_scholdoc.log 
echo "PD: '$PD'"                              >> /tmp/run_scholdoc.log 
echo "FILE: '$FILE'"                          >> /tmp/run_scholdoc.log 
echo "OUTPUT: '$OUTPUT'"                      >> /tmp/run_scholdoc.log 
echo "SCILAB: '$SCILAB'"                      >> /tmp/run_scholdoc.log 
echo "SCILAB: <base href='file://${TM_FILEPATH// /%20}'>" >> /tmp/run_scholdoc.log 

# cat /tmp/run_scholdoc.log | perl -pe 's/\n/<br>\n/'
USERCSS=`perl -ne 'print "$1" if /^css-theme:\s*(.+\.css)\s*$/' < ${FILE}`
BIB=`perl -ne 'print "$1" if /^bibliography:\s*(.+?)\s*$/' < ${FILE}`

echo "USERCSS: '$USERCSS'" >> /tmp/run_scholdoc.log 

CSSTHEME=${USERCSS:-scholmd-heuristically-latest.min.css}
CSS="$SCILAB/scripts/css/${CSSTHEME}"
# CSS="$SCILAB/css/scholdoc-style.css"
CSS_REF="file://${CSS// /%20}"

# cat - > /tmp/run_pandoc.input.txt
echo "CSS_REF: $CSS_REF" >> /tmp/run_scholdoc.log 

$PD \
	--css="$CSS_REF" \
	-w docx -o "$OUTPUT_DOC" \
	-w html5 -s -S -o $OUTPUT < "$FILE"
	# --citeproc --bibliography="${FILEDIR}/${BIB}" \

# cat $OUTPUT
