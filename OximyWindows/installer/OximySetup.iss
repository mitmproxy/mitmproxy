; OximySetup.iss
; Inno Setup script for Oximy Windows installer

#define MyAppName "Oximy"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Oximy Inc"
#define MyAppURL "https://oximy.com"
#define MyAppExeName "Oximy.exe"
#define MyAppDescription "AI Traffic Monitor"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{B8E5D3A2-7F4C-4E9B-A1D6-8C3F2B1E5A4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/support
AppUpdatesURL={#MyAppURL}/download
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=OximySetup-{#MyAppVersion}
OutputDir=Output
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
SetupIconFile=..\src\OximyWindows\Assets\oximy.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
MinVersion=10.0.18362
LicenseFile=
InfoBeforeFile=
InfoAfterFile=

; Signing (uncomment when you have a code signing certificate)
; SignTool=signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a $f

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start {#MyAppName} when Windows starts"; GroupDescription: "Startup:"

[Files]
; Main application and all dependencies
Source: "..\publish\win-x64\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Installer scripts for MDM deployments
Source: "scripts\preinstall.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\postinstall.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\uninstall.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"; Tasks: desktopicon

[Registry]
; Auto-start on login (if task is selected)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; Run post-install script for MDM setup (runs for all installs, script checks for MDM config)
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\scripts\postinstall.ps1"" -InstallPath ""{app}"" -Silent"; Flags: runhidden; StatusMsg: "Configuring Oximy..."

; Launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop running instance before uninstall
Filename: "taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillOximy"

; Run uninstall script for cleanup
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\scripts\uninstall.ps1"" -Silent"; Flags: runhidden; RunOnceId: "RunUninstallScript"

[UninstallDelete]
; Clean up user data (optional - ask user?)
Type: filesandordirs; Name: "{%USERPROFILE}\.oximy"

[Code]
var
  FinishedInstall: Boolean;

procedure InitializeWizard;
begin
  FinishedInstall := False;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    FinishedInstall := True;
  end;
end;

// Check if MDM configuration exists (for conditional operations)
function IsMDMInstall(): Boolean;
begin
  Result := RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Policies\Oximy');
end;

// Pre-install: Check if app is running and disable proxy
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Check if Oximy is running
  if Exec('tasklist.exe', '/FI "IMAGENAME eq {#MyAppExeName}" /NH', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // If running, ask user to close it (skip prompt for silent install)
    if not WizardSilent then
    begin
      if MsgBox('{#MyAppName} is currently running. Would you like to close it and continue with the installation?',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        Exec('taskkill.exe', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        Sleep(1000); // Wait for process to fully terminate
      end
      else
      begin
        Result := False;
        Exit;
      end;
    end
    else
    begin
      // Silent install - just kill the process
      Exec('taskkill.exe', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(1000);
    end;
  end;

  // Stop mitmdump if running
  Exec('taskkill.exe', '/F /IM mitmdump.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // Disable proxy as safety measure before installation
  RegWriteDWordValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Internet Settings', 'ProxyEnable', 0);
end;

// Disable proxy on uninstall to prevent leaving user without internet
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Disable system proxy
    RegWriteDWordValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Internet Settings', 'ProxyEnable', 0);
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    // Remove certificate from trusted root store (requires admin)
    // Using certutil to remove by common name
    Exec('certutil.exe', '-delstore -user Root "mitmproxy"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('certutil.exe', '-delstore Root "mitmproxy"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
