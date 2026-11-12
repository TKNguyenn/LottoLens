#ifndef AppVersion
  #error AppVersion must be supplied by packaging/build.py
#endif

[Setup]
AppId={{FD802D06-C88B-4A7C-B785-770E04465513}
AppName=LottoLens
AppVersion={#AppVersion}
AppVerName=LottoLens V{#AppVersion}
AppPublisher=LottoLens
DefaultDirName={localappdata}\Programs\LottoLens
DefaultGroupName=LottoLens
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=LottoLens-Setup-{#AppVersion}
SetupIconFile=..\docs\redesign\assets\generated\07-ticket-gold.ico
UninstallDisplayIcon={app}\LottoLens.exe
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
AppMutex=LottoLens.App
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "vietnamese"; MessagesFile: "Vietnamese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
vietnamese.DataLocation=App và dữ liệu cùng thư mục. Dữ liệu cá nhân nằm trong thư mục con data.
english.DataLocation=App and user data stay together. User files are stored in the data subfolder.
vietnamese.Shortcut=Tạo shortcut trên Desktop
english.Shortcut=Create a desktop shortcut
vietnamese.Launch=Khởi chạy LottoLens
english.Launch=Launch LottoLens
vietnamese.UninstallTitle=Gỡ cài đặt LottoLens
english.UninstallTitle=Uninstall LottoLens
vietnamese.UninstallPrompt=Chọn cách gỡ cài đặt. Cả hai lựa chọn đều xóa lịch tự cập nhật của bản cài này.
english.UninstallPrompt=Choose what to remove. Both options remove this installation's automatic-update tasks.
vietnamese.KeepData=Xóa ứng dụng, giữ lại dữ liệu (mặc định)
english.KeepData=Remove the app and keep user data (default)
vietnamese.PurgeData=Xóa ứng dụng và toàn bộ dữ liệu
english.PurgeData=Remove the app and all user data
vietnamese.DataDetails=Dữ liệu gồm lịch sử, báo cáo, bộ tham khảo, cài đặt, API key và các xác nhận. Thư mục dữ liệu:
english.DataDetails=Data includes history, reports, suggestions, settings, API key and acceptance receipts. Data folder:
vietnamese.Uninstall=Gỡ cài đặt
english.Uninstall=Uninstall
vietnamese.Cancel=Hủy
english.Cancel=Cancel
vietnamese.ConfirmPurge=Xóa vĩnh viễn toàn bộ dữ liệu LottoLens trong thư mục sau? Không thể hoàn tác.
english.ConfirmPurge=Permanently delete all LottoLens user data in this folder? This cannot be undone.
vietnamese.CleanupFailed=Chưa dọn được lịch tự cập nhật hoặc dữ liệu. Đã dừng gỡ cài đặt để giữ file ứng dụng. Hãy đóng LottoLens, kiểm tra quyền ghi và thử lại.
english.CleanupFailed=Could not clean up scheduled tasks or user data. Uninstall stopped to preserve the application files. Close LottoLens, check write permissions and try again.
vietnamese.NotWritable=Không ghi được vào thư mục cài đặt. Hãy chọn thư mục khác mà tài khoản hiện tại có quyền ghi.
english.NotWritable=The installation folder is not writable. Choose another folder writable by your current account.
vietnamese.ChooseSubfolder=Hãy chọn một thư mục riêng cho LottoLens, không dùng trực tiếp thư mục gốc ổ đĩa hoặc thư mục hệ thống.
english.ChooseSubfolder=Choose a dedicated LottoLens folder, not a drive root or Windows system directory.

[Files]
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\COPYRIGHT"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\LottoLens\LottoLens.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\LottoLens\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\LottoLens"; Filename: "{app}\LottoLens.exe"; WorkingDir: "{app}"
Name: "{autoprograms}\Gỡ LottoLens - Uninstall"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\LottoLens.exe"; Description: "{cm:Launch}"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: files; Name: "{autodesktop}\LottoLens.lnk"

[Code]
var
  PurgeData: Boolean;
  ShortcutCheck: TNewCheckBox;

function GetTempFileNameW(PathName, PrefixString: String; Unique: Cardinal; Buffer: String): Cardinal;
  external 'GetTempFileNameW@kernel32.dll stdcall';

procedure CreateDesktopShortcut;
begin
  CreateShellLink(ExpandConstant('{autodesktop}\LottoLens.lnk'), 'LottoLens',
    ExpandConstant('{app}\LottoLens.exe'), '', ExpandConstant('{app}'),
    ExpandConstant('{app}\LottoLens.exe'), 0, SW_SHOWNORMAL);
end;

procedure InitializeWizard;
begin
  WizardForm.SelectDirLabel.Caption := CustomMessage('DataLocation');
  ShortcutCheck := TNewCheckBox.Create(WizardForm);
  ShortcutCheck.Parent := WizardForm.FinishedPage;
  ShortcutCheck.Caption := CustomMessage('Shortcut');
  ShortcutCheck.Checked := True;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then begin
    WizardForm.RunList.Height := ScaleY(24);
    ShortcutCheck.SetBounds(WizardForm.RunList.Left, WizardForm.RunList.Top + ScaleY(30),
      WizardForm.RunList.Width, ScaleY(24));
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssDone) and (not WizardSilent) then
    if ShortcutCheck.Checked then CreateDesktopShortcut;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Folder, TempFile: String;
begin
  Result := '';
  Folder := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  if (Length(Folder) <= 3) or (CompareText(Folder, ExpandConstant('{win}')) = 0) or
     (CompareText(Folder, ExpandConstant('{sys}')) = 0) then begin
    Result := CustomMessage('ChooseSubfolder');
    exit;
  end;
  if not ForceDirectories(Folder) then begin
    Result := CustomMessage('NotWritable');
    exit;
  end;
  TempFile := StringOfChar(#0, 260);
  if GetTempFileNameW(Folder, 'll', 0, TempFile) = 0 then
    Result := CustomMessage('NotWritable')
  else DeleteFile(Copy(TempFile, 1, Pos(#0, TempFile) - 1));
end;

function InitializeUninstall: Boolean;
var
  Form: TSetupForm;
  Intro, Details: TNewStaticText;
  Keep, Purge: TNewRadioButton;
  OK, Cancel: TNewButton;
begin
  Result := False;
  CreateMutex('LottoLens.Maintenance');
  PurgeData := ExpandConstant('{param:PURGEDATA|0}') = '1';
  if UninstallSilent then begin
    Result := True;
    exit;
  end;
  Form := CreateCustomForm(ScaleX(530), ScaleY(280), False, False);
  try
    Form.Caption := CustomMessage('UninstallTitle');
    Form.Position := poScreenCenter;
    Intro := TNewStaticText.Create(Form); Intro.Parent := Form;
    Intro.SetBounds(ScaleX(20), ScaleY(18), ScaleX(490), ScaleY(42));
    Intro.WordWrap := True; Intro.Caption := CustomMessage('UninstallPrompt');
    Keep := TNewRadioButton.Create(Form); Keep.Parent := Form;
    Keep.SetBounds(ScaleX(20), ScaleY(68), ScaleX(490), ScaleY(24));
    Keep.Caption := CustomMessage('KeepData'); Keep.Checked := True;
    Purge := TNewRadioButton.Create(Form); Purge.Parent := Form;
    Purge.SetBounds(ScaleX(20), ScaleY(102), ScaleX(490), ScaleY(24));
    Purge.Caption := CustomMessage('PurgeData');
    Details := TNewStaticText.Create(Form); Details.Parent := Form;
    Details.SetBounds(ScaleX(20), ScaleY(143), ScaleX(490), ScaleY(83));
    Details.WordWrap := True;
    Details.Caption := CustomMessage('DataDetails') + #13#10 + ExpandConstant('{app}\data');
    OK := TNewButton.Create(Form); OK.Parent := Form;
    OK.SetBounds(ScaleX(310), ScaleY(241), ScaleX(96), ScaleY(26));
    OK.Caption := CustomMessage('Uninstall'); OK.ModalResult := mrOK; OK.Default := True;
    Cancel := TNewButton.Create(Form); Cancel.Parent := Form;
    Cancel.SetBounds(ScaleX(414), ScaleY(241), ScaleX(96), ScaleY(26));
    Cancel.Caption := CustomMessage('Cancel'); Cancel.ModalResult := mrCancel; Cancel.Cancel := True;
    if Form.ShowModal <> mrOK then exit;
    PurgeData := Purge.Checked;
    if PurgeData and (MsgBox(CustomMessage('ConfirmPurge') + #13#10#13#10 +
      ExpandConstant('{app}\data'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) <> IDYES) then exit;
    Result := True;
  finally
    Form.Free;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Arguments: String;
  Code: Integer;
begin
  if CurUninstallStep = usUninstall then begin
    Arguments := '--uninstall-cleanup';
    if PurgeData then Arguments := Arguments + ' --purge-data';
    if not Exec(ExpandConstant('{app}\LottoLens.exe'), Arguments, ExpandConstant('{app}'),
        SW_HIDE, ewWaitUntilTerminated, Code) then
      RaiseException(CustomMessage('CleanupFailed'));
    if Code <> 0 then RaiseException(CustomMessage('CleanupFailed'));
  end;
end;
