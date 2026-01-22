# Simple Usage (Without Tray Icon)

If you're experiencing tray icon issues, you can use a simpler method:

## 1. Create Desktop Shortcut

```powershell
python create_shortcut.py
```

This creates a shortcut on the desktop. You can double-click the shortcut to open the profile selection window.

## 2. Add to Start Menu

```powershell
# Create shortcut in Start Menu folder
$startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
$shortcut = "$startMenu\Autochrome Launcher.lnk"
$target = (Get-Command python).Source
$script = "$PWD\main.py"
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcut)
$link.TargetPath = $target
$link.Arguments = "`"$script`""
$link.WorkingDirectory = $PWD
$link.Save()
```

## 3. Run in Normal Mode

```powershell
python main.py
```

This directly opens the profile selection window.

## 4. Add to Windows Startup (Optional)

```powershell
# Create shortcut in Startup folder
$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$shortcut = "$startup\Autochrome Launcher.lnk"
$target = (Get-Command python).Source
$script = "$PWD\main.py"
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcut)
$link.TargetPath = $target
$link.Arguments = "`"$script`""
$link.WorkingDirectory = $PWD
$link.Save()
```

This will automatically open the profile selection window when Windows starts.
