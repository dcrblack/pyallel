from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from pyallel import constants
from pyallel.colours import Colours
from pyallel.errors import InvalidExecutableError, InvalidExecutableErrors
from pyallel.process import Process


def get_num_lines(output: str, columns: int | None = None) -> int:
    lines = 0
    columns = columns or constants.COLUMNS()
    for line in output.splitlines():
        line = constants.ANSI_ESCAPE.sub("", line)
        length = len(line)
        line_lines = 1
        if length > columns:
            line_lines = length // columns
            remainder = length % columns
            if remainder:
                line_lines += 1
        lines += 1 * line_lines
    return lines


def format_time_taken(time_taken: float) -> str:
    time_taken = round(time_taken, 1)
    seconds = time_taken % (24 * 3600)

    return f"{seconds}s"


@dataclass
class ProcessGroup:
    processes: list[Process]
    debug: bool = False
    interactive: bool = False
    timer: bool = False
    output: dict[int, list[str]] = field(default_factory=lambda: defaultdict(list))
    process_lines: list[int] = field(default_factory=list)
    completed_processes: set[int] = field(default_factory=set)
    exit_code: int = 0
    interrupt_count: int = 0
    passed: bool = True
    icon: int = 0
    colours: Colours = field(default_factory=Colours)

    def __post_init__(self) -> None:
        self.process_lines = [0 for _ in self.processes]

    def stream(self) -> int:
        for process in self.processes:
            process.run()

        if not self.interactive:
            return self.stream_non_interactive()

        while True:
            output = self.complete_output()
            self.icon += 1
            if self.icon == len(constants.ICONS):
                self.icon = 0

            print(output, end="", flush=True)

            # Clear all the lines that were just printed
            for _ in range(get_num_lines(output) - (1 if self.exit_code > 1 else 0)):
                print(
                    f"{constants.CLEAR_LINE}{constants.UP_LINE}{constants.CLEAR_LINE}",
                    end="",
                )

            if len(self.completed_processes) == len(self.processes):
                break

            time.sleep(0.1)

        print(self.complete_output(all=True), flush=True)

        if not self.exit_code and not self.passed:
            self.exit_code = 1

        return self.exit_code

    def stream_non_interactive(self) -> int:
        running_process = None
        interrupted = False

        while True:
            output = ""
            for process in self.processes:
                if (
                    running_process is None
                    and process.id not in self.completed_processes
                ):
                    output += self._get_command_status(process)
                    output += "\n"
                    running_process = process
                elif running_process is not process:
                    # Need to do this to properly keep track of how long all the other
                    # commands are taking
                    process.poll()
                    continue

                process_output = process.readline().decode()

                if not self.output[process.id] and process_output:
                    process_output = self._prefix(process_output)
                    self.output[process.id].append(process_output)
                    output += process_output
                elif process_output:
                    if self.output[process.id][-1][-1] != "\n":
                        self.output[process.id][-1] += process_output
                    else:
                        process_output = self._prefix(process_output)
                        self.output[process.id].append(process_output)
                    output += process_output

                if process.poll() is not None:
                    if process.return_code() != 0:
                        self.passed = False
                    process_output = process.read().decode()
                    if process_output:
                        output += self._prefix(process_output)

                    if (output and output[-1] != "\n") or (
                        self.output[process.id]
                        and self.output[process.id][-1][-1] != "\n"
                    ):
                        output += "\n"

                    output += self._get_command_status(
                        process,
                        passed=process.return_code() == 0,
                        timer=self.timer,
                    )
                    output += f"\n{self.colours.dim_on}=>{self.colours.dim_off} \n"
                    self.completed_processes.add(process.id)
                    running_process = None

                if self.interrupt_count == 0:
                    pass
                elif not interrupted and self.interrupt_count == 1:
                    if (output and output[-1] != "\n") or (
                        self.output[process.id]
                        and self.output[process.id][-1][-1] != "\n"
                    ):
                        output += "\n"
                    output += f"{self.colours.dim_on}=>{self.colours.dim_off} \n{self.colours.dim_on}=>{self.colours.dim_off} {self.colours.yellow_bold}Interrupt!{self.colours.reset_colour}\n{self.colours.dim_on}=>{self.colours.dim_off} \n"
                    interrupted = True

            if output:
                print(output, end="", flush=True)

            if len(self.completed_processes) == len(self.processes):
                break

            time.sleep(0.01)

        if self.interrupt_count == 2:
            print(
                f"{self.colours.dim_on}=>{self.colours.dim_off} {self.colours.red_bold}Abort!{self.colours.reset_colour}",
                flush=True,
            )

        if not self.exit_code and not self.passed:
            self.exit_code = 1

        return self.exit_code

    def _prefix(self, output: str, keepend: bool = True) -> str:
        prefixed_output = "\n".join(
            f"{self.colours.dim_on}=>{self.colours.dim_off} {line}{self.colours.reset_colour}"
            for line in output.splitlines()
        )
        if keepend and output and output[-1] == "\n":
            prefixed_output += "\n"
        return prefixed_output

    def _get_command_status(
        self,
        process: Process,
        icon: str | None = None,
        passed: bool | None = None,
        timer: bool = False,
    ) -> str:
        if passed is True:
            colour = self.colours.green_bold
            msg = "done"
            icon = icon or constants.TICK
        elif passed is False:
            colour = self.colours.red_bold
            msg = "failed"
            icon = icon or constants.X
        else:
            colour = self.colours.white_bold
            msg = "running"
            icon = icon or ""
            if not icon:
                msg += "..."

        output = f"{self.colours.dim_on}=>{self.colours.dim_off} {self.colours.white_bold}[{self.colours.reset_colour}{self.colours.blue_bold}{process.command}{self.colours.reset_colour}{self.colours.white_bold}]{self.colours.reset_colour}{colour} {msg} {icon}{self.colours.reset_colour}"

        if timer:
            end = process.end
            if not process.end:
                end = time.perf_counter()
            elapsed = end - process.start
            output += f" {self.colours.dim_on}({format_time_taken(elapsed)}){self.colours.dim_off}"

        return output

    def handle_signal(self, signum: int) -> None:
        for process in self.processes:
            if self.interrupt_count == 0:
                process.interrupt()
            else:
                process.kill()

        self.exit_code = 128 + signum
        self.interrupt_count += 1

    @classmethod
    def from_commands(
        cls,
        *commands: str,
        colours: Colours | None = None,
        debug: bool = False,
        interactive: bool = False,
        timer: bool = False,
    ) -> ProcessGroup:
        colours = colours or Colours()
        processes: list[Process] = []
        errors: list[InvalidExecutableError] = []

        for i, command in enumerate(commands):
            try:
                processes.append(Process(i + 1, command))
            except InvalidExecutableError as e:
                errors.append(e)

        if errors:
            raise InvalidExecutableErrors(*errors)

        process_group = cls(
            processes=processes,
            debug=debug,
            interactive=interactive,
            timer=timer,
            colours=colours,
        )

        return process_group

    def complete_output(self, all: bool = False) -> str:
        num_processes = len(self.processes)
        lines = constants.LINES() - (2 * num_processes)
        remainder = lines % num_processes
        tail = lines // num_processes
        for i in range(num_processes):
            self.process_lines[i] = tail
        if remainder:
            self.process_lines[-1] += remainder - 2
        else:
            self.process_lines[-1] -= 2

        output = ""
        for i, process in enumerate(self.processes, start=1):
            if process.poll() is not None:
                self.completed_processes.add(process.id)
                if process.return_code() != 0:
                    self.passed = False
                output += self._get_command_status(
                    process,
                    passed=process.return_code() == 0,
                    timer=self.timer,
                )
                output += "\n"
            else:
                output += self._get_command_status(
                    process,
                    icon=constants.ICONS[self.icon],
                    timer=self.timer,
                )
                output += "\n"

            process_output = process.read().decode()
            if not self.output[process.id]:
                self.output[process.id].append("")
            self.output[process.id][0] += process_output
            process_output = self.output[process.id][0]
            if process_output:
                if not all:
                    process_output = "\n".join(
                        process_output.splitlines()[-self.process_lines[i - 1] :]
                    )
                    process_output += "\n"
                output += self._prefix(process_output)
                if output and output[-1] != "\n":
                    output += "\n"
                if i != num_processes:
                    output += "\n"

        if self.interrupt_count == 0:
            return output

        if self.interrupt_count == 1:
            output += (
                f"\n{self.colours.yellow_bold}Interrupt!{self.colours.reset_colour}"
            )
        elif self.interrupt_count == 2:
            output += f"\n{self.colours.red_bold}Abort!{self.colours.reset_colour}"

        return output
