#!/usr/bin/env bash
set -Eeuo pipefail

# Taken from https://gist.github.com/gilcreque/649485
# and reworked a bit

# check to see if arguments are set
if (( $# < 1 )); then
    echo "Usage: $(basename "$0") textfilename [rtffilename optional]"
    exit 65
fi
input_file="$1"

# set output filename
if (( $# == 2 )); then
    output_file="$2"
else
    output_file="${input_file%.*}.rtf"
fi

# Set font face
# font="Courier"
font="Arial"
# font="Times New Roman"

# Set font size in pt
fontsize=9

# Set document height in inches
height=11 # letter
# height=14 # legal

# Set document width in inches
width=8.5

# set document margins in inches
leftm=0.5
rightm=0.5
topm=0.5
bottomm=0.756

##################################
#NOTHING BELOW NEEDS TO BE EDITED#
##################################

# calculate rtf sizes
fontsize=$(echo "$fontsize * 2 / 1" | bc)
height=$(echo "$height * 1440 / 1" | bc)
width=$(echo "$width * 1440 / 1" | bc)
leftm=$(echo "$leftm * 1440 / 1" | bc)
rightm=$(echo "$rightm * 1440 / 1" | bc)
topm=$(echo "$topm * 1440 / 1" | bc)
bottomm=$(echo "$bottomm * 1440 / 1" | bc)

{
    # start header
    printf "%s" "{\rtf1\ansi\deff0 {\fonttbl {\f0 $font;}}"
    printf "%s" "\paperh$height \paperw$width"
    printf "%s" "\margl$leftm \margr$rightm \margt$topm \margb$bottomm"
    printf "%s" "\f0\fs$fontsize"

    # add \line to the end of each line and replace an form feed characters
    # with \page for page breaks
    sed s/\$/'\\line'/ "$input_file" | sed s/\\f/'\\page'/

    # close rtf file
    echo "}"
} > "$output_file"
