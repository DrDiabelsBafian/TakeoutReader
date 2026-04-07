; TakeoutReader_Installer.iss
; Inno Setup script — Windows installer for TakeoutReader v2.0.0

#define MyAppName "TakeoutReader"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Dr. Diabels Bafian"
#define MyAppURL "https://github.com/DrDiabelsBafian/TakeoutReader"
#define MyAppExeName "TakeoutReader.exe"

[Setup]
AppId={{49833853-C925-4B3A-8D73-65E9DB27C71C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer_output
OutputBaseFilename=TakeoutReader_Setup_{#MyAppVersion}
SetupIconFile=takeoutreader.ico
LicenseFile=LICENSE.txt
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110,110

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startmenuicon"; Description: "Create a Start Menu shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "dist\TakeoutReader\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TakeoutReader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\*.log"

[Messages]
english.WelcomeLabel1=Welcome to the {#MyAppName} Setup Wizard
english.WelcomeLabel2={#MyAppName} converts your Gmail Takeout exports into a searchable offline HTML archive.%n%nNo data is ever sent to the Internet. Everything stays on your computer.%n%nClick Next to continue.
english.FinishedLabel={#MyAppName} has been installed.%n%nPlace your .mbox files or Gmail export folder somewhere, then launch {#MyAppName} to convert them into an HTML archive.
french.WelcomeLabel1=Bienvenue dans l'assistant d'installation de {#MyAppName}
french.WelcomeLabel2={#MyAppName} convertit vos exports Gmail (Takeout) en une archive HTML interactive consultable hors-ligne.%n%nAucune donnee n'est envoyee sur Internet. Tout reste sur votre ordinateur.%n%nCliquez sur Suivant pour continuer.
french.FinishedLabel=L'installation de {#MyAppName} est terminee.%n%nPlacez vos fichiers .mbox ou votre dossier d'export Gmail dans un dossier, puis lancez {#MyAppName} pour les convertir en archive HTML.
