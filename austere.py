import psutil
import logging
import sys

def main(*args):
    overlay = [x for x in psutil.process_iter() if "gameoverlayui" in x.name()]
    if len(overlay) > 0:
        # all of the gameoverlayui's have the pid
        game_pid = int(overlay[0].cmdline()[2])
        logging.info("Detected game {0}", psutil.Process(pid=game_pid).name())
    logging.debug(args)
    print(args)

if __name__ == '__main__':
    logging.basicConfig(filename='example.log', level=logging.DEBUG)
    main(sys.argv)