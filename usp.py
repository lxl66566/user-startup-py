#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# source: https://github.com/lxl66566/user-startup-py
# version: 0.1.0

import argparse
import logging as log
import os
import subprocess
import sys
import unittest
from pathlib import Path
from platform import system
from typing import Optional

LIST_BASE_STRING = "{:24} {:50}"
WINDOWS_BASE_STRING = """{prefixed_cmd}
Start-Process "cmd.exe" -ArgumentList "/c {cmd}" -WindowStyle Hidden {stdout} {stderr}
"""
LINUX_BASE_STRING = """{prefixed_cmd}
[Desktop Entry]
Type=Application
Version=1.0
Name={name}
Comment={name} startup script
Exec={cmd}
StartupNotify=false
Terminal=false
"""
MACOS_BASE_STRING = """{prefixed_cmd}
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{cmd}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    {stdout}
    {stderr}
</dict>
</plist>
"""


class S(object):
    def is_linux():  # type: ignore
        return system() == "Linux"

    def is_windows():  # type: ignore
        return system() == "Windows"

    def is_mac():  # type: ignore
        return system() == "Darwin"


def read_first_line(file_path):
    """
    read the first line of a file
    """
    log.debug(f"reading first line of `{file_path}`")
    try:
        with open(file_path, "r") as file:
            for line in file:
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith("#!"):
                    return stripped_line
            else:
                raise Exception("the file is empty")
    except (IOError, FileNotFoundError) as e:
        print(f"cannot read {file_path}: {e}")
        raise


def format_config(
    cmd: str,
    name: Optional[str] = None,
    stdout: Optional[Path] = None,
    stderr: Optional[Path] = None,
):
    if name is None:
        name = cmd.split(maxsplit=1)[0]
    if S.is_linux():
        return LINUX_BASE_STRING.format(
            prefixed_cmd=comment(cmd),
            name=name,
            cmd=cmd,
        )
    elif S.is_windows():
        return WINDOWS_BASE_STRING.format(
            prefixed_cmd=comment(cmd),
            cmd=cmd,
            stdout=(f"-RedirectStandardOutput {stdout}" if stdout else ""),
            stderr=(f"-RedirectStandardError {stderr}" if stderr else ""),
        )
    elif S.is_mac():
        return MACOS_BASE_STRING.format(
            prefixed_cmd=comment(cmd),
            name=name,
            cmd=cmd,
            stdout=(
                f"<key>StandardOutPath</key>\n<string>{stdout}</string>"
                if stdout
                else ""
            ),
            stderr=(
                f"<key>StandardErrorPath</key>\n<string>{stderr}</string>"
                if stderr
                else ""
            ),
        )
    else:
        raise Exception("Unsupported platform")


def config_path() -> Path:
    """get config file path"""
    if S.is_linux():
        return Path.home() / ".config" / "autostart"
    elif S.is_windows():
        return (
            Path.home()
            / "AppData"
            / "Roaming"
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
        )
    elif S.is_mac():
        return Path.home() / "Library" / "LaunchAgents"
    else:
        raise Exception("Unsupported platform")


def comment_prefix():
    """get comment prefix"""
    if S.is_linux() or S.is_windows():
        return "# "
    elif S.is_mac():
        return "<!--"
    else:
        raise Exception("Unsupported platform")


def comment(s: str) -> str:
    """
    get commented string
    """
    if S.is_linux() or S.is_windows():
        return f"{comment_prefix()}{s}"
    elif S.is_mac():
        return f"{comment_prefix()}{s}\n-->"
    else:
        raise Exception("Unsupported platform")


def file_ext():
    """get config file extension"""
    if S.is_linux():
        return ".desktop"
    elif S.is_windows():
        return ".ps1"
    elif S.is_mac():
        return ".plist"
    else:
        raise Exception("Unsupported platform")


def find_writable_path(name: str) -> Path:
    """
    find a writable path for the config file. ex. name, name1, name2, ...
    """
    log.debug(f"finding writable path for `{name}`")
    if not (p := (config_path() / name).with_suffix(file_ext())).exists():
        return p
    for i in range(1, 1000):
        p = (config_path() / f"{name}{i}").with_suffix(file_ext())
        if not p.exists():
            return p
    raise Exception("TOO MANY ITEMS OF SAME NAME!")


def add_item(item):
    """
    add a startup command
    """
    if S.is_linux() and (item.stdout or item.stderr):
        log.warning(
            "`--stdout` and `--stderr` are not supported for linux startup scripts. "
            "please append ` > /path/to/output.log 2> /path/to/error.log` to your command manually."
        )
    cmd: str = item.command
    name = cmd.split(maxsplit=1)[0]
    path = find_writable_path(name)
    with path.open("w") as f:
        f.write(format_config(cmd, name, item.stdout, item.stderr))
        log.info(f"added `{cmd}` to `{path}`")


def list_items(_):
    """
    list all startup commands
    """
    log.debug(
        f"finding config files in `{config_path()}` with extension `{file_ext()}`"
    )
    files = list(config_path().glob(f"*{file_ext()}"))
    log.debug(f"found {len(files)} config files")
    first_lines = list(
        map(
            lambda x: read_first_line(x).removeprefix(comment_prefix()).strip(),
            files,
        )
    )
    print(LIST_BASE_STRING.format("id", "command"))
    for path, fline in zip(files, first_lines):
        print(LIST_BASE_STRING.format(path.name.removesuffix(file_ext()), fline))


def remove_item(item):
    """
    remove a startup command
    """
    id: str = item.id
    if (p := (config_path() / id).with_suffix(file_ext())).exists():
        p.unlink()
        log.info(f"removed `{id}`")
    else:
        log.error(
            f"config file id `{id}` not found. try `{sys.argv[0]} list` to find it"
        )


def open_config_folder(_):
    if S.is_linux():
        subprocess.run(["xdg-open", str(config_path())])
    elif S.is_windows():
        subprocess.run(["explorer", str(config_path())])
    elif S.is_mac():
        subprocess.run(["open", str(config_path())])
    else:
        raise Exception("Unsupported platform")


def main():
    LOGLEVEL = os.environ.get("DEBUG") or os.environ.get("debug")
    log.basicConfig(
        format="%(levelname)s: %(message)s",
        level=log.INFO if not LOGLEVEL else log.DEBUG,
    )

    if S.is_linux() and not config_path().exists():
        log.warning("config path not found. creating it...")
        config_path().mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(
        description="make any command automatically run on startup"
    )

    subparsers = parser.add_subparsers(dest="command", help="the subcommand to run")

    add_parser = subparsers.add_parser(
        "add", aliases=["a"], help="add a startup command"
    )
    add_parser.add_argument(
        "command", type=str, help="the one-line command to run on startup"
    )
    add_parser.add_argument(
        "--stdout", nargs="?", type=str, help="file path to output the stdout log"
    )
    add_parser.add_argument(
        "--stderr", nargs="?", type=str, help="file path to output the stderr log"
    )
    add_parser.set_defaults(func=add_item)

    list_parser = subparsers.add_parser(
        "list", aliases=["l"], help="list all startup commands"
    )
    list_parser.set_defaults(func=list_items)

    remove_parser = subparsers.add_parser(
        "remove", aliases=["r"], help="delete a startup command"
    )
    remove_parser.add_argument(
        "id",
        type=str,
        help=f"the id of the command to delete. to find the id, run `{sys.argv[0]} list`",
    )
    remove_parser.set_defaults(func=remove_item)

    open_config_folder_parser = subparsers.add_parser(
        "open", aliases=["o"], help="open the auto startup config folder"
    )
    open_config_folder_parser.set_defaults(func=open_config_folder)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        exit(1)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


class Test(unittest.TestCase):
    pass
