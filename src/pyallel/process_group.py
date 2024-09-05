from __future__ import annotations

from typing import Sequence

from pyallel.errors import InvalidExecutableError, InvalidExecutableErrors
from pyallel.process import Process, ProcessOutput


class ProcessGroupOutput:
    def __init__(self, id: int, processes: Sequence[ProcessOutput]) -> None:
        self.id = id
        self.processes = processes

    def merge(self, other: ProcessGroupOutput) -> None:
        for i, _ in enumerate(self.processes):
            self.processes[i].merge(other.processes[i])


class ProcessGroup:
    def __init__(self, id: int, processes: list[Process]) -> None:
        self.id = id
        self.processes = processes
        self._exit_code: int = 0
        self._interrupt_count: int = 0

    def run(self) -> None:
        for process in self.processes:
            process.run()

    def poll(self) -> int | None:
        polls: list[int | None] = [process.poll() for process in self.processes]

        running = [p for p in polls if p is None]
        failed = [p for p in polls if p is not None and p > 0]

        if running:
            return None
        elif failed:
            return 1
        else:
            return 0

    def stream(self) -> ProcessGroupOutput:
        return ProcessGroupOutput(
            id=self.id,
            processes=[
                ProcessOutput(
                    id=process.id, process=process, data=process.read().decode()
                )
                for process in self.processes
            ],
        )

    def handle_signal(self, _signum: int) -> None:
        for process in self.processes:
            if self._interrupt_count == 0:
                process.interrupt()
            else:
                process.kill()

        self._interrupt_count += 1

    @classmethod
    def from_commands(cls, id: int, process_id: int, *commands: str) -> ProcessGroup:
        processes: list[Process] = []
        errors: list[InvalidExecutableError] = []

        for i, command in enumerate(commands):
            try:
                processes.append(Process(i + process_id, command))
            except InvalidExecutableError as e:
                errors.append(e)

        if errors:
            raise InvalidExecutableErrors(*errors)

        process_group = cls(id=id, processes=processes)

        return process_group
