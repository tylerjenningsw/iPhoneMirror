"""MuxBridge: on a device with the hidden configuration active, replace Apple Mobile Device Service with our own usbmux channel.

After start-up it sets ``USBMUXD_SOCKET_ADDRESS`` so every pymobiledevice3 usbmux access in this process goes through here,
letting the touch tunnel and QuickTime video share one USB configuration.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from iostouch.qt.usbmux_usb import MuxError, UsbMuxTransport
from iostouch.qt.usbmuxd_server import UsbmuxdThread

logger = logging.getLogger(__name__)
ENV = "USBMUXD_SOCKET_ADDRESS"
ADDR_FILE_NAME = "iostouch_usbmux.addr"


def addr_file() -> Path:
    return Path(tempfile.gettempdir()) / ADDR_FILE_NAME


def read_saved_address() -> Optional[str]:
    """Read the address written by the previous MuxBridge (for ``--usbmux auto``)."""
    try:
        return addr_file().read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def free_port_windows(port: int) -> None:
    """Windows: if the port is held by a leftover python process from this project, terminate it."""
    import subprocess
    import sys

    if sys.platform != "win32" or port <= 0:
        return
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=10).stdout
    except Exception as exc:  # noqa: BLE001
        logger.debug("netstat failed: %s", exc)
        return
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3].upper() == "LISTENING":
            pids.add(parts[4])
    for pid in pids:
        try:
            info = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10).stdout
        except Exception:  # noqa: BLE001
            info = ""
        if "python" in info.lower():
            logger.warning("port %d is held by leftover python process %s; terminating it", port, pid)
            subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=10)
        else:
            logger.warning("port %d is held by PID %s (not python); leaving it alone: %s", port, pid, info.strip()[:80])


class MuxBridge:
    def __init__(self, dev, serial: str, *, port: int = 0) -> None:
        self.dev = dev
        self.serial = serial
        self.port = port
        self.transport: Optional[UsbMuxTransport] = None
        self.server: Optional[UsbmuxdThread] = None
        self.address: Optional[str] = None
        self._prev_env: Optional[str] = None

    def start(self) -> str:
        free_port_windows(self.port)
        self.transport = UsbMuxTransport(self.dev, self.serial)
        try:
            self.transport.start()
        except MuxError:
            self.transport.close()
            self.transport = None
            raise
        self.server = UsbmuxdThread(self.transport.mux, self.serial, port=self.port)
        self.address = self.server.start()
        self._prev_env = os.environ.get(ENV)
        os.environ[ENV] = self.address
        try:
            addr_file().write_text(self.address, encoding="utf-8")
        except OSError as exc:
            logger.debug("write addr file: %s", exc)
        logger.info("MuxBridge up: %s=%s (device mux v%d)", ENV, self.address, self.transport.mux.version)
        return self.address

    def stop(self) -> None:
        try:
            if addr_file().exists() and addr_file().read_text(encoding="utf-8").strip() == self.address:
                addr_file().unlink()
        except OSError:
            pass
        if self._prev_env is None:
            os.environ.pop(ENV, None)
        else:
            os.environ[ENV] = self._prev_env
        if self.server is not None:
            try:
                self.server.stop()
            except Exception as exc:  # noqa: BLE001
                logger.debug("usbmuxd server stop: %s", exc)
            self.server = None
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception as exc:  # noqa: BLE001
                logger.debug("usbmux transport close: %s", exc)
            self.transport = None
