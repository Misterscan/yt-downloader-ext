$ErrorActionPreference = 'Stop'

$taskName = "YTDownloadHelper"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = (Resolve-Path (Join-Path $scriptDir "start-helper.ps1")).Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

if (-not (Test-Path $startScript)) {
    throw "Missing start script at $startScript"
}

$currentUser = "{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME
$actionCommand = "/d /c cd /d `"$projectRoot`" && powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startScript`""
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $actionCommand
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Auto-start YouTube downloader helper backend"

Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host "Installed and started scheduled task: $taskName"
Write-Host "Check status with: Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo"
Write-Host "Logs: .\\logs\\helper.out.log and .\\logs\\helper.err.log"
