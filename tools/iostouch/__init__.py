"""iostouch -- inject precise touches into an iPhone directly over a USB tunnel.

How it works: the iOS 18 developer disk image (DDI) ships the ``dtuhidd`` daemon, which exposes
``com.apple.coredevice.hid.universalhidservice`` over RemoteXPC. Sending 58-byte HID reports to its
mainTouchscreen surface (``_ServiceID=257``) yields ``UIEventTypeTouches`` identical to a real finger.

Prerequisites: the device trusts this computer and Developer Mode is on; the host needs no administrator
rights (userspace tunnel), no jailbreak, and no app installed on the phone.
"""

__all__ = []
