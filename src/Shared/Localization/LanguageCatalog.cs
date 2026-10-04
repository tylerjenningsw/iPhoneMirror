using System.Globalization;

namespace IPhoneMirror.Shared.Localization;

/// <summary>
/// Single source of truth for the languages the product ships. Every process
/// (main app, driver manager, tests, tooling) resolves a requested or system
/// culture through this catalog, so adding a language means adding one entry
/// here plus one resource dictionary per project. Nothing else may hard-code
/// culture names or the Traditional/Simplified Chinese mapping.
/// </summary>
internal static class LanguageCatalog
{
    /// <summary>Settings value meaning "follow the Windows display language".</summary>
    internal const string SystemLanguage = "system";

    internal const string SimplifiedChinese = "zh-CN";
    internal const string TraditionalChineseHongKong = "zh-HK";
    internal const string TraditionalChineseTaiwan = "zh-TW";
    internal const string English = "en-US";

    /// <summary>Language used when nothing else matches.</summary>
    internal const string Fallback = English;

    /// <summary>
    /// Shipped languages, in presentation order. A resource dictionary named
    /// <c>Localization/Strings.{code}.xaml</c> must exist for each entry in
    /// every localized project.
    /// </summary>
    internal static readonly IReadOnlyList<string> Supported =
        [SimplifiedChinese, TraditionalChineseHongKong, TraditionalChineseTaiwan, English];

    /// <summary>Relative resource path prefix shared by every project.</summary>
    internal const string DictionaryPrefix = "Localization/Strings.";

    internal static bool IsSupported(string? code) =>
        code is not null && Supported.Contains(code, StringComparer.OrdinalIgnoreCase);

    /// <summary>
    /// Normalizes a persisted or command-line language preference. Returns a
    /// supported culture code, or <see cref="SystemLanguage"/> for null, empty,
    /// "system" and anything unknown, so callers never need a validity check.
    /// </summary>
    internal static string NormalizePreference(string? requested)
    {
        if (string.IsNullOrWhiteSpace(requested) ||
            requested.Equals(SystemLanguage, StringComparison.OrdinalIgnoreCase))
            return SystemLanguage;
        foreach (var code in Supported)
            if (code.Equals(requested, StringComparison.OrdinalIgnoreCase)) return code;
        return SystemLanguage;
    }

    /// <summary>
    /// Resolves a preference to the concrete culture whose dictionary will load:
    /// an explicit supported code is returned as-is, and
    /// <see cref="SystemLanguage"/> maps the Windows display language.
    /// </summary>
    internal static string ResolvePreference(string? requested)
    {
        var normalized = NormalizePreference(requested);
        return normalized == SystemLanguage ? ResolveSystemCulture() : normalized;
    }

    internal static string ResolveSystemCulture() =>
        ResolveCultureName(CultureInfo.InstalledUICulture.Name);

    /// <summary>
    /// Maps any BCP-47 culture name to the closest shipped language. Taiwan
    /// cultures use the independent Taiwan dictionary, the other Traditional
    /// Chinese variants share the Hong Kong dictionary, every other Chinese
    /// variant uses Simplified Chinese, other languages match a shipped entry by
    /// exact code or by language subtag, and the rest fall back to
    /// <see cref="Fallback"/>.
    /// </summary>
    internal static string ResolveCultureName(string? cultureName)
    {
        if (string.IsNullOrWhiteSpace(cultureName)) return Fallback;
        if (IsTaiwanTraditionalChinese(cultureName)) return TraditionalChineseTaiwan;
        if (IsTraditionalChinese(cultureName)) return TraditionalChineseHongKong;
        if (cultureName.StartsWith("zh", StringComparison.OrdinalIgnoreCase))
            return SimplifiedChinese;
        foreach (var code in Supported)
            if (code.Equals(cultureName, StringComparison.OrdinalIgnoreCase)) return code;
        var language = LanguageSubtag(cultureName);
        foreach (var code in Supported)
            if (LanguageSubtag(code).Equals(language, StringComparison.OrdinalIgnoreCase))
                return code;
        return Fallback;
    }

    /// <summary>
    /// Relative WPF resource URI of a project's dictionary for one culture.
    /// </summary>
    internal static Uri DictionaryUri(string assemblyName, string cultureName) =>
        new($"/{assemblyName};component/{DictionaryPrefix}{cultureName}.xaml",
            UriKind.Relative);

    internal static bool IsDictionarySource(string? source) =>
        source?.Contains(DictionaryPrefix, StringComparison.OrdinalIgnoreCase) == true;

    private static bool IsTaiwanTraditionalChinese(string cultureName) =>
        cultureName.Equals(TraditionalChineseTaiwan, StringComparison.OrdinalIgnoreCase) ||
        cultureName.Equals("zh-Hant-TW", StringComparison.OrdinalIgnoreCase);

    private static bool IsTraditionalChinese(string cultureName) =>
        cultureName.StartsWith("zh-Hant", StringComparison.OrdinalIgnoreCase) ||
        cultureName.Equals("zh-CHT", StringComparison.OrdinalIgnoreCase) ||
        cultureName.Equals(TraditionalChineseHongKong, StringComparison.OrdinalIgnoreCase) ||
        cultureName.Equals("zh-MO", StringComparison.OrdinalIgnoreCase);

    private static string LanguageSubtag(string cultureName)
    {
        var separator = cultureName.IndexOf('-');
        return separator < 0 ? cultureName : cultureName[..separator];
    }
}
