#pragma once

#include <string>
#include <string_view>

// Text that crosses the native/managed boundary (im_last_error, device status,
// environment diagnostics, capture status) is never a human sentence. It is a
// stable message key from this header, optionally followed by ": " and a
// technical detail, and several keyed messages may be joined with "; ".
//
// The managed host owns every translation: it looks the key up in the active
// Strings.*.xaml dictionary and renders the detail with the localized template.
// Unknown text passes through unchanged, so protocol markers such as
// DRM_VIDEO_PROTECTED and raw libusb/Win32 diagnostics stay intact. Adding a
// message therefore means adding a key here and one string per language in
// src/App/Localization; no translation lives in native code.
namespace iPhoneMirror::messages {

inline constexpr std::wstring_view DetailSeparator = L": ";
inline constexpr std::wstring_view SegmentSeparator = L"; ";

namespace key {

// Shared
inline constexpr std::wstring_view UnknownError = L"NativeUnknownError";

// CoreApi (im_last_error)
inline constexpr std::wstring_view CoreNotInitialized = L"NativeCoreNotInitialized";
inline constexpr std::wstring_view CoreInitUnknownError = L"NativeCoreInitUnknownError";
inline constexpr std::wstring_view CoreShutDownDuringPreviewInit = L"NativeCoreShutDownDuringPreviewInit";
inline constexpr std::wstring_view WinsockInitFailed = L"NativeWinsockInitFailed";
inline constexpr std::wstring_view DeviceRequired = L"NativeDeviceRequired";
inline constexpr std::wstring_view CountRequired = L"NativeCountRequired";
inline constexpr std::wstring_view UsbOpenFailed = L"NativeUsbOpenFailed";
inline constexpr std::wstring_view UsbConfigurationSwitching = L"NativeUsbConfigurationSwitching";
inline constexpr std::wstring_view UsbRestoreFailed = L"NativeUsbRestoreFailed";
inline constexpr std::wstring_view DeviceListBufferTooSmall = L"NativeDeviceListBufferTooSmall";
inline constexpr std::wstring_view DeviceRefreshFailed = L"NativeDeviceRefreshFailed";
inline constexpr std::wstring_view EnvironmentInfoVersionMismatch = L"NativeEnvironmentInfoVersionMismatch";
inline constexpr std::wstring_view EnvironmentReadFailed = L"NativeEnvironmentReadFailed";
inline constexpr std::wstring_view CaptureOptionsInvalid = L"NativeCaptureOptionsInvalid";
inline constexpr std::wstring_view CaptureStatusVersionMismatch = L"NativeCaptureStatusVersionMismatch";
inline constexpr std::wstring_view WaitingForDevice = L"NativeWaitingForDevice";
inline constexpr std::wstring_view NoCaptureSession = L"NativeNoCaptureSession";
inline constexpr std::wstring_view WaitingForFirstFrame = L"NativeWaitingForFirstFrame";
inline constexpr std::wstring_view VideoTimestampPointerInvalid = L"NativeVideoTimestampPointerInvalid";
inline constexpr std::wstring_view VideoFrameInfoVersionMismatch = L"NativeVideoFrameInfoVersionMismatch";
inline constexpr std::wstring_view VideoFrameTooLarge = L"NativeVideoFrameTooLarge";
inline constexpr std::wstring_view VideoFrameLayoutInvalid = L"NativeVideoFrameLayoutInvalid";
inline constexpr std::wstring_view ScaledFrameArgumentsInvalid = L"NativeScaledFrameArgumentsInvalid";
inline constexpr std::wstring_view ScaledFrameTooLarge = L"NativeScaledFrameTooLarge";
inline constexpr std::wstring_view ScaledFrameLayoutInvalid = L"NativeScaledFrameLayoutInvalid";
inline constexpr std::wstring_view PreviewWindowInvalid = L"NativePreviewWindowInvalid";
inline constexpr std::wstring_view PreviewInitFailed = L"NativePreviewInitFailed";
inline constexpr std::wstring_view NoPreviewWindow = L"NativeNoPreviewWindow";
inline constexpr std::wstring_view PreviewCornerArgumentsInvalid = L"NativePreviewCornerArgumentsInvalid";
inline constexpr std::wstring_view RenderArgumentsInvalid = L"NativeRenderArgumentsInvalid";
inline constexpr std::wstring_view VolumeOutOfRange = L"NativeVolumeOutOfRange";

// DeviceManager (device status)
inline constexpr std::wstring_view DeviceLockdownDenied = L"NativeDeviceLockdownDenied";
inline constexpr std::wstring_view DeviceUsbConnected = L"NativeDeviceUsbConnected";
inline constexpr std::wstring_view DevicePairedValidating = L"NativeDevicePairedValidating";
inline constexpr std::wstring_view DeviceAwaitingTrust = L"NativeDeviceAwaitingTrust";
inline constexpr std::wstring_view DeviceConnectedPaired = L"NativeDeviceConnectedPaired";
inline constexpr std::wstring_view DeviceConnectedPairingUnconfirmed = L"NativeDeviceConnectedPairingUnconfirmed";
inline constexpr std::wstring_view DevicePairedUnlockRequired = L"NativeDevicePairedUnlockRequired";

// DeviceManager (environment diagnostic segments)
inline constexpr std::wstring_view EnvLibUsb0Ready = L"NativeEnvLibUsb0Ready";
inline constexpr std::wstring_view EnvAppleSupportMissing = L"NativeEnvAppleSupportMissing";
inline constexpr std::wstring_view EnvAppleServiceNotRunning = L"NativeEnvAppleServiceNotRunning";
inline constexpr std::wstring_view EnvLibUsbEnumerationReady = L"NativeEnvLibUsbEnumerationReady";
inline constexpr std::wstring_view EnvPairingReady = L"NativeEnvPairingReady";
inline constexpr std::wstring_view EnvCaptureMuxReady = L"NativeEnvCaptureMuxReady";
inline constexpr std::wstring_view EnvUsbMuxUnavailable = L"NativeEnvUsbMuxUnavailable";
inline constexpr std::wstring_view EnvLibUsbLoaded = L"NativeEnvLibUsbLoaded";
inline constexpr std::wstring_view EnvUsbDkAvailable = L"NativeEnvUsbDkAvailable";
inline constexpr std::wstring_view EnvUsbDkUnavailable = L"NativeEnvUsbDkUnavailable";
inline constexpr std::wstring_view EnvUsbDkUnprobed = L"NativeEnvUsbDkUnprobed";
inline constexpr std::wstring_view EnvLibUsbRuntimeMissing = L"NativeEnvLibUsbRuntimeMissing";
inline constexpr std::wstring_view EnvLibUsb0Present = L"NativeEnvLibUsb0Present";

// CaptureSession (capture status message)
inline constexpr std::wstring_view CaptureActivatingUsb = L"NativeCaptureActivatingUsb";
inline constexpr std::wstring_view CaptureStopping = L"NativeCaptureStopping";
inline constexpr std::wstring_view CaptureStopped = L"NativeCaptureStopped";
inline constexpr std::wstring_view CaptureCancelled = L"NativeCaptureCancelled";
inline constexpr std::wstring_view CaptureUsbRestoreUnconfirmed = L"NativeCaptureUsbRestoreUnconfirmed";
inline constexpr std::wstring_view CaptureAwaitingReconnect = L"NativeCaptureAwaitingReconnect";
inline constexpr std::wstring_view CaptureAwaitingPing = L"NativeCaptureAwaitingPing";
inline constexpr std::wstring_view CaptureReconnectingNoFrames = L"NativeCaptureReconnectingNoFrames";
inline constexpr std::wstring_view CaptureStreaming = L"NativeCaptureStreaming";
inline constexpr std::wstring_view CaptureFailed = L"NativeCaptureFailed";

} // namespace key

// A single keyed message without detail.
inline std::wstring text(std::wstring_view message_key) {
    return std::wstring(message_key);
}

// A keyed message carrying a technical detail (error text, version, ...).
inline std::wstring text(std::wstring_view message_key, std::wstring_view detail) {
    std::wstring result(message_key);
    if (detail.empty()) return result;
    result += DetailSeparator;
    result += detail;
    return result;
}

// Appends one more keyed message to a multi-segment diagnostic.
inline void append(std::wstring& diagnostic, std::wstring_view message_key,
                   std::wstring_view detail = {}) {
    if (!diagnostic.empty()) diagnostic += SegmentSeparator;
    diagnostic += text(message_key, detail);
}

} // namespace iPhoneMirror::messages
