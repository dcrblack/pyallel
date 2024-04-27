from __future__ import annotations

import importlib.metadata
import sys
import traceback

from pyallel import constants
from pyallel.colours import Colours
from pyallel.errors import InvalidExecutableErrors
from pyallel.parser import Arguments, create_parser
from pyallel.process_group_manager import ProcessGroupManager


def main_loop(
    *args: str,
    colours: Colours,
    debug: bool = False,
    interactive: bool = False,
    timer: bool = False,
) -> int:
    process_group_manager = ProcessGroupManager.from_args(
        *args,
        colours=colours,
        debug=debug,
        interactive=interactive,
        timer=timer,
    )

    return process_group_manager.stream()


def run(*args: str) -> int:
    parser = create_parser()
    parsed_args = parser.parse_args(args=args, namespace=Arguments())

    if parsed_args.version:
        my_version = importlib.metadata.version("pyallel")
        print(my_version)
        return 0

    if not parsed_args.commands:
        parser.print_help()
        return 2

    colours = Colours.from_colour(parsed_args.colour)

    interactive = True
    if not parsed_args.interactive:
        interactive = False
    elif not constants.IN_TTY:
        interactive = False

    message = None
    try:
        exit_code = main_loop(
            *parsed_args.commands,
            colours=colours,
            debug=parsed_args.debug,
            interactive=interactive,
            timer=parsed_args.timer,
        )
    except InvalidExecutableErrors as e:
        exit_code = 1
        message = str(e)
    except Exception:
        exit_code = 1
        message = traceback.format_exc()

    if exit_code == 1:
        if not message:
            print(
                f"{colours.dim_on}=>{colours.dim_off} {colours.red_bold}Failed!{colours.reset_colour}"
            )
        else:
            print(
                f"{colours.dim_on}=>{colours.dim_off} {colours.red_bold}Error: {message}{colours.reset_colour}"
            )
    elif exit_code == 0:
        print(
            f"{colours.dim_on}=>{colours.dim_off} {colours.green_bold}Done!{colours.reset_colour}"
        )

    return exit_code


def entry_point() -> None:
    sys.exit(run(*sys.argv[1:]))


if __name__ == "__main__":
    entry_point()
