#Requires -RunAsAdministrator
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$IntegrationRoot)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($IntegrationRoot)
$plan = Get-Content -LiteralPath (Join-Path $root 'egress-plan.json') -Raw | ConvertFrom-Json
$runtime = Join-Path $root 'runtime'
$expected = @((Join-Path $runtime 'venv/Scripts/python.exe'), (Join-Path $runtime 'python/python.exe')) | ForEach-Object { [IO.Path]::GetFullPath($_) }
$group = 'PDTC Local Integration'
function ConvertTo-FirewallRanges {
    param([string[]]$Networks)
    foreach ($network in $Networks) {
        $parts = $network.Split('/')
        if ($parts.Count -ne 2) { throw 'Expected an explicit CIDR network' }
        $bytes = [Net.IPAddress]::Parse($parts[0]).GetAddressBytes()
        $prefix = [int]$parts[1]
        if ($prefix -lt 0 -or $prefix -gt $bytes.Length * 8) { throw 'Invalid network prefix length' }
        $first = [byte[]]$bytes.Clone()
        $last = [byte[]]$bytes.Clone()
        for ($index = 0; $index -lt $bytes.Length; $index++) {
            $remaining = $prefix - $index * 8
            $mask = if ($remaining -ge 8) { 255 } elseif ($remaining -le 0) { 0 } else { (255 -shl (8 - $remaining)) -band 255 }
            $first[$index] = $bytes[$index] -band $mask
            $last[$index] = $first[$index] -bor (255 - $mask)
        }
        $start = [Net.IPAddress]::new($first).ToString()
        $end = [Net.IPAddress]::new($last).ToString()
        if ($start -eq $end) { $start } else { "$start-$end" }
    }
}
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
# Enumerate successfully before filtering: access failures must not look like missing rules.
$existingRules = @(Get-NetFirewallRule -PolicyStore ActiveStore -ErrorAction Stop)
foreach ($rule in $plan.rules) {
    if (@($existingRules | Where-Object { $_.Name -eq $rule.name }).Count) { throw 'A named rule already exists' }
}
$created = @()
try {
    foreach ($rule in $plan.rules) {
        $parameters = @{
            Name=$rule.name; DisplayName=$rule.name; Group=$group; Direction='Outbound';
            Action='Block'; Enabled='True'; Profile='Any'; Program=$rule.program;
            # Windows' CIM provider rejects some complement prefixes. Explicit
            # IP ranges represent exactly the same sets, including full IPv6.
            Protocol=$rule.protocol; RemoteAddress=@(ConvertTo-FirewallRanges -Networks $rule.addresses)
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
