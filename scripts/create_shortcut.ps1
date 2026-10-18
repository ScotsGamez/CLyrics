# create_shortcut.ps1
# Creates a high-DPI desktop shortcut matching the repository name for Clyrics
param(
    [string]$TargetDir = (Split-Path -Parent $PSScriptRoot),
    [string]$ShortcutName = ""
)

if (-not $ShortcutName) {
    try {
        $remote = git -C $TargetDir config --get remote.origin.url 2>$null
        if ($remote) {
            $ShortcutName = [System.IO.Path]::GetFileNameWithoutExtension($remote.TrimEnd('/'))
        }
    } catch {}
}
if (-not $ShortcutName) {
    $ShortcutName = "CLyrics"
} elseif ($ShortcutName.ToLower() -eq "clyrics") {
    $ShortcutName = "CLyrics"
}

$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "$ShortcutName.lnk"

# Clean up any legacy differently named shortcuts
$LegacyNames = @("Transparent Live Lyrics.lnk", "Transparent Lyrics.lnk", "Clyrics.lnk")
foreach ($legacy in $LegacyNames) {
    if ($legacy -cne "$ShortcutName.lnk") {
        $legacyPath = Join-Path $Desktop $legacy
        if (Test-Path $legacyPath) {
            Remove-Item $legacyPath -Force -ErrorAction SilentlyContinue
        }
    }
}

# Find pythonw (silent, no terminal window) or fallback to python
$py = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $py) {
    $py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
}
if (-not $py) {
    $py = "pythonw.exe"
}

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $py
$Shortcut.Arguments = "`"$TargetDir\run.py`""
$Shortcut.WorkingDirectory = $TargetDir

$IconPath = Join-Path $TargetDir "assets\icon.ico"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath, 0"
}
$Shortcut.Description = "CLyrics (C (See) Lyrics) - 100% Transparent Live Lyrics Overlay"
$Shortcut.Save()

# Notify Windows Explorer of shell/icon change
try {
    Start-Process -FilePath "ie4uinit.exe" -ArgumentList "-show" -WindowStyle Hidden -ErrorAction SilentlyContinue
} catch {}

Write-Host "Created desktop shortcut at: $ShortcutPath" -ForegroundColor Green
