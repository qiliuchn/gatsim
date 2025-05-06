# utils.py
import csv
from datetime import datetime
import os
import numpy
import shutil, errno
from os import listdir
import json
import re
import textwrap

def pretty_print(text, num_indent=0):
    """ 
    Print with margin.
    
    Args:
        text: text to print
        num_indent: number of indents to add to the text
    
    Returns:
        None
    """
    text = str(text)  # Convert to string if necessary
    single_indent = "    "  # default: 4 spaces
    indented_text = textwrap.fill(text, width=120, initial_indent=single_indent * num_indent, subsequent_indent=single_indent * num_indent)
    print(indented_text)
    
def parse_command(command: str) -> int:
    """ 
    Parse the command to get the duration of the simulation.
    
    Args:
        command: string that contains the command, e.g. 'run 1 day', 'run 8 hours'; default: 'run 1 day'
        
    Returns:
        duration of the simulation in minutes (int)
    """
    # Default duration
    if not command.strip():
        return 24 * 60  # Default: 1 day = 1440 minutes

    # Regex pattern: e.g., "run 2 days", "run 8 hours", "run 30 minutes"
    match = re.search(r'run\s+(\d+)\s*(day|days|hour|hours|minute|minutes)', command.lower())
    if not match:
        print("Invalid input format. Defaulting to 1 day.")
        return 24 * 60

    number = int(match.group(1))
    unit = match.group(2)

    if 'day' in unit:
        return number * 24 * 60
    elif 'hour' in unit:
        return number * 60
    elif 'minute' in unit:
        return number
    else:
        return 24 * 60  # fallback
    
    

def clean_folder(folder_path):
    """ 
    Clean a folder by deleting all files and folders inside it.
    """
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # Remove file or symbolic link
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # Remove directory and its contents
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')    


    
def convert_time_scope_str_to_datetime(curr_datetime, time_span):
    """ 
    Convert a time span str like 11:00-13:00 to a list of datetime objects
    
    Args:
        curr_datetime: datetime object that is used to determine the year, month, day
        time_str: string that contains the time
        
    Returns:
        a list of datetime objects
    """
    start, end = time_span.split("-")
    start = datetime.strptime(start, "%H:%M").time()
    end = datetime.strptime(end, "%H:%M").time()
    start_obj = curr_datetime.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
    end_obj = curr_datetime.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    ans = [start_obj, end_obj]
    return ans

def convert_time_str_to_datetime(curr_datetime, time_str):
    """ 
    Convert a time string to a datetime object
    
    Args:
        curr_datetime: datetime object that is used to determine the year, month, day
        time_str: string that contains the time
        
    Returns:
        datetime object
    """
    time_converted = datetime.strptime(time_str, "%H:%M").time()
    ans = curr_datetime.replace(hour=time_converted.hour, minute=time_converted.minute, second=0, microsecond=0)
    return ans

def extract_json_from_string(s):
    """ 
    This regex finds the first JSON object in the string
    
    Args:
        s: string that contains the dictionary
        
    Returns:
        a dict
        
    Example:
        '```json\n{"output": "3"}\n```' -> {'output': '3'}
    """
    match = re.search(r'\{.*?\}', s, re.DOTALL)
    if match:
        json_str = match.group(0)
        return json.loads(json_str)
    else:
        raise ValueError("No JSON object found in the string.")
            

def create_folder_if_not_there(curr_path): 
    """
    Checks if a folder in the curr_path exists. If it does not exist, creates
    the folder. 
    Note that if the curr_path designates a file location, it will operate on 
    the folder that contains the file. But the function also works even if the 
    path designates to just a folder. 
    Args:
        curr_list: list to write. The list comes in the following form:
                             [['key1', 'val1-1', 'val1-2'...],
                                ['key2', 'val2-1', 'val2-2'...],]
        outfile: name of the csv file to write    
    RETURNS: 
        True: if a new folder is created
        False: if a new folder is not created
    """
    outfolder_name = curr_path.split("/")
    if len(outfolder_name) != 1: 
        # This checks if the curr path is a file or a folder. 
        if "." in outfolder_name[-1]: 
            outfolder_name = outfolder_name[:-1]

        outfolder_name = "/".join(outfolder_name)
        if not os.path.exists(outfolder_name):
            os.makedirs(outfolder_name)
            return True

    return False 


def write_list_of_list_to_csv(curr_list_of_list, outfile):
    """
    Writes a list of list to csv. 
    Unlike write_list_to_csv_line, it writes the entire csv in one shot. 
    ARGS:
        curr_list_of_list: list to write. The list comes in the following form:
                             [['key1', 'val1-1', 'val1-2'...],
                                ['key2', 'val2-1', 'val2-2'...],]
        outfile: name of the csv file to write    
    RETURNS: 
        None
    """
    create_folder_if_not_there(outfile)
    with open(outfile, "w") as f:
        writer = csv.writer(f)
        writer.writerows(curr_list_of_list)


def write_list_to_csv_line(line_list, outfile): 
    """
    Writes one line to a csv file.
    Unlike write_list_of_list_to_csv, this opens an existing outfile and then 
    appends a line to that file. 
    This also works if the file does not exist already. 
    ARGS:
        curr_list: list to write. The list comes in the following form:
                             ['key1', 'val1-1', 'val1-2'...]
                             Importantly, this is NOT a list of list. 
        outfile: name of the csv file to write   
    RETURNS: 
        None
    """
    create_folder_if_not_there(outfile)

    # Opening the file first so we can write incrementally as we progress
    curr_file = open(outfile, 'a',)
    csvfile_1 = csv.writer(curr_file)
    csvfile_1.writerow(line_list)
    curr_file.close()


def read_file_to_list(curr_file, header=False, strip_trail=True): 
    """
    Reads in a csv file to a list of list. If header is True, it returns a 
    tuple with (header row, all rows)
    ARGS:
        curr_file: path to the current csv file. 
    RETURNS: 
        List of list where the component lists are the rows of the file. 
    """
    if not header: 
        analysis_list = []
        with open(curr_file) as f_analysis_file: 
            data_reader = csv.reader(f_analysis_file, delimiter=",")
            for count, row in enumerate(data_reader): 
                if strip_trail: 
                    row = [i.strip() for i in row]
                analysis_list += [row]
        return analysis_list
    else: 
        analysis_list = []
        with open(curr_file) as f_analysis_file: 
            data_reader = csv.reader(f_analysis_file, delimiter=",")
            for count, row in enumerate(data_reader): 
                if strip_trail: 
                    row = [i.strip() for i in row]
                analysis_list += [row]
        return analysis_list[0], analysis_list[1:]


def read_file_to_set(curr_file, col=0): 
    """
    Reads in a "single column" of a csv file to a set. 
    ARGS:
        curr_file: path to the current csv file. 
    RETURNS: 
        Set with all items in a single column of a csv file. 
    """
    analysis_set = set()
    with open(curr_file) as f_analysis_file: 
        data_reader = csv.reader(f_analysis_file, delimiter=",")
        for count, row in enumerate(data_reader): 
            analysis_set.add(row[col])
    return analysis_set


def get_row_len(curr_file): 
    """
    Get the number of rows in a csv file 
    ARGS:
        curr_file: path to the current csv file. 
    RETURNS: 
        The number of rows
        False if the file does not exist
    """
    try: 
        analysis_set = set()
        with open(curr_file) as f_analysis_file: 
            data_reader = csv.reader(f_analysis_file, delimiter=",")
            for count, row in enumerate(data_reader): 
                analysis_set.add(row[0])
        return len(analysis_set)
    except: 
        return False


def check_if_file_exists(curr_file): 
    """
    Checks if a file exists
    ARGS:
        curr_file: path to the current csv file. 
    RETURNS: 
        True if the file exists
        False if the file does not exist
    """
    try: 
        with open(curr_file) as f_analysis_file: pass
        return True
    except: 
        return False


def find_filenames(path_to_dir, suffix=".csv"):
    """
    Given a directory, find all files that ends with the provided suffix and 
    returns their paths.  
    ARGS:
        path_to_dir: Path to the current directory 
        suffix: The target suffix.
    RETURNS: 
        A list of paths to all files in the directory. 
    """
    filenames = listdir(path_to_dir)
    return [ path_to_dir+"/"+filename 
                     for filename in filenames if filename.endswith( suffix ) ]


def average(list_of_val): 
    """
    Finds the average of the numbers in a list.
    ARGS:
        list_of_val: a list of numeric values  
    RETURNS: 
        The average of the values
    """
    return sum(list_of_val)/float(len(list_of_val))


def std(list_of_val): 
    """
    Finds the std of the numbers in a list.
    ARGS:
        list_of_val: a list of numeric values  
    RETURNS: 
        The std of the values
    """
    std = numpy.std(list_of_val)
    return std


def copyanything(src, dst):
    """
    Copy over everything in the src folder to dst folder. 
    ARGS:
        src: address of the source folder  
        dst: address of the destination folder  
    RETURNS: 
        None
    """
    try:
        shutil.copytree(src, dst)
    except OSError as exc: # python >2.5
        if exc.errno in (errno.ENOTDIR, errno.EINVAL):
            shutil.copy(src, dst)
        else: raise


if __name__ == '__main__':
    pass
















