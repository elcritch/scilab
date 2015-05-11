#!/bin/zsh 

FILE=$1
PD=${SCHOLDOC:-$2}

SD_SCRIPT="$(dirname $0)/preview_scholdoc.sh"


STEM="${FILE:r}"
BASE="$(basename $FILE)"
HTML="${STEM}.html"
PDF="${STEM}.pdf"
DEFMARGINS="--margin-top 2cm --margin-left 2cm --margin-right 2cm --margin-bottom 2cm "
DOCMARGINS=`perl -ne 'print "$1" if /^css-print-margins:\s*(.+)\s*$/' < ${FILE}`
_MARGINS=[${DOCMARGINS:-"$DEFMARGINS"}]
# MARGINS=(${(@s/ /)MARGINS})
MARGINS=${(@s/ /)_MARGINS}

echo "" > /tmp/process_scholdoc.log 
echo "STEM: '$STEM'"                      >> /tmp/process_scholdoc.log 
echo "BASE: '$BASE'"                      >> /tmp/process_scholdoc.log 
echo "HTML: '$HTML'"                      >> /tmp/process_scholdoc.log 
echo "PDF:  '$PDF'"                       >> /tmp/process_scholdoc.log 
echo "\$0:  '$0'"                         >> /tmp/process_scholdoc.log 
echo "SD_SCRIPT: '$SD_SCRIPT'"            >> /tmp/process_scholdoc.log 
echo "MARGINS: '$MARGINS'"                >> /tmp/process_scholdoc.log 

zsh $SD_SCRIPT "$1" "$2" 1> /dev/null 2>> /tmp/process_scholdoc.log  

echo '<h1>Scholdoc</h1>'

echo '<h2>ENV:</h2><pre>'
cat /tmp/process_scholdoc.log | perl -pe 's/\n/<br>/'
echo '</pre>'


echo '<h2>wkhtmltopdf:</h2><pre>'
wkhtmltopdf --print-media-type \
				--page-size letter \
				--header-right '[page]/[toPage]' \
				$MARGINS \
				--header-spacing 2 \
				"${HTML}" "${PDF}" \
					| perl -pe 's/\n/<br>/' 2>&1 

			# --header-left "${BASE}" \
			# --header-line \
echo '</pre>'


