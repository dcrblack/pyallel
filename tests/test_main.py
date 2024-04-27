import os
import re
import signal
import subprocess
import time

import pytest
from pyallel import main
from pytest import CaptureFixture, MonkeyPatch


def prettify_error(out: str) -> str:
    return f"Got an error\n\n{out}"


PREFIX = "=> "


class TestInteractiveMode:
    """Test interactive mode that re-writes terminal output

    NOTE: These tests can only verify the exit code consistently
    as terminal output is re-written which isn't easy to consistently assert against
    """

    @pytest.fixture(autouse=True)
    def in_tty(self, monkeypatch: MonkeyPatch) -> None:
        ## Trick pyallel into thinking we are in an interactive terminal
        ## so we can test the interactive mode
        monkeypatch.setattr(main.constants, "IN_TTY", True)  # type: ignore[attr-defined]

    def test_run_single_command(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo hi", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_single_command_with_output(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo hi", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_single_command_failure(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("exit 1", "-t")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)

    def test_run_single_command_with_env(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("TEST_VAR=1 echo hi", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_multiple_commands(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("sleep 0.1; echo first", "echo hi", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_multiple_commands_single_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("exit 1", "echo hi", "-t")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)

    def test_run_multiple_commands_multiple_failures(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        exit_code = main.run("exit 1", "exit 1", "-t")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)

    def test_run_mulitiple_dependant_commands(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("echo first", ":::", "echo hi", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_mulitiple_dependant_commands_single_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("exit 1", ":::", "echo hi", "-t")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)

    def test_run_debug_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo hi", "-t", "-d")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_timer_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo hi")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_handles_running_pyallel_within_pyallel(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run(
            "pyallel ./tests/assets/test_handle_multiple_signals.sh -t", "-t"
        )
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    @pytest.mark.parametrize(
        "signal,exit_code", ((signal.SIGINT, 130), (signal.SIGTERM, 143))
    )
    def test_handles_multiple_signals(self, signal: int, exit_code: int) -> None:
        process = subprocess.Popen(
            [
                "pyallel",
                "./tests/assets/test_handle_multiple_signals.sh",
            ],
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        time.sleep(0.3)
        process.send_signal(signal)
        time.sleep(0.1)
        process.send_signal(signal)
        assert process.wait() == exit_code

    @pytest.mark.parametrize(
        "signal,exit_code", ((signal.SIGINT, 130), (signal.SIGTERM, 143))
    )
    def test_handles_multiple_signals_with_dependant_commands(
        self, signal: int, exit_code: int
    ) -> None:
        process = subprocess.Popen(
            [
                "pyallel",
                "./tests/assets/test_handle_multiple_signals.sh",
                ":::",
                "./tests/assets/test_handle_multiple_signals.sh",
            ],
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        time.sleep(0.3)
        process.send_signal(signal)
        time.sleep(0.1)
        process.send_signal(signal)
        assert process.wait() == exit_code


class TestNonInteractiveMode:
    def test_run_single_command(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo hi", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[echo hi] running... \n",
                f"{PREFIX}hi\n",
                f"{PREFIX}[echo hi] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}Done!\n",
            ]
        )

    def test_run_single_command_failure(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("exit 1", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[exit 1] running... \n",
                f"{PREFIX}[exit 1] failed ✘\n",
                f"{PREFIX}\n",
                f"{PREFIX}Failed!\n",
            ]
        )

    def test_run_single_command_with_env(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("TEST_VAR=1 echo hi", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[TEST_VAR=1 echo hi] running... \n",
                f"{PREFIX}hi\n",
                f"{PREFIX}[TEST_VAR=1 echo hi] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}Done!\n",
            ]
        )

    def test_run_multiple_commands(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("sleep 0.1; echo first", "echo hi", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[sleep 0.1; echo first] running... \n",
                f"{PREFIX}first\n",
                f"{PREFIX}[sleep 0.1; echo first] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}[echo hi] running... \n",
                f"{PREFIX}hi\n",
                f"{PREFIX}[echo hi] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}Done!\n",
            ]
        )

    def test_run_multiple_commands_single_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("exit 1", "echo hi", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[exit 1] running... \n",
                f"{PREFIX}[exit 1] failed ✘\n",
                f"{PREFIX}\n",
                f"{PREFIX}[echo hi] running... \n",
                f"{PREFIX}hi\n",
                f"{PREFIX}[echo hi] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}Failed!\n",
            ]
        )

    def test_run_multiple_commands_multiple_failures(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        exit_code = main.run("exit 1", "exit 1", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[exit 1] running... \n",
                f"{PREFIX}[exit 1] failed ✘\n",
                f"{PREFIX}\n",
                f"{PREFIX}[exit 1] running... \n",
                f"{PREFIX}[exit 1] failed ✘\n",
                f"{PREFIX}\n",
                f"{PREFIX}Failed!\n",
            ]
        )

    def test_run_mulitiple_dependant_commands(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("echo first", ":::", "echo hi", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[echo first] running... \n",
                f"{PREFIX}first\n",
                f"{PREFIX}[echo first] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}[echo hi] running... \n",
                f"{PREFIX}hi\n",
                f"{PREFIX}[echo hi] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}Done!\n",
            ]
        )

    def test_run_mulitiple_dependant_commands_single_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("exit 1", ":::", "echo hi", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[exit 1] running... \n",
                f"{PREFIX}[exit 1] failed ✘\n",
                f"{PREFIX}\n",
                f"{PREFIX}Failed!\n",
            ]
        )

    def test_run_debug_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo hi", "-n", "-t", "-d")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}DEBUG log: debug.log\n",
                f"{PREFIX}\n",
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[echo hi] running... \n",
                f"{PREFIX}hi\n",
                f"{PREFIX}[echo hi] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}Done!\n",
            ]
        )

    def test_run_timer_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo hi", "-n")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert (
            re.search(
                "".join(
                    [
                        f"{PREFIX}Running commands...\n",
                        f"{PREFIX}\n",
                        rf"{PREFIX}\[echo hi\] running... \n",
                        f"{PREFIX}hi\n",
                        rf"{PREFIX}\[echo hi\] done ✔ \(0\..*\)\n",
                        f"{PREFIX}\n",
                        f"{PREFIX}Done!\n",
                    ]
                ),
                captured.out,
            )
            is not None
        ), prettify_error(captured.out)

    def test_run_with_longer_first_command(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("sleep 1", "echo hi", "-n")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert (
            re.search(
                "".join(
                    [
                        f"{PREFIX}Running commands...\n",
                        f"{PREFIX}\n",
                        rf"{PREFIX}\[sleep 1\] running... \n",
                        rf"{PREFIX}\[sleep 1\] done ✔ \(1\..*s\)\n",
                        f"{PREFIX}\n",
                        rf"{PREFIX}\[echo hi\] running... \n",
                        f"{PREFIX}hi\n",
                        rf"{PREFIX}\[echo hi\] done ✔ \(0\..*s\)\n",
                        f"{PREFIX}\n",
                        f"{PREFIX}Done!\n",
                    ]
                ),
                captured.out,
            )
            is not None
        ), prettify_error(captured.out)

    def test_handles_running_pyallel_within_pyallel(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run(
            "pyallel ./tests/assets/test_handle_multiple_signals.sh -t", "-n", "-t"
        )
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[pyallel ./tests/assets/test_handle_multiple_signals.sh -t] running... \n",
                f"{PREFIX}{PREFIX}Running commands...\n",
                f"{PREFIX}{PREFIX}\n",
                f"{PREFIX}{PREFIX}[./tests/assets/test_handle_multiple_signals.sh] running... \n",
                f"{PREFIX}{PREFIX}hi\n",
                f"{PREFIX}{PREFIX}bye\n",
                f"{PREFIX}{PREFIX}[./tests/assets/test_handle_multiple_signals.sh] done ✔\n",
                f"{PREFIX}{PREFIX}\n",
                f"{PREFIX}{PREFIX}Done!\n",
                f"{PREFIX}[pyallel ./tests/assets/test_handle_multiple_signals.sh -t] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}Done!\n",
            ]
        )

    @pytest.mark.parametrize("wait", ["0.1", "0.5"])
    def test_handles_single_command_output_with_delayed_newlines(
        self, capsys: CaptureFixture[str], wait: str
    ) -> None:
        exit_code = main.run(f"printf hi; sleep {wait}; echo bye", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[printf hi; sleep {wait}; echo bye] running... \n",
                f"{PREFIX}hibye\n",
                f"{PREFIX}[printf hi; sleep {wait}; echo bye] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}Done!\n",
            ]
        )

    @pytest.mark.parametrize("wait", ["0.1", "0.5"])
    def test_handles_multiple_command_output_with_delayed_newlines(
        self, capsys: CaptureFixture[str], wait: str
    ) -> None:
        exit_code = main.run(
            f"printf hi; sleep {wait}; echo bye",
            f"printf hi; sleep {wait}; echo bye",
            "-n",
            "-t",
        )
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out.splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[printf hi; sleep {wait}; echo bye] running... \n",
                f"{PREFIX}hibye\n",
                f"{PREFIX}[printf hi; sleep {wait}; echo bye] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}[printf hi; sleep {wait}; echo bye] running... \n",
                f"{PREFIX}hibye\n",
                f"{PREFIX}[printf hi; sleep {wait}; echo bye] done ✔\n",
                f"{PREFIX}\n",
                f"{PREFIX}Done!\n",
            ]
        )

    @pytest.mark.parametrize(
        "signal,exit_code", ((signal.SIGINT, 130), (signal.SIGTERM, 143))
    )
    def test_handles_multiple_signals(self, signal: int, exit_code: int) -> None:
        process = subprocess.Popen(
            [
                "pyallel",
                "./tests/assets/test_handle_multiple_signals.sh",
                "-n",
                "-t",
            ],
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        time.sleep(0.3)
        process.send_signal(signal)
        time.sleep(0.1)
        process.send_signal(signal)
        assert process.stdout is not None
        out = process.stdout.read()
        assert process.wait() == exit_code, prettify_error(out.decode())
        assert out.decode().splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[./tests/assets/test_handle_multiple_signals.sh] running... \n",
                f"{PREFIX}hi\n",
                f"{PREFIX}\n",
                f"{PREFIX}Interrupt!\n",
                f"{PREFIX}\n",
                f"{PREFIX}[./tests/assets/test_handle_multiple_signals.sh] failed ✘\n",
                f"{PREFIX}\n",
                f"{PREFIX}Abort!\n",
            ]
        )

    @pytest.mark.parametrize(
        "signal,exit_code", ((signal.SIGINT, 130), (signal.SIGTERM, 143))
    )
    def test_handles_multiple_signals_with_dependant_commands(
        self, signal: int, exit_code: int
    ) -> None:
        process = subprocess.Popen(
            [
                "pyallel",
                "./tests/assets/test_handle_multiple_signals.sh",
                ":::",
                "./tests/assets/test_handle_multiple_signals.sh",
                "-n",
                "-t",
            ],
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        time.sleep(0.3)
        process.send_signal(signal)
        time.sleep(0.1)
        process.send_signal(signal)
        assert process.stdout is not None
        out = process.stdout.read()
        assert process.wait() == exit_code, prettify_error(out.decode())
        assert out.decode().splitlines(keepends=True) == (
            [
                f"{PREFIX}Running commands...\n",
                f"{PREFIX}\n",
                f"{PREFIX}[./tests/assets/test_handle_multiple_signals.sh] running... \n",
                f"{PREFIX}hi\n",
                f"{PREFIX}\n",
                f"{PREFIX}Interrupt!\n",
                f"{PREFIX}\n",
                f"{PREFIX}[./tests/assets/test_handle_multiple_signals.sh] failed ✘\n",
                f"{PREFIX}\n",
                f"{PREFIX}Abort!\n",
            ]
        )
