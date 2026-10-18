# media_reader.ps1
# Emits real-time JSON events for currently playing Windows media via GSMTC
# Uses pure local hardware CPU timers (System.Diagnostics.Stopwatch) with ZERO reliance on wall-clock / internet time
param(
    [int]$ParentPid = 0
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties, Windows.Media, ContentType = WindowsRuntime] | Out-Null
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$MgrType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]
$PropType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties]
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
})[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(1000) | Out-Null
    return $netTask.Result
}

$mgr = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) $MgrType

# Local hardware stopwatch for continuous playback progression (QueryPerformanceCounter)
$sw = [System.Diagnostics.Stopwatch]::new()
[double]$lastReportedPos = -1.0
[double]$basePos = 0.0
$lastTrackId = ""

while ($true) {
    # Parent process watchdog: if parent process exited or crashed, exit immediately
    if ($ParentPid -gt 0) {
        try {
            $p = Get-Process -Id $ParentPid -ErrorAction SilentlyContinue
            if (-not $p -or $p.HasExited) {
                exit 0
            }
        } catch {
            exit 0
        }
    }

    try {
        $session = $mgr.GetCurrentSession()
        if ($session) {
            $media = Await ($session.TryGetMediaPropertiesAsync()) $PropType
            $info = $session.GetPlaybackInfo()
            $tl = $session.GetTimelineProperties()

            $title = if ($media.Title) { $media.Title } else { "" }
            $artist = if ($media.Artist) { $media.Artist } else { "" }
            $playing = ($info.PlaybackStatus -eq 'Playing')
            $dur = if ($tl) { [double]$tl.EndTime.TotalSeconds } else { 0.0 }
            [double]$rawPos = if ($tl) { [double]$tl.Position.TotalSeconds } else { 0.0 }

            $currentTrackId = "$title - $artist"
            if ($currentTrackId -ne $lastTrackId) {
                $lastTrackId = $currentTrackId
                $lastReportedPos = -1.0
                $basePos = $rawPos
                $sw.Reset()
                if ($playing) { $sw.Start() }
            }

            # Device timeline packet update or user seek detection
            if ([Math]::Abs($rawPos - $lastReportedPos) -gt 0.05) {
                $lastReportedPos = $rawPos
                $basePos = $rawPos
                $sw.Restart()
            }

            # Local hardware position calculation without any wall-clock or UTC math
            [double]$pos = $basePos
            if ($playing) {
                if (-not $sw.IsRunning) { $sw.Start() }
                $pos += $sw.Elapsed.TotalSeconds
                if ($dur -gt 0 -and $pos -gt $dur) { $pos = $dur }
            } else {
                if ($sw.IsRunning) { $sw.Stop() }
            }
            
            $json = [PSCustomObject]@{
                title = $title
                artist = $artist
                playing = $playing
                pos = [Math]::Round($pos, 2)
                duration = [Math]::Round($dur, 2)
            } | ConvertTo-Json -Compress
            [Console]::Out.WriteLine($json)
        } else {
            $sw.Reset()
            $lastReportedPos = -1.0
            [Console]::Out.WriteLine('{"title":"","artist":"","playing":false,"pos":0,"duration":0}')
        }
    } catch {
        [Console]::Out.WriteLine('{"title":"","artist":"","playing":false,"pos":0,"duration":0}')
    }
    Start-Sleep -Milliseconds 150
}
