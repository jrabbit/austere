#!/usr/bin/env python
import json
import logging
import sys
import shlex
import subprocess
import platform
import winreg

import psutil
from clint import resources
from clint.textui import prompt, validators, puts, indent

logger = logging.getLogger("austere")

def main(*args) -> None:
    resources.init('jacklaxson', 'austere')
    j = resources.user.read("config.json")
    light_browser = json.loads(j)['light_browser']
    use_light = False
    # check for steam games running
    overlay = [x for x in psutil.process_iter() if "gameoverlayui" in x.name()]
    if len(overlay) > 0:
        # all of the gameoverlayui's have the pid
        game_pid = int(overlay[0].cmdline()[2])
        logger.info("Detected game {0}", psutil.Process(pid=game_pid).name())
        use_light = True
    # check for big picture games
    # they're direct descendants of steam
    elif len(overlay) == 0:
        for proc in psutil.process_iter():
            if proc.name() == "steam":
                z = filter(lambda x: x.name() not in ['steamwebhelper','steam','sh', 'SteamChildMonit'], proc.children(recursive=True))
                if len(z) == 1:
                    logger.info("Detected game {0}", z[0])
                    use_light = True
                elif len(z) == 0:
                    logger.info("Found no games running in big picture mode")
                else:
                    logger.error("Found more than one potential game process, this behavior is undefined")
                    logger.info(z)
    # check if we're almost out of memory
    elif psutil.virtual_memory().percent > 90:
        use_light = True
    # check battery info
    if use_light:
        subprocess.call([light_browser, sys.argv[1]])
    else:
        subprocess.call(['x-www-browser', sys.argv[1]])

    logger.debug(args)


def win_default() -> str:
    # HKEY_LOCAL_MACHINE\SOFTWARE\Clients\StartMenuInternet
    reg = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\Clients\StartMenuInternet")
    return reg


def pick_browser() -> str:
    if platform.system() == "Windows":
        logger.debug("welcome to windows. We use win10.")
        # get browser options and default on windows
        logger.debug("default browser: %s", win_default())

    elif platform.system() == "Linux":
        browsers = subprocess.check_output(
            shlex.split("update-alternatives --list x-www-browser")).split()
        print("Found these browsers:")
        with indent(4):
            for b in browsers:
                puts(b)
        not_chrome = filter(lambda x: "chrome" not in x, browsers)
        path = prompt.query('Pick your lightweight browser:', default=not_chrome[0], validators=[validators.FileValidator()])
        return path


def config() -> None:
    resources.init('jacklaxson', 'austere')
    j = resources.user.read("config.json")
    if j == None:
        path = pick_browser()
    else:
        light_browser = json.loads(j)['light_browser']
        print("Your default lightweight browser is: %s" % light_browser)
        z = prompt.query(
            'Change your lightweight browser? [y/n]', validators=[validators.OptionValidator(["y", "n"])]).lower()
        if z == "y":
            path = pick_browser()
        else:
            path = light_browser
    d = {"light_browser": path}
    resources.user.write('config.json', json.dumps(d))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) > 1:
        main(sys.argv)
    else:
        config()
