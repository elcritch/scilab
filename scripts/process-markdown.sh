#!/bin/zsh 

PANDOC=${SCHOLDOC:-$HOME/.cabal/bin//scholdoc}

FILE="$1"
OUTPUT_DIR=$(basename "$FILE")
OUTPUT_NAME="${FILE:r}"

dt=$(date)
LOG="/tmp/process-markdown-$dt.log"

echo "" > "$LOG"
echo "$OUTPUT_DIR" >> "$LOG"
echo "$OUTPUT" >> "$LOG"


echo $SCHOLDOC \
	-r markdown+yaml_metadata_block+mmd_title_block+definition_lists+footnotes+table_captions+grid_tables+simple_tables \
	--css="$HOME/proj/code/scilab/css/ntm-style.css" \
	--section-divs --mathjax -w html5 -s -S "${OUTPUT_NAME}.html"


