#!/usr/bin/env sh

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2017-2018 Bytemare <d@bytema.re>. All Rights Reserved.

# Cleans log files.
# For all log files in the current directory, reformats
# log entries that span on multiple lines, which sometimes
# break parsers. Result is written in different file.


target_file= $1

newline_delimiter="\n"

log_ext=".log"
res_ext=".clean"

for fic in `ls *${log_ext}`
do
    s=@fic.string
    strings $fic > $s
    res=$fic$res_ext
    awk 'BEGIN {accum_line = "";} /^</{if(length(accum_line)){print accum_line; accum_line = "";}} {accum_line = accum_line "" $0;} END {if(length(accum_line)){print accum_line; }}' $s > $res
    rm $s $fic
done