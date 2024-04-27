from __future__ import annotations

from argparse import ArgumentParser, RawTextHelpFormatter
from typing import Literal


class Arguments:
    colour: Literal["yes", "no", "auto"]
    commands: list[str]
    debug: bool
    interactive: bool
    timer: bool
    version: bool

    def __repr__(self) -> str:
        msg = "Arguments:\n"
        padding = len(sorted(self.__dict__.keys(), key=len, reverse=True)[0]) + 1
        for field, value in self.__dict__.items():
            msg += f"    {field: <{padding}}: {value}\n"
        return msg


COMMANDS_HELP = r"""list of quoted commands to run in parallel e.g "mypy ." "black ."

each command is executed inside a shell, so shell syntax is supported as
if you were running the command directly in a shell, some examples are below

     "MYPY_FORCE_COLOR=1 mypy ."          <- provide environment variables
     "mypy | tee -a mypy.log"             <- use pipes to redirect output
     "cat > test.log < other.log"         <- use input and output redirection
     "mypy .; pytest ."                   <- run commands one at a time in sequence
     "echo \$SHELL" or "\$(echo mypy .)"  <- expand variables and commands to evaluate (must be escaped)
     "pytest . && mypy . || echo failed!" <- use AND (&&) and OR (||) to run commands conditionally

commands can be grouped using the group separator symbol (:::)

     "echo boil kettle" "sleep 1" ::: "echo make coffee"

the above will print "boil kettle" and sleep for 1 second first before printing "make coffee"

command groups are ran in the sequence you provide them, and if a command group fails
(if a command fails inside the command group) the rest of the command groups in the sequence are not run
"""


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="pyallel",
        description="Run and handle the output of multiple executables in pyallel (as in parallel)",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "commands",
        help=COMMANDS_HELP,
        nargs="*",
    )
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        help="output debug info to a debug.log file",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-t",
        "--no-timer",
        dest="timer",
        help="don't time how long each command is taking",
        action="store_false",
        default=True,
    )
    parser.add_argument(
        "-n",
        "--non-interactive",
        help="run in non-interactive mode",
        action="store_false",
        dest="interactive",
        default=True,
    )
    parser.add_argument(
        "-V",
        "--version",
        help="print version and exit",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--colour",
        help='colour terminal output, defaults to "%(default)s"',
        choices=("yes", "no", "auto"),
        default="auto",
    )

    return parser
