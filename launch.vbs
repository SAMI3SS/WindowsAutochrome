' Launch WindowsAutochrome without showing terminal window
Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

' Get the directory where this VBS file is located
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

' Build command to run main.py (with quotes for paths with spaces)
mainPy = Chr(34) & scriptDir & "\main.py" & Chr(34)

' Try pythonw.exe first (windowless), fallback to python.exe
On Error Resume Next
WshShell.Run "pythonw.exe " & mainPy, 0, False
If Err.Number <> 0 Then
    Err.Clear
    ' Fallback: Use python.exe with window hidden (0 = hidden)
    WshShell.Run "python.exe " & mainPy, 0, False
    If Err.Number <> 0 Then
        ' If both fail, show error message
        MsgBox "Error: Python not found or main.py failed to run." & vbCrLf & vbCrLf & "Error Code: " & Err.Number & vbCrLf & "Description: " & Err.Description & vbCrLf & vbCrLf & "Please ensure:" & vbCrLf & "1. Python is installed and in PATH" & vbCrLf & "2. main.py exists in: " & scriptDir, vbCritical, "WindowsAutochrome Error"
    End If
End If
On Error Goto 0

Set WshShell = Nothing
Set fso = Nothing
