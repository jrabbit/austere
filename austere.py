import logging
import sys
import subprocess

import psutil


def main(*args):
    overlay = [x for x in psutil.process_iter() if "gameoverlayui" in x.name()]
    if len(overlay) > 0:
        # all of the gameoverlayui's have the pid
        game_pid = int(overlay[0].cmdline()[2])
        logging.info("Detected game {0}", psutil.Process(pid=game_pid).name())
        subprocess.call(['iceweasel', sys.argv[1]])
    else:
        subprocess.call(['x-www-browser', sys.argv[1]])
    logging.debug(args)
    print(args)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv)