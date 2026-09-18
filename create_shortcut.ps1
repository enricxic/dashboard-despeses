$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\ControlHouse.lnk")
$Shortcut.TargetPath = "python.exe"
$Shortcut.Arguments = "e:\Dashboard\StartDashboard.py"
$Shortcut.WorkingDirectory = "e:\Dashboard"
$Shortcut.IconLocation = "e:\Dashboard\imatges\logo.ico"
$Shortcut.WindowStyle = 7 # Minimized window for the console
$Shortcut.Save()
