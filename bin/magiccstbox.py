from __future__ import print_function
from acomms import CycleStats, CycleStatsList, Message
import dateutil.parser
import datetime
from collections import namedtuple
import scipy.io
import numpy
import glob
import pickle
import argparse
import csv
import operator
import plotter

CstParseResult = namedtuple('CstParseResult', 'cst_list line_count error_count')

def _bareprint(text):
    print(text, sep='', end='')
   
def get_csts_from_log_file(log_filename, console_progress=False, drop_packet_timeout=True):
    """ Get a CycleStatsList containing the data from all the CACST messages in 
    the specified log file.
    
    This function attempt to deal with multiple log file formats and do the
    "right thing".  If the log file contains pre-version-6 CST messages that
    don't include a full date, it will try to get the date/time from the log
    file timestamp instead.
    
    If console_progress is set, this function will print progress information to
    the console.
    
    Returns a named tuple with the CycleStatsList, the number of lines
    processed, and the number of lines where a parsing error occurred.
    """
    
    line_count = 0
    error_count = 0
    cst_list = CycleStatsList()
    
    if console_progress:
        _bareprint("Parsing {}...".format(log_filename))
                   
    with open(log_filename, 'r') as logfile:
        for line in logfile:
            line_count += 1
            
            if console_progress:
                if (line_count % 1000 == 0):
                    _bareprint(".")
                    
            dollar_pos = line.find("$CACST")
            # str.find returns -1 if the substring was not found
            if dollar_pos >= 0:
                try:
                    # look for a date in the first part of the string
                    # We start removing (hopefully garbage) characters
                    for remove_idx in range(dollar_pos):
                        try:
                            line_timestamp = dateutil.parser.parse(line[:(dollar_pos-remove_idx)], fuzzy=True)
                            break
                        except ValueError:
                            continue
                    msg = Message(line[dollar_pos:])
                    cst = CycleStats.from_nmea_msg(msg, log_datetime=line_timestamp, drop_packet_timeout=drop_packet_timeout)
                    # For now, drop packet timeouts
                    if cst.mode != 2:
                        cst_list.append(cst)
                except:
                    # We should do something, but we won't.
                    error_count += 1
    
    if console_progress:
        print("Done.\n  Processed {} lines, parsed {} CSTs, encountered {} errors.".format(line_count, len(cst_list), error_count))
    
    return CstParseResult(cst_list, line_count, error_count)

def get_csts_from_log_files(log_filename_list, console_progress=False, drop_packet_timeout=True):
    """ Get a CycleStatsList containing the data from all the CACST messages in 
    the specified log files.
    
    This function attempt to deal with multiple log file formats and do the
    "right thing".  If the log file contains pre-version-6 CST messages that
    don't include a full date, it will try to get the date/time from the log
    file timestamp instead.
    
    If console_progress is set, this function will print progress information to
    the console.
    
    Returns a named tuple with the CycleStatsList, the total number of lines
    processed, and the total number of lines where a parsing error occurred.
    """
    
    total_line_count = 0
    total_error_count = 0
    all_csts_list = CycleStatsList()
    
    for filename in log_filename_list:
        cst_list, line_count, error_count = get_csts_from_log_file(filename, console_progress)
        all_csts_list.extend(cst_list)
        total_error_count += error_count
        total_line_count += line_count
    
    if console_progress:    
        print("Processed {} files, {} total lines, {} total CSTs, {} parsing errors.".format(
            len(log_filename_list), total_line_count, len(all_csts_list), total_error_count))
      
    return CstParseResult(all_csts_list, total_line_count, total_error_count)


def save_matlab_from_csts(mat_file_name, cst_list, variable_name="csts"):
    cst_dict_of_lists = cst_list.to_dict_of_lists()
    # We can't save a normal datetime to a MAT file, so we have to convert
    # it to a numpy datetime64.
    cst_dict_of_lists['toa'] = [numpy.datetime64(toa) for toa in cst_dict_of_lists['toa']]
    
    scipy.io.savemat(mat_file_name, mdict={variable_name: cst_dict_of_lists}, oned_as='row')
    
def save_pickle_from_csts(pickle_file_name, cst_list, pickle_protocol=2):
    with open(pickle_file_name, 'wb') as picklefile:
        pickle.dump(cst_list, picklefile, protocol=pickle_protocol)
        
def save_csv_from_csts(csv_file_name, cst_list, write_header=True):
    # "If csvfile is a file object, it must be opened with the b flag on platforms where that makes a difference."
    with open(csv_file_name, 'wb') as csvfile:
        dw = csv.DictWriter(csvfile, CycleStats.fields, extrasaction='ignore')
        if write_header:
            dw.writeheader()
        dw.writerows(cst_list)
        
def load_csts_from_pickle(pickle_file_name):
    with open(pickle_file_name, 'rb') as picklefile:
        cst_list = pickle.load(picklefile)
        return cst_list

def print_csts_to_console(cst_list):
    # This is probably a bad idea.
    for cst in cst_list:
        print(cst)
    

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Magically transform CST messages into something useful.')
    ap.add_argument("-m", "--matfile", help="Save Matlab .MAT file with specified name")
    ap.add_argument("-k", "--pickle", help="Save Python pickle file with specified name")
    ap.add_argument("-c", "--csv", help="Save csv file with specified name")
    ap.add_argument("-p", "--console", action='store_true', help="Print human-readable CST values to console")
    ap.add_argument("-g", "--gui", action='store_true', help="Plot CSTs in interactive GUI (experimental)")
    ap.add_argument("-l", "--load", action='store_true', help="Load CSTs from pickle file instead of parsing log files")
    ap.add_argument("--silent", action='store_true', help="Don't print progress messages")
    ap.add_argument("--sort", default="oldfirst", choices=["none", "oldfirst", "newfirst"], help="Sort the CSTs by time in the specified direction prior to generating output. Default is 'oldfirst'.")
    ap.add_argument("log_filenames", nargs='+', help="File name(s) of log files to process.  Wildcards are OK.")
    
    args = ap.parse_args()
    
    filename_list = []
    for filename in args.log_filenames:
        filename_list.extend(glob.glob(filename))
        
    show_progress = not args.silent
    
    # First, try to parse the files we were given.
    if args.load:
        if show_progress:
            _bareprint("Loading CSTs from {}...".format(filename_list[0]))
        cst_list = load_csts_from_pickle(filename_list[0])
        if show_progress:
            print("Done.")
    else:
        cst_list = get_csts_from_log_files(filename_list, console_progress=show_progress)[0]
    
    if args.sort is not "none":
        if args.sort is "oldfirst":
            reverse = False
        else:
            reverse = True
        cst_list.sort(key=operator.itemgetter('toa'), reverse=reverse)
       
    # Now, choose what to do.
    if args.console:
        print_csts_to_console(cst_list)
    
    if args.matfile:
        if show_progress:
            _bareprint("Writing Matlab MAT file to {}...".format(args.matfile))
        save_matlab_from_csts(args.matfile, cst_list)
        if show_progress:
            print("Done.")
    
    if args.pickle:
        if show_progress:
            _bareprint("Writing pickle file to {}...".format(args.pickle))
        save_pickle_from_csts(args.pickle, cst_list)
        if show_progress:
            print("Done.")
        
    if args.csv:
        if show_progress:
            _bareprint("Writing CSV file to {}...".format(args.csv))
        save_csv_from_csts(args.csv, cst_list)
        if show_progress:
            print("Done.")
    
    if args.gui:
        print("Starting Magic CST GUI (this may take a moment)...")
        plotter.plot_csts(cst_list)

    

        
        
