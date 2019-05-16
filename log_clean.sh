#!/usr/bin/env sh

# SPDX-License-Identifier: MIT
# Copyright (C) 2018-2019 Bytemare <d@bytema.re>. All Rights Reserved.

# Cleans log files.
# For all log files in the current directory, reformat
# log entries that span on multiple lines, which sometimes
# break parsers. Result is written in different file.


target_file= $1

newline_delimiter="\n"

log_ext=".log"
new_file_extension=".clean"

for fic in `ls *${log_ext}`
do
    s=@fic.string
    strings ${fic} > ${s}
    res=${fic}${new_file_extension}
    awk 'BEGIN {accum_line = "";} /^</{if(length(accum_line)){print accum_line; accum_line = "";}} {accum_line = accum_line "" $0;} END {if(length(accum_line)){print accum_line; }}' ${s} > ${new_file_extension}
    rm ${s} ${fic}
done