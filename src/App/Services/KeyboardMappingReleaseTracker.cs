namespace IPhoneMirror.App.Services;

/// <summary>
/// Pairs every key release with the decision taken for its press. The mapped-key
/// filter decides per event whether a device key is swallowed by a keyboard
/// mapping, but that decision depends on live modifier state: Shift+A forwards
/// A-down to the phone, and if Shift is released first the plain A-up would be
/// mapped and swallowed, leaving A pressed on the device. Remembering what
/// happened to the press keeps the key-up on the same path.
/// </summary>
internal sealed class KeyboardMappingReleaseTracker
{
    private readonly Dictionary<int, bool> _pressSkipped = [];

    /// <summary>
    /// Returns whether this event must be skipped. <paramref name="mappedNow"/>
    /// is the filter's current verdict for the key; it is authoritative only for
    /// the first press of a key and for a release whose press was never seen.
    /// Auto-repeat presses and the release reuse the first press's decision, so
    /// a key that reached the device is repeated and released there even if the
    /// modifier state changed while it was held.
    /// </summary>
    public bool ShouldSkip(int virtualKey, bool down, bool mappedNow)
    {
        if (down)
        {
            if (_pressSkipped.TryGetValue(virtualKey, out var repeated)) return repeated;
            _pressSkipped[virtualKey] = mappedNow;
            return mappedNow;
        }
        return _pressSkipped.Remove(virtualKey, out var skipped) ? skipped : mappedNow;
    }

    /// <summary>Forgets outstanding presses after a keyboard reset or route change.</summary>
    public void Reset() => _pressSkipped.Clear();
}
