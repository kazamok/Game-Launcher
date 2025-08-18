; Inno Setup 스크립트 for WoW Launcher
; 이 스크립트는 WoW Launcher 설치 프로그램을 생성합니다.

[Setup]
DirExistsWarning=no
; 참고: AppId는 GUID여야 합니다. 이 값은 이 애플리케이션을 고유하게 식별합니다.
; 다른 애플리케이션을 위해 이 스크립트를 재사용할 경우 새 GUID를 생성해야 합니다.
AppId={{F2C2E5A8-704D-4A8F-A4E3-B5A9F6E8C9B1}
AppName=WoW Launcher
AppVersion=1.02
AppPublisher=
AppComments=이 프로그램은 악성코드를 포함하고 있지 않은 안전한 런처입니다.
;AppPublisher=Your Name
DefaultDirName=C:\WISE\WOW335
DefaultGroupName=WoW Launcher
DisableProgramGroupPage=yes
; "Output" 폴더에 setup.exe를 생성합니다.
OutputDir=Output
OutputBaseFilename=WoWLauncher_Setup
SetupIconFile=images\tbcicon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\WoWLauncher.exe

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; 

[Files]
; 참고: Inno Setup은 이 스크립트 파일이 있는 위치를 기준으로 상대 경로를 사용합니다.
; "dist" 폴더의 모든 파일을 설치 디렉토리({app})에 복사합니다.
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\WoW Launcher"; Filename: "{app}\WoWLauncher.exe"
Name: "{group}\{cm:UninstallProgram,WoW Launcher}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\WoW Launcher"; Filename: "{app}\WoWLauncher.exe"; Tasks: desktopicon

[Registry]
; wise-launcher:// 프로토콜을 등록합니다.
Root: HKCR; Subkey: "wise-launcher"; ValueType: string; ValueName: ""; ValueData: "URL:wise-launcher Protocol"; Flags: uninsdeletekey
Root: HKCR; Subkey: "wise-launcher"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCR; Subkey: "wise-launcher\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\WOWLauncher.exe"" ""%1"""

[Run]
Filename: "{app}\WoWLauncher.exe"; Description: "{cm:LaunchProgram,WoW Launcher}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/f /im WoWLauncher.exe"; Flags: runhidden; RunOnceId: "kill_launcher_on_uninstall"

[Code]
function InitializeSetup(): Boolean;
var
  UninstallerPath: string;
  ResultCode: Integer;
begin
  // 레지스트리에서 이전 버전의 제거 프로그램 경로를 확인합니다.
  // 키는 AppId에 "_is1"이 추가된 형태입니다.
  if RegQueryStringValue(HKA, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{F2C2E5A8-704D-4A8F-A4E3-B5A9F6E8C9B1}_is1', 'UninstallString', UninstallerPath) then
  begin
    // 제거 프로그램을 찾으면, 조용히 실행하고 끝날 때까지 기다립니다.
    Log('이전 버전을 찾았습니다. 제거 프로그램을 실행합니다: ' + UninstallerPath);
    if Exec(UninstallerPath, '/VERYSILENT', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      Log('제거 프로그램이 코드 ' + IntToStr(ResultCode) + '로 종료되었습니다.');
      Result := True; // 설치를 계속 진행합니다.
    end
    else
    begin
      // 제거 프로그램 실행에 실패한 경우, 실패를 기록하고 설치를 계속합니다.
      Log('Warning: Failed to execute the old uninstaller. Proceeding with installation anyway.');
      Result := True; // 설치를 계속 진행합니다.
    end;
  end
  else
  begin
    // 이전 설치를 찾지 못한 경우, 정상적으로 진행합니다.
    Log('이전 버전을 찾지 못했습니다.');
    Result := True;
  end;
end;

function GetWoWPath(Default: string): string;
var
  InstallPath: string;
begin
  // 32비트 WoW 클라이언트에 대한 일반적인 레지스트리 경로를 확인합니다.
  if RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Blizzard Entertainment\World of Warcraft', 'InstallPath', InstallPath) then
begin
    Result := InstallPath;
  end
  // 다른 가능한 경로도 확인합니다.
  else if RegQueryStringValue(HKLM, 'SOFTWARE\Blizzard Entertainment\World of Warcraft', 'InstallPath', InstallPath) then
begin
    Result := InstallPath;
  end
  // 경로를 찾지 못하면 기본값을 반환합니다.
  else
begin
    Result := Default;
  end;
end;
