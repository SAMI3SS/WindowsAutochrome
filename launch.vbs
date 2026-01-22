' Launch WindowsAutochrome without showing terminal window
Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

' Get the directory where this VBS file is located
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

' Try pythonw.exe first (windowless), fallback to python.exe with hidden window
On Error Resume Next
WshShell.Run "pythonw.exe main.py", 0, False
If Err.Number <> 0 Then
    Err.Clear
    ' Fallback: Use python.exe with window hidden (0 = hidden)
    WshShell.Run "python.exe main.py", 0, False
End If
On Error Goto 0

Set WshShell = Nothing
Set fso = Nothing
