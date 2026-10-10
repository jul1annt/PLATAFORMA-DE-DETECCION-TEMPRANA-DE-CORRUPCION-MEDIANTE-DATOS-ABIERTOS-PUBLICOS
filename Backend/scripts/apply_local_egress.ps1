#Requires -RunAsAdministrator
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$IntegrationRoot)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($IntegrationRoot)
$plan = Get-Content -LiteralPath (Join-Path $root 'egress-plan.json') -Raw | ConvertFrom-Json
$runtime = Join-Path $root 'runtime'
$expected = @((Join-Path $runtime 'venv/Scripts/python.exe'), (Join-Path $runtime 'python/python.exe')) | ForEach-Object { [IO.Path]::GetFullPath($_) }
$group = 'PDTC Local Integration'
if ($plan.rules.Count -ne 6) { throw 'Unexpected rule count' }
foreach ($rule in $plan.rules) {
    $program = [IO.Path]::GetFullPath($rule.program)
    if ($program -notin $expected -or $rule.name -notmatch '^PDTC-Local-[01]-(https-destinations|other-external-tcp|external-udp)$') {
        throw 'Unexpected program or rule identity'
    }
    $hash = (Get-FileHash -LiteralPath $program -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $plan.program_sha256.$program) { throw 'Executable hash changed' }
}
if (([DateTimeOffset]::UtcNow - [DateTimeOffset]::Parse($plan.created_at_utc)).TotalMinutes -gt 30) {
    throw 'Refresh approved DNS addresses before applying this plan'
}
# Existing named rules must be reviewed separately; never overwrite another policy.
foreach ($rule in $plan.rules) {
    if (Get-NetFirewallRule -Name $rule.name -ErrorAction SilentlyContinue) { throw 'A named rule already exists' }
}
$created = @()
try {
    foreach ($rule in $plan.rules) {
        $parameters = @{
            Name=$rule.name; DisplayName=$rule.name; Group=$group; Direction='Outbound';
            Action='Block'; Enabled='True'; Profile='Any'; Program=$rule.program;
            Protocol=$rule.protocol; RemoteAddress=@($rule.addresses)
        }
        if ($rule.ports) { $parameters.RemotePort = $rule.ports.Split(',') }
        New-NetFirewallRule @parameters | Out-Null
        $created += $rule.name
    }
    $rules = @(Get-NetFirewallRule -Name $created)
    if ($rules.Count -ne 6 -or @($rules | Where-Object { $_.Enabled -ne 'True' -or $_.Action -ne 'Block' }).Count) {
        throw 'Firewall rule verification failed'
    }
    @{
        applied_at_utc=[DateTimeOffset]::UtcNow.ToString('o');
        identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name;
        rule_names=$created;
        scope='Dedicated integration Python; global profiles unchanged'
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'egress-applied.json') -Encoding utf8
} catch {
    foreach ($name in $created) { Remove-NetFirewallRule -Name $name -ErrorAction SilentlyContinue }
    throw
}
