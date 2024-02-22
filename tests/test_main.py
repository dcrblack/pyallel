import os
import signal
import subprocess
import time
from pyallel import main
from pytest import CaptureFixture

import pytest


def prettify_error(out: str) -> str:
    return f"Got an error\n\n{out}"


PREFIX = "=> "


class TestNonStreamedMode:
    def test_run_single_command(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_single_command_failure(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run('sh -c "exit 1"', "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "A command failed!\n",
            ]
        )

    def test_run_single_command_with_env(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("TEST_VAR=1 echo 'hi'", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_multiple_commands(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("sh -c 'sleep 0.1; echo \"first\"'", "echo 'hi'", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "[sh] done ✓ (0.1s)\n",
                f"{PREFIX}first\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_multiple_commands_single_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run('sh -c "exit 1"', 'echo "hi"', "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "[echo] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "A command failed!\n",
            ]
        )

    def test_run_multiple_commands_multiple_failures(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        exit_code = main.run('sh -c "exit 1"', 'sh -c "exit 1"', "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "A command failed!\n",
            ]
        )

    def test_run_verbose_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-V", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo hi] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_no_timer_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-t", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] done ✓\n",
                f"{PREFIX}hi\n",
                "\n",
                "Success!\n",
            ]
        )

    @pytest.mark.parametrize("wait", ["0.1", "0.5"])
    def test_handles_single_command_output_with_delayed_newlines(
        self, capsys: CaptureFixture[str], wait: str
    ) -> None:
        exit_code = main.run(f"sh -c 'printf hi; sleep {wait}; echo bye'", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                f"[sh] done ✓ ({wait}s)\n",
                f"{PREFIX}hibye\n",
                "\n",
                "Success!\n",
            ]
        )

    @pytest.mark.parametrize("wait", ["0.1", "0.5"])
    def test_handles_multiple_command_output_with_delayed_newlines(
        self, capsys: CaptureFixture[str], wait: str
    ) -> None:
        exit_code = main.run(
            f"sh -c 'printf hi; sleep {wait}; echo bye'",
            f"sh -c 'printf hi; sleep {wait}; echo bye'",
            "-s",
        )
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                f"[sh] done ✓ ({wait}s)\n",
                f"{PREFIX}hibye\n",
                "\n",
                f"[sh] done ✓ ({wait}s)\n",
                f"{PREFIX}hibye\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_handles_invalid_executable(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("invalid_exe", "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "Error: executables [invalid_exe] were not found\n"

    def test_handles_many_invalid_executables(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("invalid_exe", "other_invalid_exe", "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert (
            captured.out
            == "Error: executables [invalid_exe, other_invalid_exe] were not found\n"
        )

    def test_does_not_run_executables_on_parsing_error(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("invalid_exe", "other_invalid_exe", "sleep 10", "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert (
            captured.out
            == "Error: executables [invalid_exe, other_invalid_exe] were not found\n"
        )
        status = subprocess.run(["pgrep", "-f", "^sleep 10$"])
        assert status.returncode == 1, "sleep shouldn't be running!"


class TestNonStreamedNonInteractiveMode:
    def test_run_single_command(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_single_command_failure(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run('sh -c "exit 1"', "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "A command failed!\n",
            ]
        )

    def test_run_single_command_with_env(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("TEST_VAR=1 echo 'hi'", "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_multiple_commands(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run(
            "sh -c 'sleep 0.1; echo \"first\"'", "echo 'hi'", "-n", "-s"
        )
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "[sh] done ✓ (0.1s)\n",
                f"{PREFIX}first\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_multiple_commands_single_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run('sh -c "exit 1"', 'echo "hi"', "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "[echo] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "A command failed!\n",
            ]
        )

    def test_run_multiple_commands_multiple_failures(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        exit_code = main.run('sh -c "exit 1"', 'sh -c "exit 1"', "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "A command failed!\n",
            ]
        )

    def test_run_verbose_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-V", "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo hi] done ✓ (0.0s)\n",
                f"{PREFIX}hi\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_no_timer_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-t", "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] done ✓\n",
                f"{PREFIX}hi\n",
                "\n",
                "Success!\n",
            ]
        )

    @pytest.mark.parametrize("wait", ["0.1", "0.5"])
    def test_handles_single_command_output_with_delayed_newlines(
        self, capsys: CaptureFixture[str], wait: str
    ) -> None:
        exit_code = main.run(f"sh -c 'printf hi; sleep {wait}; echo bye'", "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                f"[sh] done ✓ ({wait}s)\n",
                f"{PREFIX}hibye\n",
                "\n",
                "Success!\n",
            ]
        )

    @pytest.mark.parametrize("wait", ["0.1", "0.5"])
    def test_handles_multiple_command_output_with_delayed_newlines(
        self, capsys: CaptureFixture[str], wait: str
    ) -> None:
        exit_code = main.run(
            f"sh -c 'printf hi; sleep {wait}; echo bye'",
            f"sh -c 'printf hi; sleep {wait}; echo bye'",
            "-n",
            "-s",
        )
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                f"[sh] done ✓ ({wait}s)\n",
                f"{PREFIX}hibye\n",
                "\n",
                f"[sh] done ✓ ({wait}s)\n",
                f"{PREFIX}hibye\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_handles_invalid_executable(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("invalid_exe", "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "Error: executables [invalid_exe] were not found\n"

    def test_handles_many_invalid_executables(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("invalid_exe", "other_invalid_exe", "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert (
            captured.out
            == "Error: executables [invalid_exe, other_invalid_exe] were not found\n"
        )

    def test_does_not_run_executables_on_parsing_error(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("invalid_exe", "other_invalid_exe", "sleep 10", "-n", "-s")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert (
            captured.out
            == "Error: executables [invalid_exe, other_invalid_exe] were not found\n"
        )
        status = subprocess.run(["pgrep", "-f", "^sleep 10$"])
        assert status.returncode == 1, "sleep shouldn't be running!"


class TestStreamedMode:
    """Test streamed mode with interactivity

    NOTE: These tests can only verify the exit code consistently
    as terminal output is re-written which isn't easy to consistently assert against
    """

    def test_run_single_command(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_single_command_with_output(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_single_command_failure(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run('sh -c "exit 1"')
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)

    def test_run_single_command_with_env(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("TEST_VAR=1 echo 'hi'")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_multiple_commands(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("sh -c 'sleep 0.1; echo \"first\"'", "echo 'hi'")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_multiple_commands_single_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run('sh -c "exit 1"', 'echo "hi"')
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)

    def test_run_multiple_commands_multiple_failures(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        exit_code = main.run('sh -c "exit 1"', 'sh -c "exit 1"')
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)

    def test_run_verbose_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-V")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_run_no_timer_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)

    def test_handles_invalid_executable(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("invalid_exe")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "Error: executables [invalid_exe] were not found\n"

    def test_handles_many_invalid_executables(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("invalid_exe", "other_invalid_exe")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert (
            captured.out
            == "Error: executables [invalid_exe, other_invalid_exe] were not found\n"
        )

    def test_does_not_run_executables_on_parsing_error(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("invalid_exe", "other_invalid_exe", "sleep 10")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert (
            captured.out
            == "Error: executables [invalid_exe, other_invalid_exe] were not found\n"
        )
        status = subprocess.run(["pgrep", "-f", "^sleep 10$"])
        assert status.returncode == 1, "sleep shouldn't be running!"

    def test_handles_interrupt_signal(self) -> None:
        process = subprocess.Popen(
            ["pyallel", "./tests/assets/test_process_interrupt_with_trapped_output.sh"],
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        time.sleep(0.5)
        process.send_signal(signal.SIGINT)
        assert process.wait() == 2


class TestStreamedNonInteractiveMode:
    def test_run_single_command(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-n")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] running... \n",
                f"{PREFIX}hi\n",
                "[echo] done ✓ (0.0s)\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_single_command_failure(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run('sh -c "exit 1"', "-n")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] running... \n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "A command failed!\n",
            ]
        )

    def test_run_single_command_with_env(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("TEST_VAR=1 echo 'hi'", "-n")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] running... \n",
                f"{PREFIX}hi\n",
                "[echo] done ✓ (0.0s)\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_multiple_commands(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("sh -c 'sleep 0.1; echo \"first\"'", "echo 'hi'", "-n")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] running... \n",
                f"{PREFIX}first\n",
                "[sh] done ✓ (0.1s)\n",
                "\n",
                "[echo] running... \n",
                f"{PREFIX}hi\n",
                "[echo] done ✓ (0.0s)\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_multiple_commands_single_failure(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run('sh -c "exit 1"', 'echo "hi"', "-n")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] running... \n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "[echo] running... \n",
                f"{PREFIX}hi\n",
                "[echo] done ✓ (0.0s)\n",
                "\n",
                "A command failed!\n",
            ]
        )

    def test_run_multiple_commands_multiple_failures(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        exit_code = main.run('sh -c "exit 1"', 'sh -c "exit 1"', "-n")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] running... \n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "[sh] running... \n",
                "[sh] failed ✗ (0.0s)\n",
                "\n",
                "A command failed!\n",
            ]
        )

    def test_run_verbose_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-n", "-V")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo hi] running... \n",
                f"{PREFIX}hi\n",
                "[echo hi] done ✓ (0.0s)\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_no_timer_mode(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("echo 'hi'", "-n", "-t")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[echo] running... \n",
                f"{PREFIX}hi\n",
                "[echo] done ✓\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_run_with_longer_first_command(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("sleep 1", "echo 'hi'", "-n")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sleep] running... \n",
                "[sleep] done ✓ (1.0s)\n",
                "\n",
                "[echo] running... \n",
                f"{PREFIX}hi\n",
                "[echo] done ✓ (0.0s)\n",
                "\n",
                "Success!\n",
            ]
        )

    @pytest.mark.parametrize("wait", ["0.1", "0.5"])
    def test_handles_single_command_output_with_delayed_newlines(
        self, capsys: CaptureFixture[str], wait: str
    ) -> None:
        exit_code = main.run(f"sh -c 'printf hi; sleep {wait}; echo bye'", "-n")
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] running... \n",
                f"{PREFIX}hibye\n",
                f"[sh] done ✓ ({wait}s)\n",
                "\n",
                "Success!\n",
            ]
        )

    @pytest.mark.parametrize("wait", ["0.1", "0.5"])
    def test_handles_multiple_command_output_with_delayed_newlines(
        self, capsys: CaptureFixture[str], wait: str
    ) -> None:
        exit_code = main.run(
            f"sh -c 'printf hi; sleep {wait}; echo bye'",
            f"sh -c 'printf hi; sleep {wait}; echo bye'",
            "-n",
        )
        captured = capsys.readouterr()
        assert exit_code == 0, prettify_error(captured.out)
        assert captured.out == "".join(
            [
                "Running commands...\n",
                "\n",
                "[sh] running... \n",
                f"{PREFIX}hibye\n",
                f"[sh] done ✓ ({wait}s)\n",
                "\n",
                "[sh] running... \n",
                f"{PREFIX}hibye\n",
                f"[sh] done ✓ ({wait}s)\n",
                "\n",
                "Success!\n",
            ]
        )

    def test_handles_invalid_executable(self, capsys: CaptureFixture[str]) -> None:
        exit_code = main.run("invalid_exe", "-n")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert captured.out == "Error: executables [invalid_exe] were not found\n"

    def test_handles_many_invalid_executables(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("invalid_exe", "other_invalid_exe", "-n")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert (
            captured.out
            == "Error: executables [invalid_exe, other_invalid_exe] were not found\n"
        )

    def test_does_not_run_executables_on_parsing_error(
        self, capsys: CaptureFixture[str]
    ) -> None:
        exit_code = main.run("invalid_exe", "other_invalid_exe", "sleep 10", "-n")
        captured = capsys.readouterr()
        assert exit_code == 1, prettify_error(captured.out)
        assert (
            captured.out
            == "Error: executables [invalid_exe, other_invalid_exe] were not found\n"
        )
        status = subprocess.run(["pgrep", "-f", "^sleep 10$"])
        assert status.returncode == 1, "sleep shouldn't be running!"

    def test_handles_interrupt_signal(self) -> None:
        process = subprocess.Popen(
            [
                "pyallel",
                "./tests/assets/test_process_interrupt_with_trapped_output.sh",
                "-n",
            ],
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        time.sleep(0.5)
        process.send_signal(signal.SIGINT)
        assert process.stdout is not None
        out = process.stdout.read()
        assert process.wait() == 2, prettify_error(out.decode())
        assert out.decode() == "".join(
            [
                "Running commands...\n",
                "\n",
                "[./tests/assets/test_process_interrupt_with_trapped_output.sh] running... \n",
                f"{PREFIX}hi\n",
                f"{PREFIX}error\n",
                "[./tests/assets/test_process_interrupt_with_trapped_output.sh] failed ✗ (1.0s)\n",
                "\n",
                "Interrupt!\n",
            ]
        )
