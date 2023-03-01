import os
import json

def check_dir(dir):
    if not os.path.isdir(dir):
        os.mkdir(dir)
    return(dir)

def check_file(file):
    if not os.path.isfile(file):
        with open(file, 'w') as fp:
            json.dump(list(), fp)
    return file

def get_calendar(calendar, start, end):
    start_idx = calendar.searchsorted(start)
    end_idx = calendar.searchsorted(end)
    return calendar[start_idx:end_idx+1]