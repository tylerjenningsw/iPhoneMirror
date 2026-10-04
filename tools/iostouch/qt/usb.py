"""pyusb device layer: find the iPhone, activate the hidden QuickTime configuration, claim interface 0x2A, transfer data.

Windows must use the **libusb-win32 filter driver + libusb0 backend** (coexists with the Apple driver);
the libusb-1.0 backend only works when WinUSB takes over the device, which breaks usbmuxd, so it is not recommended.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import usb.core
import usb.util

logger = logging.getLogger(__name__)

APPLE_VID = 0x05AC
CLASS_VENDOR = 0xFF
SUBCLASS_USBMUX = 0xFE
SUBCLASS_QUICKTIME = 0x2A


def _is_timeout(exc: BaseException) -> bool:
    """libusb0 reports a timeout as a plain USBError containing 'timeout'; libusb1 raises USBTimeoutError or errno 110/10060."""
    if isinstance(exc, usb.core.USBTimeoutError):
        return True
    errno = getattr(exc, "errno", None)
    if errno in (110, 10060, 116):
        return True
    return "timeout" in str(exc).lower()


def get_backend(prefer: str = "auto"):
    """Select the pyusb backend: libusb0 (libusb-win32) first on Windows, otherwise libusb1."""
    import usb.backend.libusb0 as b0
    import usb.backend.libusb1 as b1

    order = {"auto": (b0, b1) if sys.platform == "win32" else (b1, b0), "libusb0": (b0,), "libusb1": (b1,)}[prefer]
    for mod in order:
        try:
            backend = mod.get_backend()
        except Exception as exc:  # noqa: BLE001
            logger.debug("backend %s failed: %s", mod.__name__, exc)
            backend = None
        if backend is not None:
            logger.info("USB backend: %s", mod.__name__.rsplit(".", 1)[-1])
            return backend
    raise RuntimeError(
        "No libusb backend is available. On Windows install the libusb-win32 filter driver "
        "(libusb0.dll must be on PATH or in the program directory), or pip install libusb to provide libusb-1.0.dll"
    )


class StaleConfigError(RuntimeError):
    """The device stays in the hidden configuration and the close request has no effect; callers may probe directly or hard-reset."""


@dataclass
class IosUsbDevice:
    dev: "usb.core.Device"
    serial: str
    mux_config: int
    qt_config: int
    original_config: int = -1  # configuration that was active before activation; restored on stop

    @property
    def activated(self) -> bool:
        return self.qt_config != -1

    def describe(self) -> dict:
        cfgs = []
        for cfg in self.dev:
            ifaces = []
            for intf in cfg:
                eps = [f"0x{ep.bEndpointAddress:02x}({'IN' if ep.bEndpointAddress & 0x80 else 'OUT'},{ep.wMaxPacketSize})" for ep in intf]
                ifaces.append({"number": intf.bInterfaceNumber, "class": intf.bInterfaceClass,
                               "subclass": intf.bInterfaceSubClass, "endpoints": eps})
            cfgs.append({"value": cfg.bConfigurationValue, "interfaces": ifaces})
        return {"serial": self.serial, "vid": f"0x{self.dev.idVendor:04x}", "pid": f"0x{self.dev.idProduct:04x}",
                "mux_config": self.mux_config, "qt_config": self.qt_config, "configs": cfgs}


def _find_interface_for_subclass(cfg, subclass: int):
    for intf in cfg:
        if intf.bInterfaceClass == CLASS_VENDOR and intf.bInterfaceSubClass == subclass:
            return intf
    return None


def _find_configs(dev) -> tuple[int, int]:
    mux, qt = -1, -1
    for cfg in dev:
        has_qt = _find_interface_for_subclass(cfg, SUBCLASS_QUICKTIME) is not None
        has_mux = _find_interface_for_subclass(cfg, SUBCLASS_USBMUX) is not None
        if has_mux and not has_qt:
            mux = cfg.bConfigurationValue
        if has_qt:
            qt = cfg.bConfigurationValue
    return mux, qt


def _serial_of(dev) -> str:
    try:
        s = usb.util.get_string(dev, dev.iSerialNumber) or ""
    except Exception:  # noqa: BLE001
        s = ""
    return correct_serial(s.rstrip("\x00").strip())


def correct_serial(s: str) -> str:
    """A 24-character USB serial lacks the hyphen (should be an 8-16 form UDID)."""
    if len(s) == 24 and "-" not in s:
        return s[:8] + "-" + s[8:]
    return s


def find_devices(backend=None, udid: Optional[str] = None) -> list[IosUsbDevice]:
    backend = backend or get_backend()
    found = []
    for dev in usb.core.find(find_all=True, idVendor=APPLE_VID, backend=backend):
        try:
            mux, qt = _find_configs(dev)
        except Exception as exc:  # noqa: BLE001
            logger.debug("skip device: %s", exc)
            continue
        if mux == -1 and qt == -1:
            continue
        serial = _serial_of(dev)
        if udid and serial != udid and serial.replace("-", "") != udid.replace("-", ""):
            continue
        found.append(IosUsbDevice(dev, serial, mux, qt))
    return found


def send_qt_config_request(dev, enable: bool) -> None:
    """bmRequestType=0x40 bRequest=0x52 wValue=0 wIndex=2 (open) / 0 (close)"""
    try:
        rc = dev.ctrl_transfer(0x40, 0x52, 0x00, 0x02 if enable else 0x00, b"", timeout=1000)
        logger.info("QT config control request (%s) sent, rc=%s", "enable" if enable else "disable", rc)
    except usb.core.USBError as exc:
        logger.warning("QT config control request (%s) errored (often harmless): %s", "enable" if enable else "disable", exc)


def _wait_for_device(backend, serial: str, want_activated: bool, retries: int, log=None,
                     resend_every: int = 0) -> Optional[IosUsbDevice]:
    """Poll until the device appears in the expected state. With ``resend_every`` > 0 the activate/close request is resent every N polls."""
    for i in range(retries):
        time.sleep(0.5)
        if log and i and i % 20 == 0:
            log(f"[usb] still waiting for the device to {'enter' if want_activated else 'leave'} the hidden configuration ... {i // 2}s (this can take over a minute)")
        if resend_every and i and i % resend_every == 0:
            try:
                for d in find_devices(backend, serial):
                    if d.activated != want_activated:
                        logger.info("resending QT config %s request", "enable" if want_activated else "disable")
                        send_qt_config_request(d.dev, want_activated)
                        usb.util.dispose_resources(d.dev)
            except Exception as exc:  # noqa: BLE001
                logger.debug("resend failed: %s", exc)
        try:
            candidates = find_devices(backend, serial)
        except Exception as exc:  # noqa: BLE001  the device may vanish briefly during re-enumeration
            logger.debug("enumerate failed while waiting: %s", exc)
            candidates = []
        for d in candidates:
            if d.activated == want_activated:
                return d
        logger.debug("waiting for QT config %s (%d/%d)", "on" if want_activated else "off", i + 1, retries)
    return None


def activate(device: IosUsbDevice, backend=None, retries: int = 40, log=None) -> IosUsbDevice:
    """Activate the hidden configuration and guarantee a **fresh session**.

    The device starts a QuickTime session (sends PING) only right after activation; if configuration 5 already exists
    (left over from last time) the device stays silent. So when it is already active, send the close request first to re-enumerate, then activate again.
    """
    backend = backend or get_backend()
    if device.activated:
        logger.info("device %s already has QT config %d (stale session); resetting first", device.serial, device.qt_config)
        try:
            device = reset_device(device, backend, retries=30, log=log)   # 15s
        except RuntimeError as exc:
            raise StaleConfigError(str(exc)) from exc
    try:
        device.original_config = device.dev.get_active_configuration().bConfigurationValue
    except Exception:  # noqa: BLE001
        device.original_config = device.mux_config
    send_qt_config_request(device.dev, True)
    try:
        usb.util.dispose_resources(device.dev)
    except Exception:  # noqa: BLE001
        pass
    d = _wait_for_device(backend, device.serial, want_activated=True, retries=retries, log=log, resend_every=20)
    if d is None:
        raise RuntimeError(
            f"could not activate QuickTime config for {device.serial} (hidden configuration did not appear within {retries * 0.5:.0f}s). "
            "iOS refuses screen capture while locked: unlock the phone, keep the screen on and retry (temporarily set Auto-Lock to Never if needed)"
        )
    d.original_config = device.original_config
    logger.info("QT config %d activated for %s (was config %d)", d.qt_config, d.serial, d.original_config)
    return d


def reset_device(device: IosUsbDevice, backend=None, retries: int = 20, log=None, hard: bool = False) -> IosUsbDevice:
    """Make the device leave the hidden configuration and re-enumerate with its normal configuration.

    By default only the close control request is sent (safe). With ``hard=True`` a USB port reset follows (equivalent to replugging);
    after a reset the device needs noticeably longer before it can be activated again, so callers should wait longer.
    """
    backend = backend or get_backend()
    send_qt_config_request(device.dev, False)
    if hard:
        try:
            device.dev.reset()
            logger.warning("usb port reset issued for %s", device.serial)
        except Exception as exc:  # noqa: BLE001
            logger.warning("usb reset failed: %s", exc)
    try:
        usb.util.dispose_resources(device.dev)
    except Exception:  # noqa: BLE001
        pass
    fresh = _wait_for_device(backend, device.serial, want_activated=False, retries=retries, log=log)
    if fresh is None:
        raise RuntimeError(f"device {device.serial} did not reappear with its normal configuration after closing the hidden one")
    time.sleep(1.0)  # let the system driver finish loading
    return fresh


def wait_for_replug(backend=None, udid: Optional[str] = None, timeout: float = 120.0, log=print) -> IosUsbDevice:
    """Diagnostics: ask the user to replug the cable and return the newly enumerated (inactive) device as soon as it appears."""
    backend = backend or get_backend()
    present = bool(find_devices(backend, udid))
    log("[replug] please unplug the iPhone cable ..." if present else "[replug] no device detected, please plug in the cable ...")
    deadline = time.time() + timeout
    if present:
        while time.time() < deadline and find_devices(backend, udid):
            time.sleep(0.3)
        log("[replug] unplugged, please plug it back in ...")
    while time.time() < deadline:
        devices = find_devices(backend, udid)
        if devices:
            d = devices[0]
            log(f"[replug] detected {d.serial} ({'active' if d.activated else 'inactive'}); activating now")
            time.sleep(0.5)
            return d
        time.sleep(0.2)
    raise RuntimeError("timed out waiting for the device to be replugged")


def deactivate(device: IosUsbDevice) -> None:
    """Send the close-hidden-configuration request. Only non-Windows platforms switch back to the original configuration (switching under the Windows filter driver risks a bluescreen)."""
    send_qt_config_request(device.dev, False)
    if sys.platform == "win32":
        return
    target = device.original_config if device.original_config > 0 else (device.mux_config if device.mux_config != -1 else 1)
    try:
        device.dev.set_configuration(target)
    except Exception as exc:  # noqa: BLE001
        logger.debug("reset config failed: %s", exc)


class QuickTimeTransport:
    """Bulk transfers after claiming interface 0x2A; ``start_reading`` loops in a thread and hands raw chunks to the callback."""

    def __init__(self, device: IosUsbDevice, *, read_size: int = 64 * 1024, timeout_ms: int = 1000,
                 deactivate_on_close: bool = True) -> None:
        # deactivate_on_close: on close, send the "close QT configuration" control request so the device re-enumerates to its normal configuration by itself.
        # Only the control request is sent; set_configuration is never called (it caused bluescreens under the Windows filter driver).
        # Closing is mandatory: otherwise the device will not start a new session on the next connection.
        if not device.activated:
            raise RuntimeError("device not activated for screen mirroring")
        self.device = device
        self.dev = device.dev
        self.read_size = read_size
        self.timeout_ms = timeout_ms
        self.deactivate_on_close = deactivate_on_close
        self._intf = None
        self._ep_in = None
        self._ep_out = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.bytes_in = 0

    def open(self) -> None:
        dev = self.dev
        # SET_CONFIGURATION must be issued explicitly through libusb: the libusb0 filter driver only recognizes configurations it set itself,
        # otherwise claim fails with "invalid configuration 0" (even if the device is already in that configuration)
        logger.info("set configuration %d", self.device.qt_config)
        try:
            dev.set_configuration(self.device.qt_config)
        except usb.core.USBError as exc:
            logger.warning("set_configuration(%d) failed: %s (continuing with claim)", self.device.qt_config, exc)
        try:
            cfg = dev.get_active_configuration()
        except usb.core.USBError:
            cfg = None
        if cfg is None or cfg.bConfigurationValue != self.device.qt_config:
            cfg = next(c for c in dev if c.bConfigurationValue == self.device.qt_config)
        intf = _find_interface_for_subclass(cfg, SUBCLASS_QUICKTIME)
        if intf is None:
            raise RuntimeError("QuickTime interface (subclass 0x2A) not found in active config")
        if sys.platform != "win32":
            try:
                if dev.is_kernel_driver_active(intf.bInterfaceNumber):
                    dev.detach_kernel_driver(intf.bInterfaceNumber)
            except Exception as exc:  # noqa: BLE001
                logger.debug("detach kernel driver: %s", exc)
        try:
            usb.util.claim_interface(dev, intf.bInterfaceNumber)
        except usb.core.USBError as exc:
            if "invalid configuration" in str(exc):
                logger.warning("claim failed (%s); forcing set_configuration and retrying", exc)
                dev.set_configuration(self.device.qt_config)
                usb.util.claim_interface(dev, intf.bInterfaceNumber)
            else:
                raise
        self._intf = intf
        self._ep_in = usb.util.find_descriptor(
            intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            and usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK)
        self._ep_out = usb.util.find_descriptor(
            intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            and usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK)
        if self._ep_in is None or self._ep_out is None:
            raise RuntimeError("bulk endpoints not found on QuickTime interface")
        # CLEAR_FEATURE(ENDPOINT_HALT) on both endpoints, matching qvh
        for ep in (self._ep_in, self._ep_out):
            try:
                dev.ctrl_transfer(0x02, 0x01, 0, ep.bEndpointAddress, b"", timeout=1000)
            except usb.core.USBError as exc:
                logger.debug("clear feature 0x%02x: %s", ep.bEndpointAddress, exc)
        logger.info("QuickTime interface %d claimed: IN=0x%02x OUT=0x%02x",
                    intf.bInterfaceNumber, self._ep_in.bEndpointAddress, self._ep_out.bEndpointAddress)

    def write(self, data: bytes) -> None:
        for attempt in range(2):
            try:
                self._ep_out.write(data, timeout=self.timeout_ms)
                return
            except usb.core.USBError as exc:
                if _is_timeout(exc) and attempt == 0:
                    logger.warning("usb write timeout, retrying once")
                    continue
                logger.error("usb write failed: %s", exc)
                return

    def read_once(self) -> bytes:
        """Read one chunk; a timeout returns empty bytes (the device having no data is normal, not an error)."""
        try:
            return bytes(self._ep_in.read(self.read_size, timeout=self.timeout_ms))
        except usb.core.USBTimeoutError:
            return b""
        except usb.core.USBError as exc:
            if _is_timeout(exc):
                return b""
            raise

    def start_reading(self, on_chunk: Callable[[bytes], None], on_error: Callable[[Exception], None]) -> None:
        def run() -> None:
            while not self._stop.is_set():
                try:
                    chunk = self.read_once()
                except Exception as exc:  # noqa: BLE001
                    if not self._stop.is_set():
                        on_error(exc)
                    return
                if chunk:
                    self.bytes_in += len(chunk)
                    on_chunk(chunk)

        self._thread = threading.Thread(target=run, name="qt-usb-reader", daemon=True)
        self._thread.start()

    def close(self) -> None:
        """Conservative teardown order: let the reader thread exit completely first (no in-flight IN transfers), then release the interface, then the handle."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.timeout_ms / 1000 + 2)
            if self._thread.is_alive():
                logger.warning("usb reader thread did not exit; skipping interface release to stay safe")
                return
        time.sleep(0.2)
        if self._intf is not None:
            try:
                usb.util.release_interface(self.dev, self._intf.bInterfaceNumber)
                logger.info("QuickTime interface released")
            except Exception as exc:  # noqa: BLE001
                logger.debug("release interface: %s", exc)
            self._intf = None
        if self.deactivate_on_close:
            deactivate(self.device)
        try:
            usb.util.dispose_resources(self.dev)
        except Exception:  # noqa: BLE001
            pass
