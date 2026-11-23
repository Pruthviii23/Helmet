"""Read several serial ports at once for a fixed time and print tagged lines.

Usage: python serial_watch.py SECONDS COM7 COM8 [...]
"""
import sys
import threading
import time

import serial


def watch(port, seconds, lock):
    try:
        s = serial.Serial(port, 115200, timeout=0.5)
    except Exception as e:  # port busy or missing
        with lock:
            print(f"[{port}] OPEN FAILED: {e}", flush=True)
        return
    # Opening the C3's USB port can reset it; toggling DTR/RTS low keeps it running.
    s.dtr = False
    s.rts = False
    end = time.time() + seconds
    buf = b""
    while time.time() < end:
        buf += s.read(256)
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            text = line.decode("utf-8", "replace").rstrip()
            if text:
                with lock:
                    print(f"[{port}] {text}", flush=True)
    s.close()


def main():
    seconds = float(sys.argv[1])
    ports = sys.argv[2:]
    lock = threading.Lock()
    threads = [threading.Thread(target=watch, args=(p, seconds, lock)) for p in ports]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
