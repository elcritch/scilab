#!/bin/zsh 

FILE=$1
PD=${SCHOLDOC:-$2}

OUTPUT="${FILE:r}.html" 
OUTPUT_DOC="${FILE:r}.docx" 

echo "" > /tmp/run_scholdoc.log 
echo "PD: '$PD'"                              >> /tmp/run_scholdoc.log 
echo "FILE: '$FILE'"                          >> /tmp/run_scholdoc.log 
echo "OUTPUT: '$OUTPUT'"                      >> /tmp/run_scholdoc.log 
echo "SCILAB: '$SCILAB'"                      >> /tmp/run_scholdoc.log 
echo "SCILAB: <base href='file://${TM_FILEPATH// /%20}'>" >> /tmp/run_scholdoc.log 

# cat /tmp/run_scholdoc.log | perl -pe 's/\n/<br>\n/'
CSS="$SCILAB/css/scholmd-heuristically-latest.min.css"
# CSS="$SCILAB/css/scholdoc-style.css"
CSS_REF="file://${CSS// /%20}"

# cat - > /tmp/run_pandoc.input.txt
echo "CSS_REF: $CSS_REF" >> /tmp/run_scholdoc.log 

$PD \
	--css="$CSS_REF" \
	-w docx -o "$OUTPUT_DOC" \
	< "$1"

cat - | $PD \
	--css="$CSS_REF" \
	-w html5 -s -S > $OUTPUT

cat $OUTPUT
