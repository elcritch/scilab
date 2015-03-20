#!/bin/zsh 

PD=${PANDOC:-$1}

OUTPUT_DIR="${MARKED_ORIGIN}"
OUTPUT="${MARKED_PATH:r}.html"

echo "" > /tmp/run_pandoc.log 
echo "PD: $PD"                              >> /tmp/run_pandoc.log 
echo "OUTPUT_DIR: $OUTPUT_DIR"              >> /tmp/run_pandoc.log 
echo "OUTPUT: $OUTPUT"                      >> /tmp/run_pandoc.log 

# cat - > /tmp/run_pandoc.input.txt

cat - | $PD \
	-r markdown+yaml_metadata_block+mmd_title_block+definition_lists+footnotes+table_captions+grid_tables+simple_tables \
	--section-divs --mathjax -w html5 -s -S > $OUTPUT 

cat $OUTPUT
