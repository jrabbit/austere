#!/usr/bin/env python
import json
import logging
import sys
import shlex
import subprocess
import platform
import winreg

from typing import List

import attr
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
        logger.info("Detected game %s", psutil.Process(pid=game_pid).name())
        use_light = True
    # check for big picture games
    # they're direct descendants of steam
    elif len(overlay) == 0:
        for proc in psutil.process_iter():
            if proc.name() == "steam":
                z = list(filter(lambda x: x.name() not in ['steamwebhelper','steam','sh', 'SteamChildMonit'], proc.children(recursive=True)))
                if len(z) == 1:
                    logger.info("Detected game %s", z[0])
                    use_light = True
                elif len(z) == 0:
                    logger.info("Found no games running in big picture mode")
                else:
                    logger.error("Found more than one potential game process, this behavior is undefined")
                    logger.info(z)
            elif proc.name() == 'Battle.net.exe':
                z = list(filter(lambda x: x.name() not in ['Battle.net Helper.exe', 'CrashMailer_64.exe'], proc.children(recursive=True)))
                if len(z) == 1:
                    logger.info("Detected game %s", z[0])
                    use_light = True
                else:
                    logger.info(z)
                logger.info("battlenet children: %s", proc.children(recursive=True))

    # check if we're almost out of memory
    elif psutil.virtual_memory().percent > 90:
        use_light = True
    # check battery info
    if use_light:
        if platform.system() == "Windows":
            pass
        else:
            subprocess.call([light_browser, sys.argv[1]])
    else:
        if platform.system() == "Windows":
            subprocess.call(['powershell.exe', '-Command', 'start {}'.format(sys.argv[1])])
        else:    
            subprocess.call(['x-www-browser', sys.argv[1]])

    logger.debug(args)


@attr.s
class WindowsBrowser():
    name = attr.ib()
    enum_order = attr.ib()
    path = attr.ib()

    # def __str__(self):
    #     return self.name

def win_default() -> str:
    # HKEY_LOCAL_MACHINE\SOFTWARE\Clients\StartMenuInternet
    reg_value = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\Clients\StartMenuInternet")
    return reg_value

def win_browser_list() -> List[WindowsBrowser]:
    # https://docs.python.org/3.6/library/winreg.html
    # reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\Clients\StartMenuInternet") as key:
        target_keys, value_keys, last_mod = winreg.QueryInfoKey(key)
        l = list()
        for i in range(target_keys):
            v = winreg.EnumKey(key, i)
            logger.debug("got value from StartMenuInternet: %s", v)
            # Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Clients\StartMenuInternet\Firefox-308046B0AF4A39CB\shell\open\command
            path = winreg.QueryValue(key, "{}\shell\open\command".format(v))
            wb = WindowsBrowser(name=v, enum_order=i, path=path)
            l.append(wb)
        # print(key)
        return l

def win_register():
    "need to be admin"
    try:
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "austere.HTTP") as k:
            # winreg.SetValue(k, None, winreg.REG_SZ,  "{} austere".format(sys.argv[0]))
            logger.debug("\shell")
            with winreg.CreateKey(k, "shell") as shellkey:
                logger.debug("\open")
                with winreg.CreateKey(shellkey, "open") as openkey:
                    logger.debug("\command")
                    with winreg.CreateKey(openkey, "command") as cmdkey:
                        winreg.SetValue(cmdkey, None, winreg.REG_SZ,  '"{} austere" "%1"'.format(sys.argv[0]))
        # with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "austere.HTTPS") as kssl:
        #     winreg.SetValue(kssl, None, winreg.REG_SZ,  "{} austere".format(sys.argv[0]))
    except OSError as e:
        logger.error(e)

def pick_browser() -> str:
    if platform.system() == "Windows":
        logger.debug("welcome to windows. We use win10.")
        # get browser options and default on windows
        logger.debug("default browser: %s", win_default())
        opts = win_browser_list()
        for b in opts:
            print(b)
        path = prompt.query('Pick your lightweight browser:')
        return path

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
