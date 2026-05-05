$ErrorActionPreference = 'Stop'

$taskName = "YTDownloadHelper"
$backendUrl = "http://127.0.0.1:5001/"

Write-Host "=== Helper Status ==="
Write-Host ""

Write-Host "1) Task state"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "- Task not found: $taskName"
} else {
    $info = $task | Get-ScheduledTaskInfo
    Write-Host "- Name: $taskName"
    Write-Host "- State: $($task.State)"
    Write-Host "- Last Run: $($info.LastRunTime)"
    Write-Host "- Last Result: $($info.LastTaskResult)"
}

Write-Host ""
Write-Host "2) Backend health"
try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $backendUrl -TimeoutSec 5
    Write-Host "- URL: $backendUrl"
    Write-Host "- Reachable: Yes"
    Write-Host "- Status Code: $($response.StatusCode)"
    Write-Host "- Body: $($response.Content)"
} catch {
    Write-Host "- URL: $backendUrl"
    Write-Host "- Reachable: No"
    Write-Host "- Error: $($_.Exception.Message)"
}
