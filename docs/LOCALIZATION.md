# Localization

iPhoneMirror ships in Simplified Chinese (`zh-CN`), Traditional Chinese for
Hong Kong (`zh-HK`) and English (`en-US`). Every process in the product reads
the same language preference and resolves it through one shared catalog, so a
language is a set of data files, never a code path. This document describes
that contract and the exact steps for adding a language.

## Single sources of truth

| Concern | Owner | Must not be duplicated in |
|---|---|---|
| Which languages exist, culture mapping, dictionary URIs | `src/Shared/Localization/LanguageCatalog.cs` | App, driver manager, tests, scripts |
| Where the user's language preference is stored and how it is read | `src/Shared/Localization/LanguagePreference.cs` | `DriverLocalization`, `LocalizationService` |
| UI text for the main app | `src/App/Localization/Strings.{culture}.xaml` | C#, XAML attributes, native code |
| UI text for the driver manager | `src/DriverInstaller/Localization/Strings.{culture}.xaml` | C#, XAML attributes |
| Text produced by the native core | Message keys in `src/Core/src/Messages.h`, translated by the app dictionaries | C++ literals |
| Startup-error captions | The app dictionaries, with an English last-resort copy in `StartupDiagnostics.FallbackText` | Per-language tables in C# |

`scripts/verify_localization.ps1` (run by CI) and `scripts/audit_localization.py`
enforce these rules: identical key sets across dictionaries, matching format
placeholders, every native key present in every language, no CJK literals in
`src/Core`, and startup fallback text equal to the `en-US` resource.

## How a language is selected

1. The main app stores the preference as `Language` in
   `%LOCALAPPDATA%\iPhoneMirror\settings.json`. Valid values are `system` or a
   code from `LanguageCatalog.Supported`.
2. `LanguageCatalog.NormalizePreference` turns any stored or command-line value
   into a supported code or `system`; `ResolvePreference` maps `system` to the
   Windows display language through `ResolveCultureName`.
3. `ResolveCultureName` maps a BCP-47 name to the closest shipped language:
   Traditional Chinese variants (`zh-Hant-*`, `zh-TW`, `zh-HK`, `zh-MO`,
   `zh-CHT`) use `zh-HK`, every other `zh*` uses `zh-CN`, other cultures match
   a shipped code exactly or by language subtag (`en-GB` to `en-US`), and
   anything else falls back to `LanguageCatalog.Fallback`.
4. `LocalizationService` (app) and `DriverLocalization` (driver manager) load
   `Localization/Strings.{culture}.xaml` for the resolved culture and set the
   thread cultures. The driver manager also accepts `--language <code>` when the
   app launches it, so both processes always agree.

## Native core messages

The C++ core never emits sentences. `im_last_error`, device status text, the
environment diagnostic and capture status messages contain a key declared in
`src/Core/src/Messages.h`, in one of three shapes:

```text
NativeCoreNotInitialized
NativeUsbOpenFailed: LIBUSB_ERROR_ACCESS
NativeEnvPairingReady; NativeEnvLibUsbLoaded: 1.0.27; NativeEnvUsbDkUnprobed
```

`IPhoneMirror.App.Localization.NativeMessages.Localize` is applied once, in
`NativeCore` at the interop boundary. It looks the key up in the active
dictionary, substitutes a detail into `{0}` when the template has one or
appends it with `NativeMessageDetailFormat` otherwise, and joins chained
segments with a space. Text that is not a known key passes through unchanged,
which keeps protocol markers such as `DRM_VIDEO_PROTECTED` and raw libusb or
Win32 diagnostics intact. Managed code that inspects native text (for example
`CaptureErrorGuidance` or `ProtectedContentStatus`) therefore keeps matching on
those stable ASCII markers, never on translated words.

To add a native message:

1. Add a `std::wstring_view` constant to `Messages.h` whose value starts with
   `Native`.
2. Emit it with `msg::text(key)`, `msg::text(key, detail)` or
   `msg::append(diagnostic, key, detail)`.
3. Add the key to all three `src/App/Localization/Strings.*.xaml` files. Use
   `{0}` where the detail belongs inside the sentence.

## Adding a language

Adding, for example, Japanese (`ja-JP`) touches data files plus one registry
entry. No translation logic changes.

1. **Catalog.** In `LanguageCatalog.cs` add
   `internal const string Japanese = "ja-JP";` and append it to `Supported`.
   `ResolveCultureName` now maps `ja` and `ja-*` cultures to it automatically.
2. **App dictionary.** Copy `src/App/Localization/Strings.en-US.xaml` to
   `Strings.ja-JP.xaml`, translate every value and keep every key. Add a
   `LanguageJapanese` display-name key to all dictionaries.
3. **Driver manager dictionary.** Do the same for
   `src/DriverInstaller/Localization/Strings.en-US.xaml`.
4. **Project files.** Add the two new `Strings.ja-JP.xaml` files as `Page`
   items next to the existing dictionaries in `iPhoneMirror.App.csproj` and
   `iPhoneMirror.DriverInstaller.csproj`, and extend the `Strings.*.xaml`
   embedded-resource globs if they are not already wildcarded.
5. **Language picker.** Add one `ComboBoxItem` with `Tag="ja-JP"` and
   `Content="{DynamicResource LanguageJapanese}"` to the language `ComboBox` in
   `src/App/MainWindow.xaml`.
6. **Installer.** Add a `[Languages]` entry in `installer/iPhoneMirror.iss`
   pointing at the Inno Setup Japanese `.isl` file, and translate the
   `CustomMessages` block for the new code.
7. **Cleanup script.** Add a `ja-JP` object to `$script:CleanupMessages` in
   `scripts/remove_selected_iphone_drivers.ps1`, then update `ScriptHash` in
   `DriverCleanupHost.cs` as described in that file.
8. **Verification.** Run `scripts/verify_localization.ps1`,
   `python scripts/audit_localization.py`, the logic tests and
   `App.Runtime.Tests --localization-audit`. The scripts read the language list
   from `LanguageCatalog.cs`, so the new language is checked automatically.

## Rules for new UI text

- Put text in the dictionaries and reference it with `{DynamicResource Key}` in
  XAML or `LocalizationService.Get`/`Format` in C#. Never build a sentence from
  fragments in code; add a format string with placeholders instead.
- Keep technical data (device names, paths, error codes, libusb and Win32
  messages, protocol fields) as `{0}`-style arguments so it survives language
  changes unchanged.
- Use `LocalizationService.Format`/`Join` for text that windows cache, so an
  open window can re-render it when the user switches language.
- Hong Kong text follows the terminology already in `Strings.zh-HK.xaml`
  (`裝置`, `驅動程式`, `鏡像`, `擷取`, `記錄`); the verification script rejects
  mainland terms in that file.
