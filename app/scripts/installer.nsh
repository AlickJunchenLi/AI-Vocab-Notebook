!include "LogicLib.nsh"

!ifndef BUILD_UNINSTALLER
Var /GLOBAL reinstallMode

!macro customInit
  StrCpy $reinstallMode "false"
  SetOverwrite on

  Push $R0
  Push $R1

  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} $R0 "/reinstall" $R1
  ${IfNot} ${Errors}
    StrCpy $reinstallMode "true"
  ${EndIf}

  Pop $R1
  Pop $R0

  ${If} ${FileExists} "$INSTDIR"
    StrCpy $reinstallMode "true"
  ${EndIf}

  ${If} $reinstallMode == "true"
  ${AndIfNot} ${Silent}
    MessageBox MB_OK|MB_ICONINFORMATION "Existing install detected. The installer will reinstall/repair and overwrite app files in $INSTDIR. Your notebook data under the user profile stays untouched."
  ${EndIf}
!macroend

!macro customInstall
  ${If} $reinstallMode == "true"
    DetailPrint "Reinstall/repair mode: overwriting existing app files; user data stays in user profile."
  ${EndIf}

  StrCpy $0 "$INSTDIR\\resources\\nodejs\\node-v20.11.1-x64.msi"

  IfFileExists "$0" 0 NodeMissing

  ${If} ${Silent}
    DetailPrint "Silent mode: skipping bundled Node.js prompt. Installer is present at $0 (not executed)."
    Goto EndNodeInstall
  ${EndIf}

  nsExec::ExecToStack 'cmd /C "node -v"'
  Pop $1 ; exit code
  Pop $2 ; output

  ${If} $1 == "0"
    MessageBox MB_YESNO|MB_ICONQUESTION "Detected Node.js $2$\r$\nInstall bundled Node.js v20.11.1 to update?" IDYES InstallNode IDNO SkipNode
  ${Else}
    MessageBox MB_YESNO|MB_ICONQUESTION "Node.js not detected. Install bundled Node.js v20.11.1 now?" IDYES InstallNode IDNO SkipNode
  ${EndIf}
  Goto EndNodeInstall

InstallNode:
  DetailPrint "Running bundled Node.js installer (per-user)..."
  ExecWait '"$SYSDIR\\msiexec.exe" /i "$0" /passive /norestart ALLUSERS=0' $3
  ${If} $3 == "0"
    DetailPrint "Node.js install completed."
  ${Else}
    MessageBox MB_ICONEXCLAMATION "Node.js installer exited with code $3. You may need to rerun it manually."
  ${EndIf}
  Goto EndNodeInstall

SkipNode:
  DetailPrint "Skipped Node.js installation."
  Goto EndNodeInstall

NodeMissing:
  DetailPrint "Bundled Node.js installer not found at $0"

EndNodeInstall:
!macroend
!endif
