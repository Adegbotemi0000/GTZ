; GTZ ID Studio - Inno Setup Script
; Produces a professional Windows installer

#define MyAppName "GTZ ID Studio"
#define MyAppVersion "1.0"
#define MyAppPublisher "GT & Zino / Xtreme Cr8"
#define MyAppExeName "GTZ ID Studio.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\GTZ ID Studio
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=GTZ_ID_Studio_Setup_v1.0
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "odbcinstall"; Description: "Install Microsoft ODBC Driver (required for SQL Server connection)"; GroupDescription: "Optional components:"; Flags: unchecked

[Files]
; Main application executable
Source: "dist\GTZ ID Studio.exe"; DestDir: "{app}"; Flags: ignoreversion

; App icon
Source: "assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; ODBC driver installer (optional)
Source: "extras\msodbcsql.msi"; DestDir: "{tmp}"; Flags: deleteafterinstall; Tasks: odbcinstall

[Icons]
; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: startmenuicon

; Uninstaller in Start Menu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Install ODBC driver silently if user selected it
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\msodbcsql.msi"" /quiet /norestart"; StatusMsg: "Installing ODBC Driver for SQL Server..."; Tasks: odbcinstall; Flags: waituntilterminated

; Launch app after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Messages]
WelcomeLabel1=Welcome to {#MyAppName} Setup
WelcomeLabel2=This will install {#MyAppName} version {#MyAppVersion} on your computer.%n%nGTZ ID Studio is a professional staff ID card design and printing application.%n%nClick Next to continue.
FinishedLabel=Setup has finished installing {#MyAppName} on your computer.%n%nThe application can be launched using the shortcuts created on your Desktop or Start Menu.
