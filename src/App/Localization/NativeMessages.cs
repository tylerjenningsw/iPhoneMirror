using System.Text.RegularExpressions;

namespace IPhoneMirror.App.Localization;

/// <summary>
/// Translates text produced by the native core. The core never emits sentences;
/// it emits message keys declared in <c>src/Core/src/Messages.h</c>, optionally
/// followed by <c>": "</c> and a technical detail, and a diagnostic may chain
/// several such messages with <c>"; "</c>. Each key has one string per language
/// in <c>Strings.*.xaml</c>, so native text follows the UI language without any
/// translation living in C++.
/// <para>
/// Anything that is not a known key passes through unchanged: protocol markers
/// (for example <c>DRM_VIDEO_PROTECTED</c>), libusb or Win32 diagnostics, and
/// device names are never rewritten.
/// </para>
/// </summary>
internal static partial class NativeMessages
{
    /// <summary>Prefix shared by every key the native core may emit.</summary>
    internal const string KeyPrefix = "Native";
    internal const string DetailSeparator = ": ";
    internal const string SegmentSeparator = "; ";
    private const string DetailFormatKey = "NativeMessageDetailFormat";
    private const string SegmentJoin = " ";

    [GeneratedRegex(@"^(Native[A-Za-z0-9]+)(?:: (.*))?$", RegexOptions.Singleline | RegexOptions.CultureInvariant)]
    private static partial Regex MessagePattern();

    /// <summary>
    /// Returns the localized rendering of <paramref name="text"/>, or the input
    /// itself when it is empty, not keyed, or uses a key that no dictionary
    /// defines.
    /// </summary>
    internal static string Localize(string? text)
    {
        if (string.IsNullOrEmpty(text)) return text ?? string.Empty;
        if (TryLocalizeSingle(text, out var single)) return single;

        // A multi-segment diagnostic only counts when every segment is a known
        // key; otherwise a raw detail containing "; " would be torn apart.
        if (!text.Contains(SegmentSeparator, StringComparison.Ordinal)) return text;
        var segments = text.Split(SegmentSeparator, StringSplitOptions.None);
        var localized = new string[segments.Length];
        for (var index = 0; index < segments.Length; ++index)
        {
            if (!TryLocalizeSingle(segments[index], out localized[index])) return text;
        }
        return LocalizationService.Join(SegmentJoin, localized);
    }

    /// <summary>
    /// Splits one native message into its key and optional detail. Returns false
    /// for text that does not follow the key contract.
    /// </summary>
    internal static bool TryParse(string? text, out string key, out string? detail)
    {
        key = string.Empty;
        detail = null;
        if (string.IsNullOrEmpty(text)) return false;
        var match = MessagePattern().Match(text);
        if (!match.Success) return false;
        key = match.Groups[1].Value;
        detail = match.Groups[2].Success ? match.Groups[2].Value : null;
        return true;
    }

    private static bool TryLocalizeSingle(string text, out string localized)
    {
        localized = text;
        if (!TryParse(text, out var key, out var detail)) return false;
        var template = LocalizationService.Get(key);
        // Get returns the key itself when no dictionary defines it.
        if (template == key) return false;
        if (detail is null)
        {
            localized = template;
            return true;
        }
        // Templates that place the detail themselves use {0}; the rest get the
        // generic "message: detail" layout of the active language.
        localized = template.Contains("{0}", StringComparison.Ordinal)
            ? LocalizationService.Format(key, detail)
            : LocalizationService.Format(DetailFormatKey, template, detail);
        return true;
    }
}
