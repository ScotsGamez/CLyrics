# media_reader.ps1
# Emits real-time JSON events for currently playing Windows media via GSMTC
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

while ($true) {
    try {
        $session = $mgr.GetCurrentSession()
        if ($session) {
            $media = Await ($session.TryGetMediaPropertiesAsync()) $PropType
            $info = $session.GetPlaybackInfo()
            $tl = $session.GetTimelineProperties()
            $pos = 0.0
            if ($tl) {
                $pos = $tl.Position.TotalSeconds
                if ($info.PlaybackStatus -eq 'Playing' -and $tl.LastUpdatedTime) {
                    $elapsed = ([DateTimeOffset]::UtcNow - $tl.LastUpdatedTime.ToUniversalTime()).TotalSeconds
                    if ($elapsed -gt 0 -and $elapsed -lt 30) { $pos += $elapsed }
                }
            }
            $dur = if ($tl) { $tl.EndTime.TotalSeconds } else { 0.0 }
            $title = if ($media.Title) { $media.Title } else { "" }
            $artist = if ($media.Artist) { $media.Artist } else { "" }
            $playing = ($info.PlaybackStatus -eq 'Playing')
            
            $json = [PSCustomObject]@{
                title = $title
                artist = $artist
                playing = $playing
                pos = [Math]::Round($pos, 2)
                duration = [Math]::Round($dur, 2)
            } | ConvertTo-Json -Compress
            [Console]::Out.WriteLine($json)
        } else {
            [Console]::Out.WriteLine('{"title":"","artist":"","playing":false,"pos":0,"duration":0}')
        }
    } catch {
        [Console]::Out.WriteLine('{"title":"","artist":"","playing":false,"pos":0,"duration":0}')
    }
    Start-Sleep -Milliseconds 150
}
