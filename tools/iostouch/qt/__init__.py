"""Python implementation of the private Apple USB screen capture protocol (QuickTime Screen Capture).

Modules:
* coremedia -- CoreMedia serialization: NSNumber, dictionaries, CMTime, CMClock, FormatDescription, CMSampleBuffer
* packets   -- parsing and building PING / SYNC / ASYN / RPLY packets
* session   -- session state machine (handshake, clocks, back-pressure, stop) and frame reassembly across USB reads
* usb       -- pyusb device discovery, hidden-configuration activation, claiming interface 0x2A, transfers
* h264      -- AVCC -> Annex-B, SPS/PPS extraction, PyAV decoding

Protocol blueprint: quicktime_video_hack (MIT).
"""
