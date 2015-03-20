#!/bin/zsh 

PD=${SCHOLDOC:-$2}

FILE="$1"
OUTPUT_DIR=$(basename "$FILE")
OUTPUT_NAME="${FILE:r}"

dt=$(date)
LOG="/tmp/process-markdown-$dt.log"

echo "PD: $PD"                              > "$LOG"
echo "OUTPUT_DIR: $OUTPUT_DIR: $OUTPUT_DIR" >> "$LOG"
echo "OUTPUT: $OUTPUT"                      >> "$LOG"

$PD \
	-r markdown+yaml_metadata_block+mmd_title_block+definition_lists+footnotes+table_captions+grid_tables+simple_tables \
	--css="$HOME/proj/code/scilab/css/ntm-style.css" \
	--section-divs --mathjax -w html5 -s -S "${FILE}" > "${OUTPUT_NAME}.html"

echo "Generated html5... "

wkhtmltopdf --print-media-type --page-size letter "${OUTPUT_NAME}.html" "${OUTPUT_NAME}.pdf"

