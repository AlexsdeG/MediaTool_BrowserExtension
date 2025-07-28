; MediaTool Installer
!define APPNAME "MediaTool"
!define COMPANYNAME "MediaTool"
!define DESCRIPTION "Media download and conversion tool"
!define VERSIONMAJOR 1
!define VERSIONMINOR 0
!define VERSIONBUILD 0

RequestExecutionLevel admin

InstallDir "$PROGRAMFILES\${APPNAME}"

Name "${APPNAME}"
Icon "icon.ico"
outFile "MediaTool-Installer.exe"

!include LogicLib.nsh

page components
page directory
page instfiles

!macro VerifyUserIsAdmin
UserInfo::GetAccountType
pop $0
${If} $0 != "admin"
    messageBox mb_iconstop "Administrator rights required!"
    setErrorLevel 740
    quit
${EndIf}
!macroend

function .onInit
    setShellVarContext all
    !insertmacro VerifyUserIsAdmin
functionEnd

section "MediaTool Service" SecService
    setOutPath $INSTDIR
    
    ; Copy service files
    file "dist\service.exe"
    file "dist\*.*"
    
    ; Create uninstaller
    writeUninstaller "$INSTDIR\uninstall.exe"
    
    ; Install as Windows service (optional)
    nsExec::ExecToLog '"$INSTDIR\service.exe" --install'
    
    ; Add to startup instead of service
    ; writeRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "MediaToolService" "$INSTDIR\service.exe"
    
    ; Add to Add/Remove Programs
    writeRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
    writeRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\uninstall.exe"
    writeRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$INSTDIR"
    writeRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
    writeRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMajor" ${VERSIONMAJOR}
    writeRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMinor" ${VERSIONMINOR}
    writeRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoModify" 1
    writeRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoRepair" 1
    
    ; Start service
    nsExec::ExecToLog '"$INSTDIR\service.exe" --start'
    
sectionEnd

section "Chrome Extension" SecExtension
    ; Copy extension files to a known location
    setOutPath "$INSTDIR\extension"
    file /r "extension\*.*"
    
    ; Show installation instructions
    messageBox MB_OK "Extension files copied to $INSTDIR\extension$\n$\nTo install:$\n1. Open Chrome$\n2. Go to chrome://extensions/$\n3. Enable Developer Mode$\n4. Click 'Load unpacked'$\n5. Select the extension folder"
sectionEnd

; Uninstaller
section "Uninstall"
    ; Stop and remove service
    nsExec::ExecToLog '"$INSTDIR\service.exe" --stop'
    nsExec::ExecToLog '"$INSTDIR\service.exe" --uninstall'
    
    ; Remove from startup
    deleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "MediaToolService"
    
    ; Remove files
    rmDir /r "$INSTDIR"
    
    ; Remove from Add/Remove Programs
    deleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
sectionEnd