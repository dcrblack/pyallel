from __future__ import annotations

from typing import Any
import pytest
from pyallel.colours import Colours
from pyallel.printer import Printer, get_num_lines, set_process_lines
from pyallel.process import Process, ProcessOutput
from pyallel.process_group import ProcessGroupOutput


@pytest.mark.parametrize(
    "output,columns,expected",
    (
        pytest.param("Hello Mr Anderson", 20, 1, id="output fits within 20 columns"),
        pytest.param(
            "Hello Mr Anderson\nIt is inevitable",
            20,
            2,
            id="output wraps over 2 lines with 20 columns",
        ),
        pytest.param(
            "Hello Mr Anderson\nIt is inevitable\nHAHAHAHAH",
            20,
            3,
            id="output wraps over 3 lines with 20 columns",
        ),
    ),
)
def test_get_num_lines(output: str, columns: int, expected: int) -> None:
    assert get_num_lines(output, columns) == expected


@pytest.mark.parametrize("columns,lines", ((8, 3), (5, 4)))
def test_get_num_lines_with_columns(columns: int, lines: int) -> None:
    assert get_num_lines("Hello Mr Anderson", columns=columns) == lines


def test_get_num_lines_with_long_command() -> None:
    # First line is a 800 length string, which divides evenly into `200`
    line = "long" * 200
    assert get_num_lines(f"{line}\nLong output", columns=200) == 5


def test_get_num_lines_with_long_line() -> None:
    assert get_num_lines(" " * 250, columns=200) == 2


@pytest.mark.parametrize("chars", ["\x1B[0m", "\x1B(B"])
def test_get_num_lines_ignores_ansi_chars(chars: str) -> None:
    assert get_num_lines(chars * 100, columns=10) == 1


def test_set_process_lines() -> None:
    output = ProcessGroupOutput(
        id=1,
        processes=[ProcessOutput(id=1, process=Process(1, "echo first; echo second"))],
    )

    set_process_lines(output, lines=58)

    assert output.processes[0].process.lines == 58


@pytest.mark.parametrize(
    "lines,expected_lines1,expected_lines2,expected_lines3",
    (
        pytest.param(59, 53, 3, 3, id="59 lines shared between 3 processes"),
        pytest.param(50, 44, 3, 3, id="50 lines shared between 3 processes"),
        pytest.param(31, 25, 3, 3, id="31 lines shared between 3 processes"),
    ),
)
def test_set_process_lines_shares_lines_across_processes(
    lines: int, expected_lines1: int, expected_lines2: int, expected_lines3: int
) -> None:
    output = ProcessGroupOutput(
        id=1,
        processes=[
            ProcessOutput(
                id=1,
                process=Process(1, "echo first; echo second"),
                data="first\nsecond",
            ),
            ProcessOutput(
                id=2,
                process=Process(2, "echo first; echo second"),
                data="first\nsecond",
            ),
            ProcessOutput(
                id=3,
                process=Process(3, "echo first; echo second"),
                data="first\nsecond",
            ),
        ],
    )

    set_process_lines(output, lines=lines)

    assert output.processes[0].process.lines == expected_lines1
    assert output.processes[1].process.lines == expected_lines2
    assert output.processes[2].process.lines == expected_lines3


def test_set_process_lines_shares_lines_across_many_more_processes() -> None:
    output = ProcessGroupOutput(
        id=1,
        processes=[
            ProcessOutput(id=i, process=Process(i, "echo first; echo second"))
            for i in range(1, 60)
        ],
    )

    set_process_lines(output, lines=59)

    for i in range(59):
        assert output.processes[i].process.lines == 1, f"process index {i}"


@pytest.mark.parametrize(
    "lines,lines1,lines2,lines3,expected_lines1,expected_lines2,expected_lines3",
    (
        pytest.param(
            59,
            0.4,
            0.2,
            0.2,
            37,
            11,
            11,
            id="59 lines shared between 3 processes with remainder given to process with most lines",
        ),
        pytest.param(
            59, 1.0, 0.0, 0.0, 59, 0, 0, id="All lines given to first process"
        ),
        pytest.param(59, 0.5, 0.0, 0.0, 57, 1, 1, id="57 lines given to first process"),
    ),
)
def test_set_process_lines_with_fixed_and_dynamic_lines(
    lines: int,
    lines1: float,
    lines2: float,
    lines3: float,
    expected_lines1: int,
    expected_lines2: int,
    expected_lines3: int,
) -> None:
    output = ProcessGroupOutput(
        id=1,
        processes=[
            ProcessOutput(id=1, process=Process(1, "echo first; echo second", lines1)),
            ProcessOutput(id=2, process=Process(2, "echo first; echo second", lines2)),
            ProcessOutput(id=3, process=Process(3, "echo first; echo second", lines3)),
        ],
    )

    set_process_lines(output, lines=lines)

    assert output.processes[0].process.lines == expected_lines1
    assert output.processes[1].process.lines == expected_lines2
    assert output.processes[2].process.lines == expected_lines3


@pytest.mark.parametrize(
    "kwargs,lines,expected",
    (
        pytest.param(
            {},
            0,
            [
                (False, "[echo first; echo second] done ✔", "\n"),
                (True, "first", "\n"),
                (True, "second", "\n"),
            ],
            id="no flags and no lines yields all output",
        ),
        pytest.param(
            {"tail_output": True},
            0,
            [],
            id="tail output with no lines",
        ),
        pytest.param(
            {"tail_output": True},
            1,
            [(False, "[echo first; echo second] done ✔", "\n")],
            id="tail output with 1 line yields only command status line",
        ),
        pytest.param(
            {"tail_output": True},
            3,
            [
                (False, "[echo first; echo second] done ✔", "\n"),
                (True, "first", "\n"),
                (True, "second", "\n"),
            ],
            id="tail output with 3 lines yields command status line plus 2 output lines",
        ),
    ),
)
def test_printer_generate_process_output(
    kwargs: dict[str, Any], lines: int, expected: list[tuple[bool, str, str]]
) -> None:
    printer = Printer(colours=Colours.from_colour("no"))
    process = Process(1, "echo first; echo second")
    process.lines = lines
    process.run()
    process.wait()

    output = printer.generate_process_output(
        ProcessOutput(id=1, process=process, data="first\nsecond\n"),
        **kwargs,
    )

    assert output == expected


@pytest.mark.parametrize(
    "kwargs,expected",
    (
        pytest.param(
            {},
            "[echo first; echo second] done ✔",
            id="no flags yields done command status",
        ),
        pytest.param(
            {"include_progress": False},
            "[echo first; echo second] running... ",
            id="don't include progress yields running status",
        ),
        pytest.param(
            {"include_timer": True},
            "[echo first; echo second] done ✔ (0.0s)",
            id="include timer yields timer",
        ),
    ),
)
def test_printer_generate_process_output_status(
    kwargs: dict[str, Any], expected: str
) -> None:
    printer = Printer(colours=Colours.from_colour("no"))
    process = Process(1, "echo first; echo second")
    process.run()
    process.wait()

    output = printer.generate_process_output_status(
        ProcessOutput(id=1, process=process, data="first\nsecond\n"), **kwargs
    )

    assert output == expected


def test_printer_generate_process_group_output() -> None:
    printer = Printer(colours=Colours.from_colour("no"))
    process1 = Process(1, "echo first; echo second")
    process2 = Process(1, "echo third; echo fourth")
    process1.run()
    process2.run()
    process1.wait()
    process2.wait()

    output = printer.generate_process_group_output(
        ProcessGroupOutput(
            id=1,
            processes=[
                ProcessOutput(id=1, process=process1, data="first\nsecond\n"),
                ProcessOutput(id=2, process=process2, data="third\nfourth\n"),
            ],
        ),
    )

    assert output == [
        (False, "[echo first; echo second] done ✔", "\n"),
        (True, "first", "\n"),
        (True, "second", "\n"),
        (False, "[echo third; echo fourth] done ✔", "\n"),
        (True, "third", "\n"),
        (True, "fourth", "\n"),
    ]
