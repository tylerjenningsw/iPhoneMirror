using System.Globalization;
using System.Windows;
using IPhoneMirror.App.Services;
using IPhoneMirror.App.Updater;
using IPhoneMirror.Shared.Localization;

namespace IPhoneMirror.App.Localization;

/// <summary>
/// WPF-side language switching for the main app. Which languages exist and how
/// a culture maps onto them is owned by <see cref="LanguageCatalog"/>; this
/// class only swaps the merged resource dictionary and the thread cultures.
/// </summary>
internal static class LocalizationService
{
    internal const string SystemLanguage = LanguageCatalog.SystemLanguage;
    internal const string SimplifiedChinese = LanguageCatalog.SimplifiedChinese;
    internal const string TraditionalChineseHongKong = LanguageCatalog.TraditionalChineseHongKong;
    internal const string TraditionalChineseTaiwan = LanguageCatalog.TraditionalChineseTaiwan;
    internal const string English = LanguageCatalog.English;

    private static string _selectedLanguage = SystemLanguage;
    private static CultureInfo _effectiveCulture = CultureInfo.GetCultureInfo(LanguageCatalog.Fallback);

    internal static event EventHandler? LanguageChanged;

    internal static string SelectedLanguage => _selectedLanguage;
    internal static CultureInfo EffectiveCulture => _effectiveCulture;
    internal static string StartupCultureName =>
        LanguageCatalog.ResolvePreference(_selectedLanguage);

    internal static void Initialize()
    {
        var configured = LoadLanguage();
        ApplyLanguage(configured, persist: false, notify: false);
    }

    internal static void SetLanguage(string language) =>
        ApplyLanguage(language, persist: true, notify: true);

    internal static string Get(string key)
    {
        if (Application.Current?.TryFindResource(key) is string value)
            return LocalizedText.Resource(key, value);
        return key;
    }

    internal static string GetOrDefault(string key, string fallback) =>
        Application.Current?.TryFindResource(key) is string value
            ? LocalizedText.Resource(key, value) : fallback;

    internal static string Format(string key, params object?[] arguments) =>
        LocalizedText.Format(key, arguments);

    internal static string RefreshText(string value) => LocalizedText.Refresh(value);

    internal static string Join(string separator, IEnumerable<string?> values) =>
        LocalizedText.Join(separator, values);

    internal static void RefreshWhenLanguageChanges(Window window, Action refresh)
    {
        var closed = false;
        void Changed(object? sender, EventArgs args)
        {
            if (closed || window.Dispatcher.HasShutdownStarted) return;
            if (window.Dispatcher.CheckAccess()) refresh();
            else window.Dispatcher.BeginInvoke(new Action(() => { if (!closed) refresh(); }));
        }
        LanguageChanged += Changed;
        window.Closed += (_, _) => { closed = true; LanguageChanged -= Changed; };
    }

    private static void ApplyLanguage(string language, bool persist, bool notify)
    {
        language = LanguageCatalog.NormalizePreference(language);
        var cultureName = LanguageCatalog.ResolvePreference(language);
        var culture = CultureInfo.GetCultureInfo(cultureName);

        // Record the requested language before loading its resource dictionary so a
        // startup-failure dialog remains localized even when that load throws.
        _selectedLanguage = language;
        var application = Application.Current;
        if (application is not null)
        {
            var dictionaries = application.Resources.MergedDictionaries;
            var replacement = new ResourceDictionary
            {
                Source = LanguageCatalog.DictionaryUri(
                    typeof(LocalizationService).Assembly.GetName().Name!, cultureName),
            };
            var existingIndex = -1;
            for (var index = 0; index < dictionaries.Count; ++index)
            {
                if (LanguageCatalog.IsDictionarySource(dictionaries[index].Source?.OriginalString))
                {
                    existingIndex = index;
                    break;
                }
            }
            if (existingIndex >= 0) dictionaries[existingIndex] = replacement;
            else dictionaries.Insert(0, replacement);
        }

        _effectiveCulture = culture;
        CultureInfo.CurrentCulture = culture;
        CultureInfo.CurrentUICulture = culture;
        CultureInfo.DefaultThreadCurrentCulture = culture;
        CultureInfo.DefaultThreadCurrentUICulture = culture;

        if (persist) SaveLanguage(language);
        if (notify) LanguageChanged?.Invoke(null, EventArgs.Empty);
    }

    internal static string ResolveCultureName(string cultureName) =>
        LanguageCatalog.ResolveCultureName(cultureName);

    private static string LoadLanguage() => LanguagePreference.Read();

    private static void SaveLanguage(string language, string? settingsPath = null)
    {
        try
        {
            new UpdateSettingsStore(settingsPath ?? LanguagePreference.SettingsPath).Update(settings =>
                settings.Language = language);
        }
        catch (Exception error)
        {
            // Language switching must remain usable even if settings cannot be saved.
            DiagnosticLogger.Exception("localization", "language_save_failed", error);
        }
    }
}
