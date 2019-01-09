from multiprocessing import Process, Pool, Manager
from os import getpid, makedirs, path, cpu_count
from time import sleep
from errno import EEXIST
from threading import Thread

"""
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (C) 2017-2018 Bytemare <d@bytema.re>. All Rights Reserved.
"""

# For correlation coefficient
try:
    import Levenshtein
except ImportError:
    import difflib

import datetime
# import distance

# For nested dicts
from collections import defaultdict
# Directories
from pathlib import Path

target_dir = ["."]

# Specify directories where logs are
logs_dirs = ["/dir/1", "/dir/2"]

# Reference files to look for
logs_refs = ["log_files_1", "log_files_2"]

# Log files extension to look for
log_file_extension = ".clean"

# Create a dictionary
logs_dict = dict(zip(logs_dirs, logs_refs))

# Log Types
desired_logs = ["INF", "*WRN*", "**ERR**"]
undesired_logs = ["DBG", "TRC"]

# Token To send to writer process to stop
stop_token = "stop"

# Results
# Datetime for file dumps
date = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
# Destination folder
results_dir = "./results"

# Sensitivity of correlation purge. Must be between 0 and 1.0, with the latter meaning exact copy.
correlation_threshold = 0.8


def get_result_filename(log_reference):
    return results_dir + "/" + log_reference  # date + "_" + log_reference


def selector(log_ref, queue):
    """
    Launched by a separate process,
    Reads and inserts into database the received from queue until it receives the stop_token message
    :param log_ref:
    :param queue:
    :return:
    """

    print("Writer " + str(getpid()) + " with " + log_ref + " launched...")

    # Nested dictionary hack
    def nested_dict():
        return defaultdict(nested_dict)

    #  Populate root of nested dictionary with types of desired log types
    logs = nested_dict()
    for d in desired_logs:
        logs[d] = dict()

    cpt = 0

    # Start daemon loop
    while True:

        msg = queue.get()

        if msg == stop_token:
            break

        log_records = logs[msg[1]].get(msg[2])
        if log_records is None:
            cpt += 1
            logs[msg[1]][msg[2]] = list()
            logs[msg[1]][msg[2]].append(msg)
            # print("add " + str(msg[5]))
            continue

        for curr_inplace_log in logs[msg[1]][msg[2]]:

            log_inplace = curr_inplace_log[5]
            log_new = msg[5]

            # diffl = difflib.SequenceMatcher(None, log_inplace, log_new).ratio()
            try:
                corr = Levenshtein.ratio(log_inplace, log_new)
            except NameError:
                corr = difflib.SequenceMatcher(None, log_inplace, log_new).ratio()
            # sor = 1 - distance.sorensen(log_inplace, log_new)
            # jac = 1 - distance.jaccard(log_inplace, log_new)

            # print("For " + log_inplace + "\nand " + log_new + "\n => " + str(lev))

            if corr > correlation_threshold:
                break

        #  Yes, hacky, but does a hell of a job.
        # The break statement will quit the for loop and not enter this 'else'. But if all test of the 'if' pass,
        # then this 'else' is executed.
        # So it is really important for this else statement to be outside and juste after the for loop,
        # indented with the for.
        else:
            # print(
            #    msg[5] + "\n => " + str(lev) + " (added on list of " + str(len(logs[msg[1]][msg[2]])) + " elements ).")
            cpt += 1
            logs[msg[1]][msg[2]].append(msg)

    filename = get_result_filename(log_ref)
    print("Writer " + str(getpid()) + " got stop token, dumping " + str(cpt) + " results to file : " + filename)

    write_results(filename, logs)
    print("Writer " + str(getpid()) + " exiting.")


def write_results(filename, logs):

    with open(filename, 'w+') as log_file:
        for d in desired_logs:
            for record, record_list in logs[d].items():
                for r in record_list:
                    log_file.write(" ".join(r) + "\n")


def log_worker(filename, dest_queues):
    r = get_log_ref(filename)
    # s = ">> " + str(os.getpid()) + " for " + filename + " to " + r + " <<"

    with open(filename, 'r') as log_file:

        # print("Worker " + str(getpid()) + " : " + filename + " : open at " + str(log_file))

        try:
            cpt = 0
            for line in log_file:
                cpt += 1
                # print("Worker " + str(getpid()) + " : " + line)
                s = line.split()
                # print("Worker " + str(getpid()) + " on "+ r +" -> split : " + str(s))
                if s[1] in desired_logs:
                    sp = s[4].split(">")
                    # print("Worker " + str(getpid()) + " split > : " + str(sp))
                    s[4] = sp[0] + ">"

                    if len(s) > 5:
                        s[5] = sp[1] + "".join(s[5:])
                        s[6:] = []
                    else:
                        s.append(sp[1])

                    # print("Worker " + str(getpid()) + " sending on " + r + " : " + str(s))
                    # print("Worker " + str(os.getpid()) + " sent.")

                    dest_queues[r].put(s)
        except Exception as e:
            print("Worker " + str(getpid()) + " error : " + str(e))
            print("Worker " + str(getpid()) + " : " + line)
            s = line.split()
            print("Worker " + str(getpid()) + " on " + r + " -> split : " + str(s))
            print("Worker " + str(getpid()) + " split > : " + str(s[4].split(">")))

    dest_queues["progress"].put(str(getpid()))
    # print("Worker " + str(getpid()) + " out.")


def file_collector(target_dir, suffix_pattern=log_file_extension):
    files = []

    # print("Looking into " + directory)
    files.append(list(Path(target_dir).glob('**/*' + suffix_pattern)))
    # print("Got " + str(len(files[0])))

    print("[i] Found " + str(len(files[0])) + " files.")

    return files[0]


def get_log_ref(filename):
    s = str(filename).split('/')[-2:-1][0]

    for l in logs_dirs:
        if l in s:
            return logs_dict[l]

    print("[ERROR] Could not recognise log membership. " + str(filename))
    raise ValueError


def show_parameters():
    #  Print parameter set
    print("[i] Looking for log files ending with " + log_file_extension)
    print("[i] Folders to into are " + str(logs_dirs))
    print("[i] Folders are supposed to be here : " + target_dir[0])
    print("[i] Desired log types to look for are " + str(desired_logs))
    print("[i] Specifically don't look for " + str(undesired_logs))
    print("[i] The Levenshtein correlation threshold is " + str(correlation_threshold))

    #  Print system parameters
    print("[i] The number of processes to be launched for gathering is " + str(len(logs_refs)))
    print("[i] The number of processes to crawl through logs is " + str(cpu_count()))
    print("[i] Results will be written to " + results_dir)
    print("[i] and will be prepended with actual datetime " + date)


def progresser(progresser_queue, num_files):
    print("Progress thread ready.")
    sleep(1)

    for i in range(num_files):
        print("\r=> " + str(100*i/num_files) + "% ( " + str(i) + " / " + str(num_files) + ")\t", end="")
        if progresser_queue.get() == stop_token:
            print("\r=> " + str(100 * (i+1) / num_files) + "% ( " + str(i) + " / " + str(num_files) + ")\t", end="")
            break


if __name__ == '__main__':

    show_parameters()

    try:
        makedirs(results_dir)
    except OSError as e:
        if e.errno != EEXIST:
            raise

    for dir in logs_dirs:

        print("\n[i] Working with logs in " + dir)

        # Launch Selector Process
        manager_d = Manager()
        manager_q = Manager()

        # Create Queues to pass lines into, as many as we have reference files
        queues = manager_d.dict()
        ref = logs_dict[dir]
        queues[ref] = manager_q.Queue()
        sel = Process(target=selector, args=(ref, queues[ref], ))
        sel.start()
        print("[i] Selector process launched.")

        # Collect file list and launch Progress Thread
        progress_queue = manager_q.Queue()
        queues["progress"] = progress_queue

        files = file_collector(dir)
        p = Thread(target=progresser, args=(progress_queue, len(files),))
        p.start()

        # Launch Worker Processes
        # Dispatch jobs, Pool() with no argument calls cpu_count() to dispatch on number of processes
        workers = Pool()
        for f in files:
            # print("Job on " + str(i))
            workers.apply_async(log_worker, (str(f), queues))

        print("[i] All " + str(workers._processes) + " worker processes launched.")
        workers.close()

        # Waiting for job termination
        workers.join()

        # When workers are done, send stop signal to selector
        queues[ref].put(stop_token)

        #  Tell progress thread to stop
        progress_queue.put(stop_token)
        p.join()

        print("[i] Waiting for writer to finish.")
        sel.join()

    exit(0)
