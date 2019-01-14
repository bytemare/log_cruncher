# log_cruncher
Reduce big log volumes for better analysis / log correlation.

During a security audit, I needed to identify how my traffic (DoS, and fuzzing, typically) was impacting the network, the target instances, and how it may trigger the firewalls and SIEM.
The network had high band traffic with tons of Gigabytes of logs a day. I had access to log files. What I wanted, was to see if my malicious traffic behaved differently from normal traffic, and if it triggered different logging calls.
I did that by profiling normal and malicious behaviour, and comparing the difference.

## Profiling
In order to do that, I wanted to know how "normal" behaviour translates into logs, and then compare it to when when I was operating my attacks on the network. I would then see what difference they made.
So, for a given target, I created a "profile", a log file containing "typical log lines". Collecting logs during my attacks, and applying the same profiling technique on this set, would give me new log lines that were not encountered before.

[The Levenshtein distance](https://en.wikipedia.org/wiki/Levenshtein_distance "Levenshtein distance") is used (when available) to reduce the number of lines that are redundant to a certain ratio. Several log lines may be very similar but only differ in datetime or non-interesting values. Only one typical log line of this type is kept. **The sensitivity can be set as correllation threshold of values between 0 and 1.**

## Computing
I had limited ressources at my disposal. Hundreds of GB of logs per target, the disk i/o would take hours, and I couldn't load everything in RAM and analyse them there.
A fast solution I saw was to dispatch analysis of files to different threads, who would send a temporary result to a writer thread saving results on disk, a fair memory-disk tradeoff.

Basic CPython is pretty bad in multi-threading, thus a pool of process workers are used, to correctly leverage the potential of available cores.

Depending on the machine, crunching 80 GB of log files to some files of some dozen of lines each can take a few hours.

## Use
1. Your log files may be broken by having log entries span over several lines, thus breaking the parser. Use the shell script **log_clean.sh** in a directory to reassemble these entries back into one line.
2. Modify the parameters in the python script to your need. Some variables may seem redundant to you, but allow different use cases.
3. Be sure to lower cpu load, you even may give the process an higher priority.
4. Launch the script on log files you want to profile : the more input, the better the profile.
5. Operate steps 1 to 4 on a subset of logs extracted during the attack.
6. Compare the two results.
