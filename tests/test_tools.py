"""The errors people hit on a fresh install: ffmpeg not found ("[WinError 2]"), the speech model not downloaded,
and an AI model name the service does not know. Runs against the code directly; nothing is downloaded."""
import io, os, shutil, sys, tarfile, tempfile
from pathlib import Path
os.environ["CUTCUT_DATA"] = tempfile.mkdtemp(prefix="pc-tools-"); os.environ["DATABASE_URL"] = ""
os.environ.pop("CUTCUT_MODELS", None)          # this test makes and removes a model: only ever inside its own folder
os.environ.update(CUTCUT_AI_PROVIDER="gemini", CUTCUT_AI_MODELS="gemini-old", CUTCUT_AI_KEY="test-key-123456")
sys.path.insert(0, ".")
from studio import ai, config, fetch_model, safe, tools
fails = []
def check(n, got, want=True):
    ok = want(got) if callable(want) else got == want
    print(("PASS " if ok else "FAIL ") + n + ("" if ok else f"   got {got!r}")); ok or fails.append(n)

# ---- ffmpeg
real_path = os.environ.get("PATH", "")
original_custom = os.environ.get("CUTCUT_FFMPEG_DIR")
exe = ".exe" if sys.platform == "win32" else ""
path_bin = Path(tempfile.mkdtemp(prefix="pc-ff-path-"))
custom_bin = Path(tempfile.mkdtemp(prefix="pc-ff-custom-"))
missing_bin = Path(tempfile.mkdtemp(prefix="pc-ff-missing-"))
for directory in (path_bin, custom_bin):
    for name in tools.NEEDED:
        f = directory / (name + exe); f.write_bytes(b"x"); f.chmod(0o755)
(missing_bin / ("ffmpeg" + exe)).write_bytes(b"x")
(missing_bin / ("ffmpeg" + exe)).chmod(0o755)

# PATH takes precedence when it contains both executables.
os.environ["PATH"] = str(path_bin)
os.environ["CUTCUT_FFMPEG_DIR"] = str(custom_bin)
check("both executables are detected from PATH before the custom directory", tools.setup(), [])
check("PATH detection does not need a custom PATH injection", os.environ["PATH"], str(path_bin))

# A configured custom folder is added to this process PATH and must contain both tools.
os.environ["PATH"] = ""
os.environ["CUTCUT_FFMPEG_DIR"] = str(custom_bin)
check("both executables are detected from CUTCUT_FFMPEG_DIR", tools.setup(), [])
check("custom FFmpeg directory is added to this process PATH", str(custom_bin) in os.environ["PATH"].split(os.pathsep), True)
check("custom executables become discoverable to child processes", (bool(shutil.which("ffmpeg")), bool(shutil.which("ffprobe"))), (True, True))

# Missing either executable is reported explicitly and gives setup guidance.
os.environ["PATH"] = ""
os.environ["CUTCUT_FFMPEG_DIR"] = str(missing_bin)
check("missing ffprobe is reported when custom folder only has ffmpeg", tools.setup(), ["ffprobe"])
err = FileNotFoundError(2, "The system cannot find the file specified")
check("bare Windows executable errors explain FFmpeg installation and configuration", ("ffmpeg" in safe.friendly(err).lower(), "install" in safe.friendly(err).lower(), "CUTCUT_FFMPEG_DIR" in safe.friendly(err)), (True, True, True))
check("an unrelated error is left as it is", safe.friendly(ValueError("That link is a playlist.")), "That link is a playlist.")

# Restore process configuration before other tests.
os.environ["PATH"] = real_path
if original_custom is None:
    os.environ.pop("CUTCUT_FFMPEG_DIR", None)
else:
    os.environ["CUTCUT_FFMPEG_DIR"] = original_custom
tools.setup()
for directory in (path_bin, custom_bin, missing_bin):
    shutil.rmtree(directory, ignore_errors=True)

# ---- the speech model
d = config.ASR_MODEL_DIR
assert str(d).startswith(os.environ["CUTCUT_DATA"]), "the test must only touch its own folder"
check("no model to begin with", fetch_model.ready(), False)
d.mkdir(parents=True); (d / "tokens.txt").write_text("a 1")
check("half a model (a download that was cut off) does not count", fetch_model.ready(), False)
def fake_download(url, dest, hook=None):
    buf = tempfile.mkdtemp(prefix="pc-tar-")
    src = Path(buf) / config.ASR_MODEL_NAME; src.mkdir()
    for n in ("tokens.txt", "encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx"):
        (src / n).write_bytes(b"model")
    with tarfile.open(dest, "w:bz2") as t:
        t.add(src, arcname=config.ASR_MODEL_NAME)
    if hook: hook(1, 100, 100)
fetch_model.urllib.request.urlretrieve = fake_download
fetch_model.ensure()
check("the model is downloaded by itself and put in place whole", (fetch_model.ready(), sorted(p.name for p in d.iterdir())),
      (True, ["decoder.int8.onnx", "encoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"]))
check("nothing is left over from the download", sorted(p.name for p in config.MODELS_DIR.iterdir()), [config.ASR_MODEL_NAME])
shutil.rmtree(d)
def no_internet(url, dest, hook=None):
    raise OSError("getaddrinfo failed")
fetch_model.urllib.request.urlretrieve = no_internet
try:
    fetch_model.ensure(); said = ""
except RuntimeError as e:
    said = str(e)
check("no internet: said in plain words, and no half model left behind", ("internet" in said, fetch_model.ready(), d.exists()), (True, False, False))

# ---- the AI
check("an unknown model name", ai.explain("HTTP 404 models/gemini-old is not found for API version v1beta"), lambda s: "gemini-old" in s and "Find models" in s)
check("a refused key", ai.explain("HTTP 400 API key not valid. Please pass a valid API key."), lambda s: "refused the key" in s)
check("out of quota", ai.explain("HTTP 429 You exceeded your current quota"), lambda s: "limit" in s)
check("cannot be reached", ai.explain("[Errno 11001] getaddrinfo failed"), lambda s: "couldn't reach" in s)
check("anything else is not guessed at", ai.explain("something odd"), "")
ai.note_problem("HTTP 404 model not found")
check("the reason is kept for the dashboard, and cleared when the AI answers again", (bool(ai.problem["text"]), (ai.clear_problem(), ai.problem["text"])[1]), (True, ""))

print("ALL PASSED" if not fails else f"{len(fails)} failed")
shutil.rmtree(os.environ["CUTCUT_DATA"], ignore_errors=True); shutil.rmtree(hidden, ignore_errors=True)
sys.exit(1 if fails else 0)
