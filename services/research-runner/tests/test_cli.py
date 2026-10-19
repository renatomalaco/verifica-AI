import subprocess
import sys


def test_cli_gate_cascade_passes():
    result = subprocess.run(
        [sys.executable, "-m", "research_runner", "--mode", "cascade", "--threshold-f1", "0.92"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "F1-Score" in result.stdout
    assert "GATE CIENTIFICO: APROVADO" in result.stdout


def test_cli_gate_high_threshold_fails():
    result = subprocess.run(
        [sys.executable, "-m", "research_runner", "--mode", "heuristic", "--threshold-f1", "0.95"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "GATE CIENTIFICO: REPROVADO" in result.stdout


def test_cli_all_modes_outputs_table():
    result = subprocess.run(
        [sys.executable, "-m", "research_runner", "--mode", "all"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Modo 1" in result.stdout
    assert "Modo 3" in result.stdout
