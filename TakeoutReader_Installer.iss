; ============================================
; TakeoutReader_Installer.iss
; Inno Setup script - installeur Windows pro
; ============================================

#define MyAppName "TakeoutReader"
#define MyAppVersion "1.0.0"
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
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Creer un raccourci sur le Bureau"; GroupDescription: "Raccourcis:"
Name: "startmenuicon"; Description: "Creer un raccourci dans le menu Demarrer"; GroupDescription: "Raccourcis:"

[Files]
Source: "dist\TakeoutReader\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TakeoutReader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\*.log"

[Messages]
french.WelcomeLabel1=Bienvenue dans l'assistant d'installation de {#MyAppName}
french.WelcomeLabel2={#MyAppName} convertit vos exports Gmail (Takeout) en une archive HTML interactive consultable hors-ligne.%n%nAucune donnee n'est envoyee sur Internet. Tout reste sur votre ordinateur.%n%nCliquez sur Suivant pour continuer.
french.FinishedLabel=L'installation de {#MyAppName} est terminee.%n%nPlacez vos fichiers .mbox ou votre dossier d'export Gmail dans un dossier, puis lancez {#MyAppName} pour les convertir en archive HTML.
