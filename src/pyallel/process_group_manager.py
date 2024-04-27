from __future__ import annotations

import signal
import sys
from dataclasses import dataclass, field
from typing import Any

from pyallel.colours import Colours
from pyallel.process_group import ProcessGroup


@dataclass
class ProcessGroupManager:
    process_groups: list[ProcessGroup]
    interactive: bool = False
    debug: bool = False
    colours: Colours = field(default_factory=Colours)

    def stream(self) -> int:
        exit_code = 0

        if not self.interactive:
            if self.debug:
                print(
                    f"{self.colours.dim_on}DEBUG mode{self.colours.dim_off}\n",
                    flush=True,
                    file=sys.stderr,
                )
            print(
                f"{self.colours.dim_on}=>{self.colours.dim_off} {self.colours.white_bold}Running commands...{self.colours.reset_colour}\n{self.colours.dim_on}=>{self.colours.dim_off} ",
                flush=True,
            )

        for process_group in self.process_groups:
            exit_code = process_group.stream()
            if exit_code > 0:
                break

        return exit_code

    def handle_signal(self, signum: int, _frame: Any) -> None:
        for process_group in self.process_groups:
            process_group.handle_signal(signum)

    @classmethod
    def from_args(
        cls,
        *args: str,
        colours: Colours | None = None,
        debug: bool = False,
        interactive: bool = False,
        timer: bool = False,
    ) -> ProcessGroupManager:
        colours = colours or Colours()
        last_separator_index = 0
        commands: list[str] = []
        process_groups: list[ProcessGroup] = []

        for i, arg in enumerate(args):
            if arg == ":::":
                if i - 1 == 0:
                    process_groups.append(
                        ProcessGroup.from_commands(
                            args[0],
                            colours=colours,
                            debug=debug,
                            interactive=interactive,
                            timer=timer,
                        )
                    )
                else:
                    process_groups.append(
                        ProcessGroup.from_commands(
                            *commands[last_separator_index:],
                            colours=colours,
                            debug=debug,
                            interactive=interactive,
                            timer=timer,
                        )
                    )

                last_separator_index = i
                continue

            commands.append(arg)

        if len(process_groups) > 1:
            last_separator_index -= 1

        process_groups.append(
            ProcessGroup.from_commands(
                *commands[last_separator_index:],
                colours=colours,
                debug=debug,
                interactive=interactive,
                timer=timer,
            )
        )

        process_group_manager = cls(
            process_groups=process_groups,
            debug=debug,
            interactive=interactive,
            colours=colours,
        )

        signal.signal(signal.SIGINT, process_group_manager.handle_signal)
        signal.signal(signal.SIGTERM, process_group_manager.handle_signal)

        return process_group_manager
