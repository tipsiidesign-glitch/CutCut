"""The line under load: holds while the server is near full, moves the moment it is not. Usage: test_load_queue.py <root>"""
import os
import sys
import tempfile
import threading
import time

# The Windows multiprocessing child imports this file as __mp_main__. Reuse the
# parent's isolated data folder instead of creating another temp directory there.
if __name__ == "__main__":
    os.environ["CUTCUT_DATA"] = tempfile.mkdtemp(prefix="pc-queue-")
sys.path.insert(0, sys.argv[1])
from studio import config, jobs, load  # noqa: E402

load.MIN_FREE_RAM_GB = 0.0  # this checks the processor; memory is asserted separately below
config.JOB_WORKERS = 8      # the queue test is about order, not the machine's worker setting

fails = []


def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"   {extra}" if extra else ""), flush=True)
    if not ok:
        fails.append(name)


def measurement(name, value, error):
    return f"{name}={value}; error={error or 'none'}"


def check_monitor_readings():
    # Keep monitor work inside the parent process. Windows multiprocessing imports
    # the test module in each child, but must not repeat these assertions there.
    load.start()
    time.sleep(2.5)
    idle = load.state()
    if load._cpu_supported:
        check("monitor reads the processor", "cpu" not in idle["errors"] and 0 <= idle["cpu"] <= 100,
              measurement("cpu_percent", idle["cpu"], idle["errors"].get("cpu")))
    else:
        check("unsupported processor readings are reported", bool(idle["errors"].get("cpu")),
              measurement("cpu_percent", idle["cpu"], idle["errors"].get("cpu")))
    check("monitor reads free memory", "ram" not in idle["errors"] and idle["ram_free_gb"] > 0.1,
          measurement("ram_free_gb", idle["ram_free_gb"], idle["errors"].get("ram")))
    check("monitor reads free disk", "disk" not in idle["errors"] and idle["disk_free_gb"] > 0.1,
          measurement("disk_free_gb", idle["disk_free_gb"], idle["errors"].get("disk")))
    return idle


def check_windows_api_failures():
    if os.name != "nt":
        print("SKIP Windows API failure probes: this is not Windows.", flush=True)
        return
    import ctypes
    from unittest.mock import patch

    class FailedCall:
        def __call__(self, *args):
            return 0

    class FakeKernel:
        GetSystemTimes = FailedCall()
        GlobalMemoryStatusEx = FailedCall()

    with patch.object(ctypes, "WinDLL", return_value=FakeKernel()), patch.object(ctypes, "get_last_error", return_value=0):
        try:
            load._cpu_times()
            cpu_error = "no error"
        except OSError as e:
            cpu_error = str(e)
        try:
            load._ram_free_gb()
            ram_error = "no error"
        except OSError as e:
            ram_error = str(e)
    check("GetSystemTimes FALSE is reported", "GetSystemTimes returned FALSE" in cpu_error, cpu_error)
    check("GlobalMemoryStatusEx FALSE is reported", "GlobalMemoryStatusEx returned FALSE" in ram_error, ram_error)


def burn(until):
    while time.time() < until:
        sum(i * i for i in range(20000))


import multiprocessing  # noqa: E402

if __name__ == "__main__":
    idle = check_monitor_readings()
    check_windows_api_failures()
    if load._cpu_supported:
        # A small fixed pool keeps this test bounded even on workstations with
        # dozens or hundreds of logical processors.
        worker_count = max(1, min(os.cpu_count() or 2, 4))
        stop = time.time() + 10
        ps = [multiprocessing.Process(target=burn, args=(stop,)) for _ in range(worker_count)]
        [p.start() for p in ps]
        time.sleep(5)
        hot = load.state()
        rose = hot["cpu"] > idle["cpu"] and "cpu" not in hot["errors"]
        check("processor reading rises during bounded work", rose,
              f"idle={idle['cpu']}%; loaded={hot['cpu']}%; workers={worker_count}; error={hot['errors'].get('cpu') or 'none'}")
        if rose:
            load.BUSY_CPU = (idle["cpu"] + hot["cpu"]) / 2
        else:
            # Keep the failure diagnostic useful and do not mistake background
            # load or a stale reading for a successful threshold transition.
            load.BUSY_CPU = 101.0
        check("load monitor holds new work above the observed threshold", rose and load.busy(),
              f"cpu={hot['cpu']}%; threshold={load.BUSY_CPU}%; errors={hot['errors']}")
        [p.join() for p in ps]
        t0 = time.time()
        while load.busy() and time.time() - t0 < 15:
            time.sleep(0.2)
        check("monitor releases work after processor load ends", not load.busy(),
              f"{time.time() - t0:.1f}s after work stopped: {load.state()}")
    else:
        print("SKIP CPU load transition: processor sampling is unsupported on this platform.", flush=True)

    # ---- the line: four people, one video each; pretend the server is full, then free
    q = jobs._FairQueue()
    started, release = [], threading.Event()

    def worker():
        while True:
            item = q.get()
            started.append((item[1], time.time()))
            release.wait()
            q.done()

    load._force = True
    for u in "abcd":
        q.put(("job", "job-" + u, None), user=u)
    for _ in range(4):
        threading.Thread(target=worker, daemon=True).start()
    time.sleep(8)
    check("server full: one video runs, the rest wait", len(started) == 1 and q.held, f"started {len(started)}")
    check("waiting people are told their place", q.ahead() == {"job-b": 0, "job-c": 1, "job-d": 2}, str(q.ahead()))
    t_free = time.time()
    load._force = False
    time.sleep(2.2)
    check("server frees up: the next video starts at once", len(started) == 2,
          f"{started[1][1] - t_free:.1f}s after it freed up" if len(started) > 1 else f"started {len(started)}")
    time.sleep(14)
    check("the rest follow a few seconds apart, not all at once", len(started) == 4,
          f"gaps {[round(b[1] - a[1], 1) for a, b in zip(started, started[1:])]}" )
    release.set()
    time.sleep(1.5)
    check("line is empty and nothing is held", q.running == 0 and not q.turn)
    print("\n%d failed" % len(fails) if fails else "\nALL PASSED", flush=True)
    sys.exit(1 if fails else 0)
