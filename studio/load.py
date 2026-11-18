"""How busy the server really is, measured every second: processor, memory and disk.

Nothing here counts people. New heavy work (another video, another recording) starts only while the machine has
room, waits in line for a moment when it is nearly full, and is let through the second it frees up again. That is
what keeps a rush from slowing everyone down or crashing the server."""
import os
import shutil
import threading
import time

from . import config

BUSY_CPU = float(config.env("CUTCUT_BUSY_CPU", "82"))          # percent: above this, no extra videos are started
MIN_FREE_RAM_GB = float(config.env("CUTCUT_MIN_FREE_RAM_GB", "1.5"))
MIN_FREE_DISK_GB = float(config.env("CUTCUT_MIN_FREE_DISK_GB", "3"))

_state = {"cpu": 0.0, "ram_free": 99.0, "disk_free": 99.0, "at": 0.0}
_measurement_errors = {"cpu": None, "ram": None, "disk": None}
_cpu_supported = os.name == "nt" or os.path.isfile("/proc/stat")
_force = None            # tests only: pretend the server is busy (True) or free (False)
_started = False
_lock = threading.Lock()


def _cpu_times():
    """(busy, total) processor time so far, in any unit."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        idle, kernel, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        get_times = ctypes.WinDLL("kernel32", use_last_error=True).GetSystemTimes
        get_times.argtypes = (ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
                              ctypes.POINTER(wintypes.FILETIME))
        get_times.restype = wintypes.BOOL
        ctypes.set_last_error(0)
        if not get_times(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            code = ctypes.get_last_error()
            if code:
                raise ctypes.WinError(code)
            raise OSError("GetSystemTimes returned FALSE without a Windows error code.")
        n = lambda f: (f.dwHighDateTime << 32) | f.dwLowDateTime          # noqa: E731
        total = n(kernel) + n(user)                                        # kernel time includes idle time
        return total - n(idle), total
    with open("/proc/stat", encoding="ascii") as f:
        v = [int(x) for x in f.readline().split()[1:9]]
    if len(v) < 5:
        raise OSError("/proc/stat did not contain processor counters.")
    return sum(v) - v[3] - v[4], sum(v)                                    # everything except idle and waiting on disk


def _ram_free_gb() -> float:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class M(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                (n, ctypes.c_ulonglong) for n in ("total", "avail", "tpf", "apf", "tv", "av", "aev")]
        m = M()
        m.dwLength = ctypes.sizeof(M)
        get_status = ctypes.WinDLL("kernel32", use_last_error=True).GlobalMemoryStatusEx
        get_status.argtypes = (ctypes.POINTER(M),)
        get_status.restype = wintypes.BOOL
        ctypes.set_last_error(0)
        if not get_status(ctypes.byref(m)):
            code = ctypes.get_last_error()
            if code:
                raise ctypes.WinError(code)
            raise OSError("GlobalMemoryStatusEx returned FALSE without a Windows error code.")
        if m.total <= 0 or m.avail > m.total:
            raise OSError("GlobalMemoryStatusEx returned invalid physical memory totals.")
        return m.avail / 1e9
    with open("/proc/meminfo", encoding="ascii") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1e6
    raise OSError("/proc/meminfo did not report MemAvailable.")


def _failed(metric: str, error: Exception, fallback: float):
    """Expose a failed reading and use a conservative value until the next sample succeeds."""
    _measurement_errors[metric] = f"{type(error).__name__}: {error}"
    key = {"cpu": "cpu", "ram": "ram_free", "disk": "disk_free"}[metric]
    _state[key] = fallback


def _watch():
    last = None
    if _cpu_supported:
        try:
            last = _cpu_times()
        except Exception as e:  # noqa: BLE001 - report failures and retry on the next tick
            _failed("cpu", e, 100.0)

    while True:
        time.sleep(1)
        if _cpu_supported:
            try:
                now = _cpu_times()
                if last is None:
                    # Establish a fresh baseline after a failed sample; do not reuse old counters.
                    _state["cpu"] = 0.0
                else:
                    used, total = now[0] - last[0], now[1] - last[1]
                    if total <= 0 or used < 0:
                        raise OSError("Processor counters did not advance monotonically.")
                    sample = max(0.0, min(100.0, 100.0 * used / total))
                    # Smooth brief spikes so one sample neither holds people up nor lets too much in.
                    _state["cpu"] = 0.55 * _state["cpu"] + 0.45 * sample
                last = now
                _measurement_errors["cpu"] = None
            except Exception as e:  # noqa: BLE001
                last = None
                _failed("cpu", e, 100.0)
        else:
            _measurement_errors["cpu"] = "Processor readings are not supported on this platform."
            _state["cpu"] = 0.0

        try:
            _state["ram_free"] = _ram_free_gb()
            _measurement_errors["ram"] = None
        except Exception as e:  # noqa: BLE001
            _failed("ram", e, 0.0)

        try:
            if time.time() - _state["at"] > 15:
                _state["disk_free"] = shutil.disk_usage(config.DATA_DIR).free / 1e9
                _state["at"] = time.time()
                _measurement_errors["disk"] = None
        except Exception as e:  # noqa: BLE001
            _failed("disk", e, 0.0)


def start():
    global _started
    with _lock:
        if not _started:
            _started = True
            threading.Thread(target=_watch, daemon=True, name="load").start()


def busy() -> bool:
    """True while the server is near capacity or a required reading has failed."""
    if _force is not None:
        return _force
    start()
    cpu_failed = _cpu_supported and _measurement_errors["cpu"] is not None
    return (cpu_failed or _measurement_errors["ram"] is not None
            or _state["cpu"] >= BUSY_CPU or _state["ram_free"] < MIN_FREE_RAM_GB)


def disk_full() -> bool:
    start()
    return _measurement_errors["disk"] is not None or _state["disk_free"] < MIN_FREE_DISK_GB


def state() -> dict:
    start()
    return {"cpu": round(_state["cpu"]), "ram_free_gb": round(_state["ram_free"], 1),
            "disk_free_gb": round(_state["disk_free"], 1), "busy": busy(), "busy_cpu": BUSY_CPU,
            "errors": {name: error for name, error in _measurement_errors.items() if error}}
