from __future__ import annotations

import signal
import subprocess
import tempfile
import time
from typing import BinaryIO

from pyallel.errors import InvalidLinesModifierError


class ProcessOutput:
    def __init__(self, id: int, process: Process, data: str = "") -> None:
        self.id = id
        self.data = data
        self.lines = len(data.splitlines()) + 1
        self.process = process

    def merge(self, other: ProcessOutput) -> None:
        self.data += other.data
        self.lines += len(other.data.splitlines())


class Process:
    def __init__(self, id: int, command: str, percentage_lines: float = 0.0) -> None:
        self.id = id
        self.command = command
        self.start = 0.0
        self.end = 0.0
        self.lines = 0
        self.percentage_lines = percentage_lines
        self._fd: BinaryIO
        self._process: subprocess.Popen[bytes]

    def run(self) -> None:
        self.start = time.perf_counter()
        fd, fd_name = tempfile.mkstemp()
        self._fd = open(fd_name, "rb")
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.DEVNULL,
            stdout=fd,
            stderr=subprocess.STDOUT,
            shell=True,
        )

    def __del__(self) -> None:
        try:
            self._fd.close()
        except AttributeError:
            pass

    def poll(self) -> int | None:
        poll = self._process.poll()
        if poll is not None and not self.end:
            self.end = time.perf_counter()
        return poll

    def read(self) -> bytes:
        return self._fd.read()

    def readline(self) -> bytes:
        return self._fd.readline()

    def return_code(self) -> int | None:
        return self._process.returncode

    def interrupt(self) -> None:
        if hasattr(self, "_process"):
            self._process.send_signal(signal.SIGINT)

    def kill(self) -> None:
        if hasattr(self, "_process"):
            self._process.send_signal(signal.SIGKILL)

    def wait(self) -> int:
        return self._process.wait()

    @classmethod
    def from_command(cls, id: int, command: str) -> Process:
        cmd = command.split(" :: ", maxsplit=1)
        if len(cmd) == 1:
            return cls(id, cmd[0])

        args, *parts = cmd

        percentage_lines = 0
        for arg in args.split(" "):
            try:
                arg, value = args.split("=")
            except ValueError:
                continue

            if arg == "lines":
                try:
                    percentage_lines = int(value)
                except ValueError:
                    raise InvalidLinesModifierError(
                        "lines modifier must be a number between 1 and 100"
                    )

                if not 0 < percentage_lines <= 100:
                    raise InvalidLinesModifierError(
                        "lines modifier must be a number between 1 and 100"
                    )

                break

        return cls(id, " ".join(parts), round(percentage_lines / 100, 2))
