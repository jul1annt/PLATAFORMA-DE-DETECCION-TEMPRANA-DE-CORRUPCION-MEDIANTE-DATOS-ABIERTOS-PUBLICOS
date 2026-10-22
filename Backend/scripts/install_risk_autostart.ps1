param([Parameter(Mandatory=$true)][string]$Root,[switch]$Run)
$ErrorActionPreference='Stop'
$resolvedRoot=(Resolve-Path -LiteralPath $Root).Path
function Resolve-PackageFile([string]$Container,[string]$Candidate) {
    if ([string]::IsNullOrWhiteSpace($Candidate) -or -not [System.IO.Path]::IsPathRooted($Candidate)) {
        throw 'El manifiesto debe declarar una ruta absoluta del paquete.'
    }
    $containerPath=(Resolve-Path -LiteralPath $Container).Path.TrimEnd('\','/')
    $candidatePath=(Resolve-Path -LiteralPath $Candidate).Path
    if (-not $candidatePath.StartsWith($containerPath+[System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $candidatePath -PathType Leaf)) {
        throw 'El archivo no pertenece al directorio esperado del paquete.'
    }
    return $candidatePath
}
$runtime=Get-Content -LiteralPath (Join-Path $resolvedRoot 'runtime.json') -Raw | ConvertFrom-Json
$release=Get-Content -LiteralPath (Join-Path $resolvedRoot 'release.json') -Raw | ConvertFrom-Json
$python=Resolve-PackageFile (Join-Path $resolvedRoot 'runtime') $runtime.python
$backend=(Resolve-Path -LiteralPath $release.backend).Path
$releaseContainer=(Resolve-Path -LiteralPath (Join-Path $resolvedRoot 'releases')).Path.TrimEnd('\','/')
if (-not $backend.StartsWith($releaseContainer+[System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'El backend seleccionado no pertenece al paquete.'
}
$gate=Resolve-PackageFile $backend (Join-Path $backend 'scripts\risk_runtime_check.py')
$controller=Resolve-PackageFile $backend (Join-Path $backend 'scripts\local_integration.py')
$installer=Resolve-PackageFile $backend (Join-Path $backend 'scripts\install_risk_autostart.ps1')
& $python $gate --root $resolvedRoot
if ($LASTEXITCODE -ne 0) { throw 'No se instala ni inicia la tarea: publicación analítica pendiente de validación.' }
if ($Run) {
    $state=& $python $controller --root $resolvedRoot status | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo comprobar el supervisor local.' }
    if (-not $state.supervisor_alive) {
        & $python $controller --root $resolvedRoot start
        if ($LASTEXITCODE -ne 0) { throw 'El controlador rechazó el inicio; revisar procesos y bloqueo conservados.' }
    }
    exit 0
}
$taskName='PDTC-Riesgo-Local'
$existing=Get-ScheduledTask -ErrorAction Stop | Where-Object TaskName -eq $taskName
if ($existing) { throw 'La tarea ya existe; conservarla y revisar antes de cambiarla.' }
if ($resolvedRoot.Contains('"') -or $installer.Contains('"')) { throw 'Ruta inválida para la tarea.' }
$arguments='-NoProfile -NonInteractive -WindowStyle Hidden -File "'+$installer+'" -Root "'+$resolvedRoot+'" -Run'
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger=New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$principal=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -Hidden
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Select-Object TaskName,State
