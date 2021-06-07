#!/usr/bin/env python
"""
**************************************************************************
**                                                                      **
** Python Script to hash files and strings on the windwos command line  **
**                                                                      **
** History:                                                             **
** May 21	    github.com/brtwrst    V1.0                              **
**************************************************************************
"""
import hashlib
import argparse
import os
import sys


def progressbar(
    progress,
    prefix='Progress',
    suffix='',
    decimals=0,
    length=50,
    style='| =',
):
    """
    Call in a loop to create terminal progress bar
    @params:
        progress    - Required  : current progress between 0 - 1 (Float)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : number of decimals in percent complete (Int)
        length      - Optional  : length of bar (Int)
        fill        - Optional  : bar characters (Str)
    """
    if not 0 <= progress <= 1:
        return False
    numfilled = int(progress * length)
    bar = ''.join([style[0],
                   style[2] * numfilled,
                   style[1] * (length - numfilled),
                   style[0],
                   ])
    percent = f'{100*progress:.{decimals}f}'
    print(f'{prefix+" " if prefix else ""}{bar} {percent}% {suffix}', end='\r', flush=True)
    if progress == 1:
        print(' '*(len(prefix) + 10 + length + len(suffix)), end='\r', flush=True)


def get_args():
    """
    factory function for argparse
    """
    parser = argparse.ArgumentParser(description='Simple hashing script.')
    parser.add_argument("target",
                        help='Files/Strings to hash. use * to hash all files in current folder'
                        + ' For string mode use: "pyhash -s". Quote Strings that include spaces',
                        default=[],
                        nargs='*')
    parser.add_argument("-l", "--list-algorithms",
                        help="List all available hashing algorithms and exit",
                        action='version',
                        version=str(sorted(hashlib.algorithms_guaranteed)))
    parser.add_argument("-a", "--algorithms",
                        help="Algorithm(s) to use. Default: md5 sha1 sha256."
                        + " Supports multiple selections. eg -a sha1 md5 ."
                        + " Supports Groups: all, sha, sha3, blake, shake.",
                        default=['md5', 'sha1', 'sha256'],
                        nargs='+')
    parser.add_argument("-p", "--progressbar", action='store_true',
                        help="Show progressbar")
    parser.add_argument("-s", "--string", action='store_true',
                        help="Hash a given string or a string from stdin")
    return parser.parse_args()


def create_hashers(algorithms):
    hashers = {}
    for alg in algorithms:
        try:
            hashers[alg] = hashlib.new(alg)
        except ValueError:
            print(f'Unsupported hashing algorithm: "{alg}"')
            print('Please use pyhash -l or --list to see supported algorithms.')
            return False
    return hashers


def get_file_hashes(file, algorithms, show_progress=False):
    """
    Calculate hashes with all requested algorithms for a given file
    """
    # try to create hashers with algorithms specified by -a
    hashers = create_hashers(algorithms)

    # Read files in blocks of BLOCKSIZE to prevent loading big files to ram
    BLOCKSIZE = 65536
    # Calculations to determine the percentage of the file already read
    FILESIZE = os.path.getsize(file)
    NUM_BLOCKS = FILESIZE // BLOCKSIZE
    n = NUM_BLOCKS // 100 or 1
    i = 1
    # Open file
    with open(file, 'rb') as file_handle:
        # Looping through file updating hasher every time
        while buf := file_handle.read(BLOCKSIZE):
            for alg in algorithms:
                hashers[alg].update(buf)
            if show_progress:
                # Print progressbar every 1% and on last loop
                if i % n == 0 or i == NUM_BLOCKS:
                    progressbar(i / (NUM_BLOCKS or 1))
                i += 1

    ret = {}

    for alg, hasher in hashers.items():
        # Try Block to handle shake hashes - they require a digest length
        try:
            ret[alg] = hasher.hexdigest()
        except TypeError:
            ret[alg] = hasher.hexdigest(int(alg[-3:]))

    return ret


def get_string_hashes(string, algorithms):
    """
    Calculate hashes with all requested algorithms for a given string
    """
    # try to create hashers with algorithms specified by -a
    hashers = create_hashers(algorithms)

    for alg in algorithms:
        hashers[alg].update(string.encode())

    ret = {}

    for alg, hasher in hashers.items():
        # Try Block to handle shake hashes - they require a digest length
        try:
            ret[alg] = hasher.hexdigest()
        except TypeError:
            ret[alg] = hasher.hexdigest(int(alg[-3:]))

    return ret


def main():
    args = get_args()

    # algorithm list of str. Set by -a | Defaults to ['md5', 'sha1', 'sha256']
    algorithms = args.algorithms

    # get list of available algorithms
    avail_algs = sorted(hashlib.algorithms_guaranteed)

    # create algorithm group dictionary
    alg_grps = {
        'sha': [x for x in avail_algs if ('sha' in x and '_' not in x)],
        'sha3': [x for x in avail_algs if ('sha3_' in x)],
        'blake': [x for x in avail_algs if ('blake' in x)],
        'shake': [x for x in avail_algs if ('shake' in x)],
    }

    # if all is specified - use all available algorithms
    if 'all' in algorithms:
        algorithms = avail_algs

    else:
        # Expand group names in algorithm list
        for a in alg_grps.keys():
            if a in algorithms:
                algorithms.remove(a)
                algorithms += alg_grps[a]

    # String Mode: get provided string or read in stdin
    if args.string:
        strings = args.target
        if not strings:
            if not sys.stdin.isatty():
                strings = [sys.stdin.read().strip()]
        if not strings:
            print('No Input detected on stdin! - Exiting')
            return

        for string in strings:
            print('hashing string:', string)
            hashes = get_string_hashes(string, algorithms)
            if not hashes:
                return False
            for alg, hashdigest in hashes.items():
                print(f'{alg}:'.ljust(9), hashdigest)
            print()

        return True

    # File Mode:
    # get list of filenames to hash
    files = args.target

    if not files:
        print('No files Specified. Type pyhash -h for more info')
        return

    # Support * syntax for windows cmd (aka do it manually)
    if files[0] in '*' and len(files) == 1:
        files = [f for f in os.listdir('.') if os.path.isfile(f)]

    # progressbar flag. Set by -p
    show_progress = args.progressbar

    for file in files:
        if not os.path.isfile(file):
            print(f'{file} is not a file - skipping')
            continue

        print('hashing:', file)
        hashes = get_file_hashes(file, algorithms, show_progress)
        if not hashes:
            return False

        for alg, hashdigest in hashes.items():
            print(f'{alg}:'.ljust(9), hashdigest)
        print()


# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
