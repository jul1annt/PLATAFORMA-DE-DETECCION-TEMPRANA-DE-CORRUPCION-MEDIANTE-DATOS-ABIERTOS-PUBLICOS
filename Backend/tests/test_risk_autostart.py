"""Exercise the PowerShell installer with simulated task cmdlets, never Windows tasks."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


INSTALLER = Path(__file__).resolve().parents[1] / 'scripts/install_risk_autostart.ps1'
SHELL = shutil.which('powershell.exe') if os.name == 'nt' else None
pytestmark = pytest.mark.skipif(SHELL is None, reason='Windows PowerShell is required')

WRAPPER = r'''
param([string]$Installer,[string]$Root,[switch]$Run)
$ErrorActionPreference='Stop'
function global:Write-TestTrace($Value) {
    Add-Content -LiteralPath (Join-Path $Root 'trace.jsonl') -Value ($Value | ConvertTo-Json -Compress)
}
function global:Get-ScheduledTask {
    [CmdletBinding()]param()
    Write-TestTrace @{event='task-query'}
    $settings=Get-Content -LiteralPath (Join-Path $Root 'fake-settings.json') -Raw | ConvertFrom-Json
    if ($settings.existing_task) { [pscustomobject]@{TaskName='PDTC-Riesgo-Local'} }
}
function global:New-ScheduledTaskAction {
    param($Execute,$Argument)
    [pscustomobject]@{Execute=$Execute;Argument=$Argument}
}
function global:New-ScheduledTaskTrigger {
    param([switch]$AtLogOn,$User)
    [pscustomobject]@{AtLogOn=[bool]$AtLogOn;User=$User}
}
function global:New-ScheduledTaskPrincipal {
    param($UserId,$LogonType,$RunLevel)
    [pscustomobject]@{UserId=$UserId;LogonType=$LogonType;RunLevel=$RunLevel}
}
function global:New-ScheduledTaskSettingsSet {
    param([switch]$StartWhenAvailable,$MultipleInstances,[switch]$Hidden)
    [pscustomobject]@{StartWhenAvailable=[bool]$StartWhenAvailable;MultipleInstances=$MultipleInstances;Hidden=[bool]$Hidden}
}
function global:Register-ScheduledTask {
    param($TaskName,$Action,$Trigger,$Principal,$Settings)
    Write-TestTrace @{event='task-registration-simulated';name=$TaskName;action=$Action;trigger=$Trigger;principal=$Principal;settings=$Settings}
    [pscustomobject]@{TaskName=$TaskName;State='Simulated'}
}
if ($Run) { & $Installer -Root $Root -Run } else { & $Installer -Root $Root }
'''

FAKE_PYTHON = r'''
param([string]$EntryPoint,[Parameter(ValueFromRemainingArguments=$true)]$Arguments)
$root=Split-Path -Parent $PSScriptRoot
$settings=Get-Content -LiteralPath (Join-Path $root 'fake-settings.json') -Raw | ConvertFrom-Json
$name=Split-Path -Leaf $EntryPoint
if ($name -eq 'risk_runtime_check.py') {
    Add-Content -LiteralPath (Join-Path $root 'trace.jsonl') -Value (@{event='gate';entry=$EntryPoint;interpreter=$PSCommandPath} | ConvertTo-Json -Compress)
    exit ([int]$settings.gate_exit)
}
$action=$Arguments[-1]
Add-Content -LiteralPath (Join-Path $root 'trace.jsonl') -Value (@{event=$action;entry=$EntryPoint} | ConvertTo-Json -Compress)
if ($action -eq 'status') { @{supervisor_alive=[bool]$settings.alive} | ConvertTo-Json -Compress }
exit 0
'''


def fixture(tmp_path, **changes):
    root = tmp_path / 'isolated package with spaces'
    runtime = root / 'runtime'; runtime.mkdir(parents=True)
    backend = root / 'releases/selected/Backend'
    scripts = backend / 'scripts'; scripts.mkdir(parents=True)
    python = runtime / 'python-fixture.ps1'
    python.write_text(FAKE_PYTHON, encoding='utf-8-sig')
    for name in ('risk_runtime_check.py', 'local_integration.py', 'install_risk_autostart.ps1'):
        (scripts / name).write_text('# isolated fixture', encoding='utf-8')
    (root / 'runtime.json').write_text(json.dumps({'python': str(python)}), encoding='utf-8')
    (root / 'release.json').write_text(json.dumps({'backend': str(backend)}), encoding='utf-8')
    (root / 'fake-settings.json').write_text(json.dumps({'gate_exit': 0, 'alive': False,
                                                       'existing_task': False, **changes}), encoding='utf-8')
    wrapper = root / 'harness.ps1'; wrapper.write_text(WRAPPER, encoding='utf-8-sig')
    return root, backend, python, wrapper


def execute(root, wrapper, run=False):
    command = [SHELL, '-NoProfile', '-NonInteractive', '-File', str(wrapper),
               '-Installer', str(INSTALLER), '-Root', str(root)]
    if run:
        command.append('-Run')
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    trace = root / 'trace.jsonl'
    events = [json.loads(line) for line in trace.read_text(encoding='utf-8-sig').splitlines()] if trace.exists() else []
    return result, events


@pytest.mark.parametrize('run', [False, True])
def test_unapproved_gate_never_queries_registers_or_starts_a_task(tmp_path, run):
    root, backend, python, wrapper = fixture(tmp_path, gate_exit=23)
    result, events = execute(root, wrapper, run=run)
    assert result.returncode != 0
    assert [event['event'] for event in events] == ['gate']
    assert Path(events[0]['entry']) == backend / 'scripts/risk_runtime_check.py'
    assert Path(events[0]['interpreter']) == python


@pytest.mark.parametrize('alive,expected', [(False, ['gate', 'status', 'start']),
                                           (True, ['gate', 'status'])])
def test_run_uses_selected_controller_and_does_not_duplicate_live_supervisor(tmp_path, alive, expected):
    root, backend, _, wrapper = fixture(tmp_path, alive=alive)
    result, events = execute(root, wrapper, run=True)
    assert result.returncode == 0, result.stderr
    assert [event['event'] for event in events] == expected
    assert all(Path(event['entry']) == backend / 'scripts/local_integration.py' for event in events[1:])


def test_registration_is_only_simulated_and_uses_selected_installer(tmp_path):
    root, backend, _, wrapper = fixture(tmp_path)
    result, events = execute(root, wrapper)
    assert result.returncode == 0, result.stderr
    assert [event['event'] for event in events] == ['gate', 'task-query', 'task-registration-simulated']
    task = events[-1]
    assert task['action']['Execute'] == 'powershell.exe'
    assert str(backend / 'scripts/install_risk_autostart.ps1') in task['action']['Argument']
    assert str(INSTALLER) not in task['action']['Argument']
    assert '-WindowStyle Hidden' in task['action']['Argument'] and task['action']['Argument'].endswith(' -Run')
    assert task['principal']['RunLevel'] == 'Limited'
    assert task['principal']['LogonType'] == 'Interactive'
    assert task['settings']['MultipleInstances'] == 'IgnoreNew' and task['settings']['StartWhenAvailable'] is True


def test_existing_task_is_not_replaced(tmp_path):
    root, _, _, wrapper = fixture(tmp_path, existing_task=True)
    result, events = execute(root, wrapper)
    assert result.returncode != 0
    assert [event['event'] for event in events] == ['gate', 'task-query']


@pytest.mark.parametrize('invalid', ['external-python', 'relative-python', 'external-backend',
                                    'missing-gate', 'missing-controller', 'missing-installer',
                                    'missing-runtime-manifest'])
def test_invalid_package_is_rejected_before_any_runtime_or_task_action(tmp_path, invalid):
    root, backend, python, wrapper = fixture(tmp_path)
    if invalid in ('external-python', 'relative-python'):
        external = tmp_path / 'external.ps1'; external.write_text(FAKE_PYTHON, encoding='utf-8-sig')
        value = str(external) if invalid == 'external-python' else 'relative.ps1'
        (root / 'runtime.json').write_text(json.dumps({'python': value}), encoding='utf-8')
    elif invalid == 'external-backend':
        other = tmp_path / 'unrelated'; other.mkdir()
        (root / 'release.json').write_text(json.dumps({'backend': str(other)}), encoding='utf-8')
    elif invalid == 'missing-runtime-manifest':
        (root / 'runtime.json').unlink()
    else:
        name = {'missing-gate': 'risk_runtime_check.py', 'missing-controller': 'local_integration.py',
                'missing-installer': 'install_risk_autostart.ps1'}[invalid]
        (backend / 'scripts' / name).unlink()
    result, events = execute(root, wrapper)
    assert result.returncode != 0
    assert events == []
