#!/bin/zsh 

FILE=$1
PD=${SCHOLDOC:-$2}

STEM="${FILE:r}"
BASE="$(basename $FILE)"
HTML="${STEM}.html"
PDF="${STEM}.pdf"

./run_scholdoc.sh "$1" "$2"

wkhtmltopdf --print-media-type \
				--page-size letter \
				--header-right '[page]/[toPage]' \
				--margin-top 2cm \
				-L 0mm -R 0mm \
				--header-spacing 2 \
				"${HTML}" "${PDF}"

			# --header-left "${BASE}" \
			# --header-line \

open "$PDF"
