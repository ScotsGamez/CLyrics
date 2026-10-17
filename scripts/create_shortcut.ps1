# create_shortcut.ps1
# Creates a high-DPI desktop shortcut for Transparent Live Lyrics Overlay
param(
    [string]$TargetDir = (Split-Path -Parent $PSScriptRoot)
)

$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "Transparent Live Lyrics.lnk"

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
$Shortcut.Description = "100% Transparent Live Lyrics Overlay"
$Shortcut.Save()

Write-Host "Created desktop shortcut at: $ShortcutPath" -ForegroundColor Green
