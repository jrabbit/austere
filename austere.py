#!/usr/bin/env python
import json
import logging
import sys
import shlex
import subprocess
import os.path
import platform
from typing import List
from pathlib import Path

if platform.system() == "Windows":
    import winreg

import attr
import psutil
import click

from clint.textui import prompt, validators

logger = logging.getLogger("austere")
FOLDER = click.get_app_dir("Austere")
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def main(url) -> None:
    with open(os.path.join(FOLDER, "config.json"), "r") as j:
        light_browser = json.loads(j.read())['light_browser']
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
                z = list(filter(lambda x: x.name() not in ['steamwebhelper', 'steam', 'sh', 'SteamChildMonit'], proc.children(recursive=True)))
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


@attr.s
class WindowsBrowser:
    name = attr.ib()
    enum_order = attr.ib()
    path = attr.ib()
    def __str__(self):
        return f"<{self.enum_order}> {self.name} ({self.path})"

# https://stackoverflow.com/questions/31164253/how-to-open-url-in-microsoft-edge-from-the-command-line#31281412
# https://msdn.microsoft.com/en-us/library/windows/desktop/cc144175(v=vs.85).aspx

def win_default() -> str:
    # HKEY_LOCAL_MACHINE\SOFTWARE\Clients\StartMenuInternet
    reg_value = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Clients\StartMenuInternet")
    return reg_value


def win_browser_list() -> List[WindowsBrowser]:
    # https://docs.python.org/3.6/library/winreg.html
    # reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Clients\StartMenuInternet") as key:
        target_keys, value_keys, last_mod = winreg.QueryInfoKey(key)
        l = list()
        for i in range(target_keys):
            v = winreg.EnumKey(key, i)
            logger.debug("got value from StartMenuInternet: %s", v)
            # Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Clients\StartMenuInternet\Firefox-308046B0AF4A39CB\shell\open\command
            path = winreg.QueryValue(key, r"{}\shell\open\command".format(v))
            wb = WindowsBrowser(name=v, enum_order=i, path=path)
            l.append(wb)
        # print(key)
        return l


def pick_browser() -> str:
    if platform.system() == "Windows":
        logger.debug("welcome to windows. We use win10.")
        # get browser options and default on windows
        logger.debug("default browser: %s", win_default())
        opts = win_browser_list()
        for b in opts:
            print(b)
        browser = False
        while not browser:
            response = click.prompt('Pick your lightweight browser')
            if response.isdigit():
                if int(response) <= len(opts):
                    browser = opts[int(response)]
        return browser.path

    elif platform.system() == "Linux":
        browsers = subprocess.check_output(
            shlex.split("update-alternatives --list x-www-browser")).split()
        print("Found these browsers:")
        for b in browsers:
            print(b)
        not_chrome = list(filter(lambda x: "chrome" not in x, browsers))
        path = prompt.query('Pick your lightweight browser:', default=not_chrome[0], validators=[validators.FileValidator()])
        return path


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('--version', 'my_version', default=False, is_flag=True, help="this is a bogus arg mapped to version command for maximum nice", hidden=True)
@click.option('--debug', default=False, is_flag=True, help="control log level")
@click.option('--verbose/--silent', default=True, help="control log level")
@click.pass_context
def cli_base(ctx, verbose, debug, my_version):
    # mk_folder()
    # only the first basicConfig() is respected.
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    if verbose:
        logging.basicConfig(level=logging.INFO)
    if my_version:
        # Skip directly to version command like the user would expect a gnu program to.
        ctx.invoke(version)
        ctx.exit()
    elif ctx.invoked_subcommand is None:
        # still do normal things via the named help even
        ctx.invoke(local_help)


@click.group()
def windows_cli():
    pass


@windows_cli.command()
def win_register():
    "need to be admin"
    value_to_put = f'"{sys.executable} austere" "%1"'
    try:
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "austere.HTTP") as k:
            # winreg.SetValue(k, None, winreg.REG_SZ,  "{} austere".format(sys.argv[0]))
            logger.debug(r"\shell")
            with winreg.CreateKey(k, "shell") as shellkey:
                logger.debug(r"\open")
                with winreg.CreateKey(shellkey, "open") as openkey:
                    logger.debug(r"\command")
                    with winreg.CreateKey(openkey, "command") as cmdkey:
                        winreg.SetValue(cmdkey, None, winreg.REG_SZ, value_to_put)
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "austere.HTTPS") as kssl:
            winreg.SetValue(kssl, None, winreg.REG_SZ, value_to_put)

    except OSError as e:
        logger.exception("we hit a registry issue")


@windows_cli.command()
def win_user_reg() -> None:
    value_to_put = f'"{sys.executable} austere" "%1"'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Clients\StartMenuInternet\austere_macguffin") as start_menu:
        winreg.SetValue(start_menu, None, winreg.REG_SZ, "austere")
        with winreg.CreateKey(start_menu, "Capabilities") as cap:
            winreg.SetValueEx(cap, "ApplicationName", None, winreg.REG_SZ, "Jack Laxson Presents: austere")
            winreg.SetValueEx(cap, "ApplicationDescription", None, winreg.REG_SZ, "long description goes here")
            winreg.SetValueEx(cap, "ApplicationIcon", None, winreg.REG_SZ, r"C:\Program Files\Mozilla Firefox\firefox.exe,0")
            with winreg.CreateKey(cap, "URLAssociations") as url_assoc:
                winreg.SetValueEx(url_assoc, "https", None, winreg.REG_SZ, "austere.HTTP")
                winreg.SetValueEx(url_assoc, "http", None, winreg.REG_SZ, "austere.HTTP")
            with winreg.CreateKey(cap, "StartMenu") as assoc_menu:
                winreg.SetValueEx(assoc_menu, "StartMenuInternet", None, winreg.REG_SZ, "austere_macguffin")
            with winreg.CreateKey(cap, "FileAssociations") as file_assoc:
                winreg.SetValueEx(file_assoc, ".html", None, winreg.REG_SZ, "austere.HTTP")
        with winreg.CreateKey(start_menu, "InstallInfo") as install_info:
            winreg.SetValueEx(install_info, "IconsVisible", None, winreg.REG_DWORD, 1)
        with winreg.CreateKey(start_menu, "shell") as shellkey:
            logger.debug(r"\open")
            with winreg.CreateKey(shellkey, "open") as openkey:
                logger.debug(r"\command")
                with winreg.CreateKey(openkey, "command") as cmdkey:
                    winreg.SetValue(cmdkey, None, winreg.REG_SZ, value_to_put)
        with winreg.CreateKey(start_menu, "DefaultIcon") as reg_icon:
            winreg.SetValue(reg_icon,None, winreg.REG_SZ, r"C:\Program Files\Mozilla Firefox\firefox.exe,0")

    # with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"Software\RegisteredApplications") as reg_apps:
    #     winreg.SetValueEx(reg_apps, "austere_macguffin", None, winreg.REG_SZ, r"Software\Clients\StartMenuInternet\austere_macguffin\Capabilities")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications") as reg_apps:
        winreg.SetValueEx(reg_apps, "austere_macguffin", None, winreg.REG_SZ, r"Software\Clients\StartMenuInternet\austere_macguffin\Capabilities")


@cli_base.command()
def version():
    ver = "0.2.0"
    print(f"version {ver} austere")


@cli_base.command("help")
@click.pass_context
def local_help(ctx):
    """Show this message and exit."""
    print(ctx.parent.get_help())


def _browser_default():
    if platform.system() == "Windows":
        return win_default()
    elif platform.system() == "Linux":
        browsers = subprocess.check_output(
            shlex.split("update-alternatives --list x-www-browser")).split()
        print("Found these browsers:")
        for b in browsers:
            print(b)
        not_chrome = list(filter(lambda x: "chrome" not in x, browsers))
        return not_chrome[0]

@click.group()
def linux():
    pass


@linux.command()
@click.option("--script_name")
@click.option("--desktop_path")
def install(desktop_path, script_name):
    "create .desktop file for gnome and other DEs"
    if desktop_path:
        f = desktop_path
    else:
        f = Path("", "austere.desktop")
    if script_name:
        script = script_name
    else:
        script = sys.argv[0]
    with open(f) as fd:
        fd.write(f"""#!/usr/bin/env xdg-open
[Desktop Entry]
Version=1.1
Name=Austere
Comment="a default browser switcher based on material conditions & contexts"
Exec={script} %u
#Terminal=True
Icon=view-refresh
Type=Application
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml_xml;image/webp;x-scheme-handler/http;x-scheme-handler/https;x-scheme-handler/ftp;
""")

@cli_base.command("config")
@click.option('--light-browser', prompt=True, default=_browser_default)
def config_cmd(light_browser):
    """Configure your austere install. Choose a light-weight browser."""
    cfg_path = os.path.join(FOLDER, "config.json")
    try:
        with open(cfg_path) as f:
            cfg = json.load(f)
        light_browser = cfg['light_browser']
        print(f"Your configured lightweight browser is: {light_browser}")
    except (FileNotFoundError, json.JSONDecodeError):
        path = pick_browser()
    z = prompt.query(
        'Change your lightweight browser? [y/n]', validators=[validators.OptionValidator(["y", "n"])]).lower()
    if z == "y":
        path = pick_browser()
    else:
        path = light_browser
    d = {"light_browser": path}
    with open(cfg_path, 'w') as f:
        json.dump(d, f)


@cli_base.command()
@click.argument("URL")
def run_on_url(url):
    "default action?"
    main(url)

# Hide os-dependent commands
if platform.system() == "Linux":
    cli = click.CommandCollection(sources=[cli_base, linux])()
elif platform.system == "Windows":
    cli = click.CommandCollection(sources=[cli_base, windows_cli])
else:
    cli = cli_base

if __name__ == '__main__':
    Path(FOLDER).mkdir(exist_ok=True)
    cli()
