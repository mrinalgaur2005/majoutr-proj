#!/usr/bin/env python3
"""Prevent system sleep, suspend, and idle blanking while this process runs."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

INHIBIT_ENV = "KEEP_AWAKE_SYSTEMD_WRAPPED"
PULSE_SEC = 45
PORTAL_FLAGS = 12  # InhibitSuspend (4) | InhibitIdle (8)


def _reexec_under_systemd_inhibit() -> None:
    if os.environ.get(INHIBIT_ENV) == "1":
        return
    os.environ[INHIBIT_ENV] = "1"
    cmd = [
        "systemd-inhibit",
        "--what=idle:sleep:shutdown:handle-lid-switch:handle-power-key:handle-suspend-key",
        "--who=keep-awake",
        "--why=Prevent sleep when unattended",
        "--mode=block",
        sys.executable,
        *__file_paths(),
        *sys.argv[1:],
    ]
    os.execvp(cmd[0], cmd)


def __file_paths() -> list[str]:
    return [os.path.abspath(__file__)]


def _portal_idle_inhibit():
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    proxy = Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.NONE,
        None,
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.Inhibit",
        None,
    )
    variant = GLib.Variant("(sua{sv})", ("", PORTAL_FLAGS, {}))
    proxy.call_sync("Inhibit", variant, Gio.DBusCallFlags.NONE, -1, None)
    return proxy


def _pulse_screensaver() -> None:
    subprocess.run(
        ["xdg-screensaver", "reset"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def main() -> int:
    _reexec_under_systemd_inhibit()

    try:
        _portal_idle_inhibit()
    except Exception as exc:  # noqa: BLE001 — optional layer on non-GNOME desktops
        print(f"keep_awake: portal inhibit unavailable ({exc}); using systemd-inhibit only", file=sys.stderr)

    stop = False

    def on_signal(_signum, _frame) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    print("keep_awake: running — system and display should stay awake (Ctrl+C to stop)", flush=True)

    while not stop:
        _pulse_screensaver()
        for _ in range(PULSE_SEC):
            if stop:
                break
            time.sleep(1)

    print("keep_awake: stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())