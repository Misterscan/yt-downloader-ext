$ErrorActionPreference = 'Stop'

$taskName = "YTDownloadHelper"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($task) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Uninstalled scheduled task: $taskName"
} else {
    Write-Host "Task not found: $taskName"
}
