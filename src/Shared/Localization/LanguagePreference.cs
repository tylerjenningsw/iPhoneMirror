using System.IO;
using System.Text.Json;

namespace IPhoneMirror.Shared.Localization;

/// <summary>
/// Location and read-only access to the user's language preference. The main
/// app owns the settings file; the driver manager and other helpers only read
/// the <c>Language</c> value, so they share this definition instead of
/// re-declaring the path and JSON shape.
/// </summary>
internal static class LanguagePreference
{
    internal const string PropertyName = "Language";

    internal static readonly string SettingsPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "iPhoneMirror", "settings.json");

    /// <summary>
    /// Reads the stored preference, normalized through
    /// <see cref="LanguageCatalog.NormalizePreference"/>. Any missing file,
    /// malformed JSON or unknown value yields <see cref="LanguageCatalog.SystemLanguage"/>.
    /// </summary>
    internal static string Read(string? path = null)
    {
        path ??= SettingsPath;
        try
        {
            if (!File.Exists(path)) return LanguageCatalog.SystemLanguage;
            using var document = JsonDocument.Parse(File.ReadAllText(path));
            return document.RootElement.ValueKind == JsonValueKind.Object &&
                document.RootElement.TryGetProperty(PropertyName, out var value) &&
                value.ValueKind == JsonValueKind.String
                ? LanguageCatalog.NormalizePreference(value.GetString())
                : LanguageCatalog.SystemLanguage;
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or JsonException)
        {
            return LanguageCatalog.SystemLanguage;
        }
    }
}
