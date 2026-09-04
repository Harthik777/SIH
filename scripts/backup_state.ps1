param(
    [string]$DestinationDirectory = "",
    [string]$StateRoot = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $StateRoot) { $StateRoot = Join-Path $ProjectRoot "backend\data" }
if (-not $DestinationDirectory) { $DestinationDirectory = Join-Path $ProjectRoot "output\backups" }

$ResolvedState = (Resolve-Path -LiteralPath $StateRoot).Path
New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
$ResolvedDestination = (Resolve-Path -LiteralPath $DestinationDirectory).Path
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Staging = Join-Path ([System.IO.Path]::GetTempPath()) "sentinel-backup-$([guid]::NewGuid().ToString('N'))"
$Archive = Join-Path $ResolvedDestination "sentinel-state-$Timestamp.zip"

try {
    New-Item -ItemType Directory -Path $Staging -Force | Out-Null
    foreach ($Name in @("investigations", "uploads")) {
        $Source = Join-Path $ResolvedState $Name
        if (Test-Path -LiteralPath $Source) { Copy-Item -LiteralPath $Source -Destination $Staging -Recurse }
    }
    $Manifest = Get-ChildItem -LiteralPath $Staging -File -Recurse | ForEach-Object {
        [pscustomobject]@{
            Path = $_.FullName.Substring($Staging.Length + 1)
            SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            Bytes = $_.Length
        }
    }
    $Manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $Staging "backup-manifest.json") -Encoding utf8
    Compress-Archive -Path (Join-Path $Staging "*") -DestinationPath $Archive -CompressionLevel Optimal
    Write-Output $Archive
} finally {
    if (Test-Path -LiteralPath $Staging) { Remove-Item -LiteralPath $Staging -Recurse -Force }
}
