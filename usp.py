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


class S:
    @staticmethod
    def is_linux():  # type: ignore
        return system() == "Linux"

    @staticmethod
    def is_windows():  # type: ignore
        return system() == "Windows"

    @staticmethod
    def is_mac():  # type: ignore
        return system() == "Darwin"

    @staticmethod
    def ch(d: dict):
        if temp := d.get(system()[0].lower()):
            return temp
        else:
            raise Exception("Unsupported platform")

    @staticmethod
    def config_path() -> Path:
        """get config file path"""
        return S.ch(
            {
                "l": Path.home() / ".config" / "autostart",
                "w": (
                    Path.home()
                    / "AppData"
                    / "Roaming"
                    / "Microsoft"
                    / "Windows"
                    / "Start Menu"
                    / "Programs"
                    / "Startup"
                ),
                "m": Path.home() / "Library" / "LaunchAgents",
            }
        )

    @staticmethod
    def comment_prefix():
        """get comment prefix"""
        return S.ch({"l": "# ", "w": "# ", "m": "<!--"})

    @staticmethod
    def comment(s: str) -> str:
        """
        get commented string
        """
        lm = lambda: f"{S.comment_prefix()}{s}"  # noqa: E731
        return S.ch({"l": lm(), "w": lm(), "m": f"{S.comment_prefix()}{s}\n-->"})

    @staticmethod
    def open_command() -> str:
        """
        use the command to open config folder
        """
        return S.ch({"l": "xdg-open", "w": "explorer", "m": "open"})

    @staticmethod
    def file_ext():
        """get config file extension"""
        return S.ch({"l": ".desktop", "w": ".ps1", "m": ".plist"})


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
            prefixed_cmd=S.comment(cmd),
            name=name,
            cmd=cmd,
        )
    elif S.is_windows():
        return WINDOWS_BASE_STRING.format(
            prefixed_cmd=S.comment(cmd),
            cmd=cmd,
            stdout=(f"-RedirectStandardOutput {stdout}" if stdout else ""),
            stderr=(f"-RedirectStandardError {stderr}" if stderr else ""),
        )
    elif S.is_mac():
        return MACOS_BASE_STRING.format(
            prefixed_cmd=S.comment(cmd),
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


def find_writable_path(name: str) -> Path:
    """
    find a writable path for the config file. ex. name, name1, name2, ...
    """
    log.debug(f"finding writable path for `{name}`")
    if not (p := (S.config_path() / name).with_suffix(S.file_ext())).exists():
        return p
    for i in range(1, 1000):
        p = (S.config_path() / f"{name}{i}").with_suffix(S.file_ext())
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
        f"finding config files in `{S.config_path()}` with extension `{S.file_ext()}`"
    )
    files = list(S.config_path().glob(f"*{S.file_ext()}"))
    log.debug(f"found {len(files)} config files")
    first_lines = list(
        map(
            lambda x: read_first_line(x).removeprefix(S.comment_prefix()).strip(),
            files,
        )
    )
    print(LIST_BASE_STRING.format("id", "command"))
    for path, fline in zip(files, first_lines):
        print(LIST_BASE_STRING.format(path.name.removesuffix(S.file_ext()), fline))


def remove_item(item):
    """
    remove a startup command
    """
    id: str = item.id
    if (p := (S.config_path() / id).with_suffix(S.file_ext())).exists():
        p.unlink()
        log.info(f"removed `{id}`")
    else:
        log.error(
            f"config file id `{id}` not found. try `{sys.argv[0]} list` to find it"
        )


def open_config_folder(_):
    subprocess.run([S.open_command(), str(S.config_path())])


def main(argv: list):
    LOGLEVEL = os.environ.get("DEBUG") or os.environ.get("debug")
    log.basicConfig(
        format="%(levelname)s: %(message)s",
        level=log.INFO if not LOGLEVEL else log.DEBUG,
    )

    if S.is_linux() and not S.config_path().exists():
        log.warning("config path not found. creating it...")
        S.config_path().mkdir(parents=True, exist_ok=True)

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

    if len(argv) == 0:
        parser.print_help(sys.stderr)
        exit(1)
    args = parser.parse_args(args=argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])


class Test(unittest.TestCase):
    def test_add_and_remove(self):
        main(["add", "test hello world"])
        main(["remove", "test"])

    def test_list(self):
        main(["list"])
