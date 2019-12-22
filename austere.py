#!/usr/bin/env python
"""austere a default browser app manager"""
import json
import logging
import sys
import shlex
import subprocess
import os.path
import platform
from typing import Sequence
from pathlib import Path

import attr
import psutil
import click

if platform.system() == "Windows":
    import winreg

if sys.version_info[0:2] == (3, 8):
    from importlib.metadata import future_version
else:
    future_version = None

logger = logging.getLogger("austere")
FOLDER = click.get_app_dir("Austere")
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def main(url: str) -> None:
    with open(os.path.join(FOLDER, "config.json"), "r") as j:
        light_browser = json.loads(j.read())['light_browser']
    use_light = False
    # check for steam games running
    overlay = [x for x in psutil.process_iter() if "gameoverlayui" in x.name().decode()]
    if len(overlay) > 0:
        # all of the gameoverlayui's have the pid
        game_pid = int(overlay[0].cmdline()[2])
        logger.info("Detected game %s", psutil.Process(pid=game_pid).name().decode())
        use_light = True
    # check for big picture games
    # they're direct descendants of steam
    elif len(overlay) == 0:
        for proc in psutil.process_iter():
            if proc.name() == "steam":
                z = list(filter(lambda x: x.name().decode() not in ['steamwebhelper', 'steam', 'sh', 'SteamChildMonit'], proc.children(recursive=True)))
                if len(z) == 1:
                    logger.info("Detected game %s", z[0])
                    use_light = True
                elif len(z) == 0:
                    logger.info("Found no games running in big picture mode")
                else:
                    logger.error("Found more than one potential game process, this behavior is undefined")
                    logger.info(z)
            elif proc.name() == 'Battle.net.exe':
                z = list(filter(lambda x: x.name().decode() not in ['Battle.net Helper.exe', 'CrashMailer_64.exe'], proc.children(recursive=True)))
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
            subprocess.call([light_browser, url])
    else:
        if platform.system() == "Windows":
            # win 7+ assumption ?
            subprocess.call(['powershell.exe', '-Command', 'start', url])
        else:
            subprocess.call(['x-www-browser', url])


@attr.s
class WindowsBrowser:
    name: str = attr.ib()
    enum_order: int = attr.ib()
    path: str = attr.ib()

    def __str__(self) -> str:
        return f"<{self.enum_order}> {self.name} ({self.path})"

# https://stackoverflow.com/questions/31164253/how-to-open-url-in-microsoft-edge-from-the-command-line#31281412
# https://msdn.microsoft.com/en-us/library/windows/desktop/cc144175(v=vs.85).aspx

def win_default():
    # HKEY_LOCAL_MACHINE\SOFTWARE\Clients\StartMenuInternet
    reg_value = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Clients\StartMenuInternet")
    return reg_value


def win_browser_list() -> Sequence[WindowsBrowser]:
    # https://docs.python.org/3.6/library/winreg.html
    # reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Clients\StartMenuInternet") as key:
        target_keys, _, _ = winreg.QueryInfoKey(key)
        l = list()
        for i in range(target_keys):
            v = winreg.EnumKey(key, i)
            logger.debug("got value from StartMenuInternet: %s", v)
            # Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Clients\StartMenuInternet\Firefox-308046B0AF4A39CB\shell\open\command
            path = winreg.QueryValue(key, r"{}\shell\open\command".format(v))
            l.append(WindowsBrowser(name=v, enum_order=i, path=path))
        # print(key)
        return l


def pick_browser() -> str:
    if platform.system() == "Windows":
        logger.debug("welcome to windows. We use win10.")
        # get browser options and default on windows
        logger.debug("default browser: %s", win_default())
        opts = win_browser_list()
    elif platform.system() == "Linux":
        opts = linux_browser_list()
    for b in opts:
        print(b)
    while True:
        response = click.prompt('Pick your lightweight browser')
        if response.isdigit():
            if int(response) <= len(opts):
                return opts[int(response)].path

class LinuxBrowser(WindowsBrowser):
    pass

def linux_browser_list() -> Sequence[LinuxBrowser]:
    paths = subprocess.check_output(
        shlex.split("update-alternatives --list x-www-browser")).decode().split()
    return [LinuxBrowser(name=p, enum_order=i, path=p) for i, p in enumerate(paths)]
#    not_chrome = list(filter(lambda x: "chrome".encode() not in x, browsers))


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('--version', 'my_version', default=False, is_flag=True, help="this is a bogus arg mapped to version command for maximum nice", hidden=True)
@click.option('--debug', default=False, is_flag=True, help="control log level")
@click.option('--verbose/--silent', default=True, help="control log level")
@click.pass_context
def cli_base(ctx: click.Context, verbose: bool, debug: bool, my_version: bool) -> None:
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
def windows_cli() -> None:
    pass


@windows_cli.command()
def win_register() -> None:
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

    except OSError:
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
            winreg.SetValue(reg_icon, None, winreg.REG_SZ, r"C:\Program Files\Mozilla Firefox\firefox.exe,0")

    # with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"Software\RegisteredApplications") as reg_apps:
    #     winreg.SetValueEx(reg_apps, "austere_macguffin", None, winreg.REG_SZ, r"Software\Clients\StartMenuInternet\austere_macguffin\Capabilities")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications") as reg_apps:
        winreg.SetValueEx(reg_apps, "austere_macguffin", None, winreg.REG_SZ, r"Software\Clients\StartMenuInternet\austere_macguffin\Capabilities")


@cli_base.command()
def version() -> None:
    if future_version:
        ver = future_version("austere")
    else:
        ver = "0.3.0"
    print(f"version {ver} austere")


@cli_base.command("help")
@click.pass_context
def local_help(ctx: click.Context) -> None:
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
        not_chrome = list(filter(lambda x: "chrome".encode() not in x, browsers))
        return not_chrome[0]

@click.group()
def linux() -> None:
    pass


@linux.command()
@click.option("--script_name")
@click.option("--desktop_path")
def install(desktop_path: str, script_name: str) -> None:
    "create .desktop file for gnome and other DEs"
    if desktop_path:
        f = desktop_path
    else:
        f = Path("/usr/local/share/applications", "austere.desktop")
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
def config_cmd(light_browser: str) -> None:
    """Configure your austere install. Choose a light-weight browser."""
    cfg_path = os.path.join(FOLDER, "config.json")
    try:
        with open(cfg_path) as f:
            cfg = json.load(f)
        light_browser = cfg['light_browser']
        print(f"Your configured lightweight browser is: {light_browser}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug("couldn't open config at %s: %s", f, e)
    path = pick_browser()
    d = {"light_browser": path}
    with open(cfg_path, 'w') as f:
        json.dump(d, f)


@cli_base.command()
@click.argument("URL")
def run_on_url(url: str) -> None:
    "default action?"
    main(url)

# Hide os-dependent commands
if platform.system() == "Linux":
    cli = click.CommandCollection(sources=[cli_base, linux])()
elif platform.system() == "Windows":
    cli = click.CommandCollection(sources=[cli_base, windows_cli])
else:
    cli = cli_base

if __name__ == '__main__':
    Path(FOLDER).mkdir(exist_ok=True)
    cli()
