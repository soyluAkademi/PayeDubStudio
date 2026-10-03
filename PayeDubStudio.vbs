' Paye Games Dub Studio - yerel sunucuyu baslatir, tarayicida acar
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
kok = fso.GetParentFolderName(WScript.ScriptFullName)
app = """" & kok & "\program\sunucu.py" & """"

If Not fso.FileExists(kok & "\program\sunucu.py") Then
    MsgBox "program\sunucu.py bulunamadi." & vbCrLf & _
           "Bu dosya program klasorunun bir ust klasorunde durmali.", 16, "Paye Games Dub Studio"
    WScript.Quit
End If

On Error Resume Next
sh.Run "pythonw " & app, 0, False
If Err.Number <> 0 Then
    Err.Clear
    sh.Run "python " & app, 1, False
    If Err.Number <> 0 Then
        MsgBox "Python bulunamadi. Python kurulu mu, PATH'e ekli mi?", 16, "Paye Games Dub Studio"
    End If
End If
