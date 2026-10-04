using System.Globalization;
using System.Windows;
using IPhoneMirror.Shared.Localization;

namespace IPhoneMirror.DriverInstaller.Services;

/// <summary>
/// Resource lookup for the driver manager. Language selection and culture
/// mapping come from the shared <see cref="LanguageCatalog"/>; the stored user
/// preference comes from <see cref="LanguagePreference"/>, so this process can
/// never disagree with the main app about which dictionary to load.
/// </summary>
internal static class DriverLocalization
{
    internal const string Chinese = LanguageCatalog.SimplifiedChinese;
    internal const string TraditionalChineseHongKong = LanguageCatalog.TraditionalChineseHongKong;
    internal const string TraditionalChineseTaiwan = LanguageCatalog.TraditionalChineseTaiwan;
    internal const string English = LanguageCatalog.English;

    internal static string Language { get; private set; } = LanguageCatalog.Fallback;
    internal static CultureInfo Culture { get; private set; } = CultureInfo.GetCultureInfo(LanguageCatalog.Fallback);

    internal static void Initialize(IReadOnlyList<string> arguments)
    {
        var requested = ReadArgument(arguments) ?? LanguagePreference.Read();
        Language = LanguageCatalog.ResolvePreference(requested);
        Culture = CultureInfo.GetCultureInfo(Language);
        CultureInfo.CurrentCulture = Culture;
        CultureInfo.CurrentUICulture = Culture;
        CultureInfo.DefaultThreadCurrentCulture = Culture;
        CultureInfo.DefaultThreadCurrentUICulture = Culture;
    }

    internal static string Get(string key) =>
        Application.Current?.TryFindResource(key) as string ?? key;

    internal static string GetOrDefault(string key, string fallback) =>
        Application.Current?.TryFindResource(key) as string ?? fallback;

    internal static string Format(string key, params object?[] arguments) =>
        string.Format(Culture, Get(key), arguments);

    internal static ResourceDictionary CreateDictionary() => new()
    {
        Source = new Uri($"{LanguageCatalog.DictionaryPrefix}{Language}.xaml", UriKind.Relative),
    };


    internal static string LocalizeOperationResult(string message)
    {
        if (message is "ParentBindingComplete" or "ParentBindingRestartRequired" or
            "ParentResetRestartRequired" or "ParentResetComplete" or "ParentChangeRejected" or
            "ParentChangeRolledBack" or "ParentRollbackRestartRequired" or "ParentChangeRecoveryNeeded")
            return Get(message);
        // Translate only known application messages, never arbitrary device names,
        // paths, native diagnostics, or protocol fields.
        (string Prefix, string Key)[] messages =
        [
            ("The incorrect Apple parent device was removed. Reconnect the iPhone to rebind usbccgp.", "DriverParentRemoved"),
            ("Selected-device capture filter removed. Reconnect the device to complete unload.", "DriverFilterRemovedReconnect"),
            ("Selected-device capture filter installed. Reconnect the device to complete activation.", "DriverFilterInstalledReconnect"),
            ("Parent driver repair stopped after the removal request began. Reconnect the iPhone and review the operation log. ", "DriverParentRepairStopped"),
            ("Parent driver repair was rejected before any system change. ", "DriverParentRepairRejected"),
            ("Driver operation failed and all captured state was restored. ", "DriverOperationRolledBack"),
            ("Driver operation failed and rollback was incomplete. Review the operation log. ", "DriverOperationRollbackIncomplete"),
        ];
        foreach (var (prefix, key) in messages)
        {
            if (!message.StartsWith(prefix, StringComparison.Ordinal)) continue;
            var translated = Get(key);
            if (translated == key) return message;
            var detail = message[prefix.Length..];
            return detail.Length == 0 ? translated
                : translated + "\n" + Format("DriverOperationDetailsFormat", detail);
        }
        return message;
    }

    private static string? ReadArgument(IReadOnlyList<string> arguments)
    {
        for (var index = 0; index + 1 < arguments.Count; ++index)
            if (string.Equals(arguments[index], "--language", StringComparison.OrdinalIgnoreCase))
                return arguments[index + 1];
        return null;
    }

    internal static string ResolveCultureName(string cultureName) =>
        LanguageCatalog.ResolveCultureName(cultureName);
}
