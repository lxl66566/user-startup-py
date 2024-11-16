# user-startup-py

> [!CAUTION]
> This project has been RIIR, and is no longer maintained.
> please use [user-startup-rs](https://github.com/lxl66566/user-startup-rs) instead.

A simple cross-platform python script to make your command auto run on startup!

no need to install anything (except python3 runtime), no need to edit any config files, no need to be root user.

## Usage

1. download the [usp.py](https://github.com/lxl66566/user-startup-py/blob/main/usp.py) script, from web, git, wget or anything.
   - wget: `wget https://raw.githubusercontent.com/lxl66566/user-startup-py/main/usp.py`
2. run `python3 usp.py` to see help message

## Examples

```bash
python3 usp.py add "echo hello world"     # add a command to run on startup
python3 usp.py list                       # list all commands and it's id
python3 usp.py remove echo                # delete a command from startup (by id)
python3 usp.py open                       # open the startup config folder
```

## QA

- **Q**: If I have more than one line command, how to run them?
  - **A**: Manually write the commands to a script, and runs this script as a command.

## Thanks

- [typicode/user-startup](https://github.com/typicode/user-startup)
