; ============================================
; TakeoutReader_Installer.iss
; Inno Setup script — installeur Windows pro
; Telecharger Inno Setup : https://jrsoftware.org/isinfo.php
; ============================================

#define MyAppName "TakeoutReader"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Fabian De Blander"
#define MyAppURL "https://github.com/fabiandeblander/TakeoutReader"
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
; Pas besoin de droits admin — installe dans AppData si user-only
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer_output
OutputBaseFilename=TakeoutReader_Setup_{#MyAppVersion}
; Icone de l'installeur (optionnel — commenter si pas de .ico)
; SetupIconFile=takeoutreader.ico
LicenseFile=LICENSE.txt
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Taille minimale fenetre
WizardSizePercent=110,110
; DPI-aware
DPIAware=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Creer un raccourci sur le Bureau"; GroupDescription: "Raccourcis:"; Flags: checked
Name: "startmenuicon"; Description: "Creer un raccourci dans le menu Demarrer"; GroupDescription: "Raccourcis:"; Flags: checked

[Files]
; Le dossier complet genere par PyInstaller --onedir ou Nuitka --standalone
; Inclut l'exe + toutes les DLL/libs necessaires
Source: "dist\TakeoutReader\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TakeoutReader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Fichier licence
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

; README (optionnel)
; Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Proposer de lancer apres installation
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Nettoyer les fichiers generes (logs, etc.)
Type: files; Name: "{app}\*.log"

[Messages]
; Personnalisation des messages d'installation
french.WelcomeLabel1=Bienvenue dans l'assistant d'installation de {#MyAppName}
french.WelcomeLabel2={#MyAppName} convertit vos exports Gmail (Takeout) en une archive HTML interactive consultable hors-ligne.%n%nAucune donnee n'est envoyee sur Internet. Tout reste sur votre ordinateur.%n%nCliquez sur Suivant pour continuer.
french.FinishedLabel=L'installation de {#MyAppName} est terminee.%n%nPlacez vos fichiers .mbox ou votre dossier d'export Gmail dans un dossier, puis lancez {#MyAppName} pour les convertir en archive HTML.
