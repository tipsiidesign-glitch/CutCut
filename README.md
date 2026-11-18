# CutCut

CutCut turns long videos and live streams into short, vertical clips. It runs as a local web app on your Windows PC, with local speech recognition and optional AI-assisted clip selection.

## What it does

- Import a local video or a video link from a supported source: YouTube, Twitch, or Kick.
- Record supported live creator channels and make clips from the stream.
- Transcribe speech locally with Sherpa-ONNX and the Parakeet model.
- Use an AI provider to help select moments and write clip hooks, titles, descriptions, and hashtags. Without a configured AI provider, video clip selection can fall back to loudness-based picks.
- Render vertical clips with captions, selectable layout and caption styles, and adjustable clip length and output quality.
- Optionally connect YouTube, Instagram, or TikTok accounts for manual posting or creator-configured automatic posting. Platform developer apps and account authorization are required.

CutCut uses FFmpeg for media processing. It does not bundle FFmpeg or the speech model; the model is downloaded on first launch when needed.

## AI providers

CutCut supports these providers in **Settings → AI**:

| Provider | Provider ID | Example model |
|---|---|---|
| Google Gemini | `gemini` | `gemini-2.5-flash` |
| OpenAI | `openai` | `gpt-4o-mini` |
| xAI / Grok | `xai` | `grok-4` |
| Groq | `groq` | `llama-3.3-70b-versatile` |
| OpenRouter | `openrouter` | `google/gemini-2.5-flash` |
| Anthropic / Claude | `anthropic` | Choose an available model in Settings |
| Custom OpenAI-compatible API | `custom` | Set the model and API base URL |

The default provider is Gemini and the default model is `gemini-2.5-flash`. Model availability and pricing are controlled by each provider.

### Configure Gemini

1. Start CutCut and open **Settings → AI**.
2. Select **Gemini**, enter the model `gemini-2.5-flash`, and add your Google AI Studio API key.
3. Save the settings and use the provider test in the AI settings page.

Alternatively, copy `.env.example` to `.env` and set the relevant values:

```dotenv
CUTCUT_AI_PROVIDER=gemini
CUTCUT_AI_MODELS=gemini-2.5-flash
CUTCUT_AI_KEY=your-gemini-api-key
```

The dashboard's saved provider settings take precedence over `.env`. `.env` and `data/ai.json` are local configuration and are excluded from Git; never commit real keys.

## Technology

- Python 3.11, FastAPI, and Uvicorn
- SQLAlchemy with SQLite for the local setup; PostgreSQL is supported for the documented Docker deployment
- Sherpa-ONNX and Parakeet for speech recognition
- FFmpeg for video and audio processing
- yt-dlp for supported online media sources
- NumPy, SoundFile, and Pillow
- HTML, CSS, and JavaScript frontend

## Windows installation

### Requirements

- 64-bit Windows 10 or Windows 11
- PowerShell and an internet connection for setup and model downloads
- FFmpeg with both `ffmpeg.exe` and `ffprobe.exe`
- Space for the application, speech model, source videos, and rendered clips

The checked-in setup and start scripts currently expect FFmpeg in:

```text
D:\ffmpeg-9.0.2-essentials_build\ffmpeg-9.0.2-essentials_build\bin
```

If your FFmpeg installation is elsewhere, update the `$env:CUTCUT_FFMPEG_DIR` / `$ff` path in `Setup-Instant.ps1` and `Start-Instant.ps1` before running setup. The scripts do not download or install FFmpeg.

### Install and start

1. Clone the repository and enter its folder:

   ```powershell
   git clone https://github.com/tipsiidesign-glitch/CutCut.git
   Set-Location CutCut
   ```

2. Run `Setup-Instant.bat`. It downloads the Python 3.11.9 embeddable runtime if needed, installs pip and the pinned packages in `requirements.txt`, and prepares local folders.
3. Run `Start-Instant.bat` and leave its PowerShell window open while CutCut is running.
4. Open [http://127.0.0.1:8765](http://127.0.0.1:8765) in your browser.
5. Configure an AI provider in **Settings → AI** if you want AI-assisted moment selection and clip text.

The Windows launcher stores application data under `data/` and binds to `127.0.0.1` by default. Press **Ctrl+C** in the running PowerShell window to stop the server. Do not expose this local setup to a public network: local sign-in is disabled by default.

For the Docker-based server deployment, see [DEPLOY.md](DEPLOY.md).

## Project layout

```text
studio/                 Application server, AI, transcription, media, jobs, and storage
web/                    Browser interface and brand assets
tests/                  Application test scripts
deploy/                 Docker, reverse-proxy, and optional ASR deployment files
Setup-Instant.*         Windows dependency and runtime setup
Start-Instant.*         Windows application launcher
Stop-Instant.*          Reminder to stop the server with Ctrl+C
requirements.txt        Pinned Python dependencies
.env.example            Documented environment-variable template
DEPLOY.md               Docker/server deployment guide
GAMING.md               Gaming-stream behavior and notes
```

Application data, credentials, downloaded models, runtime binaries, caches, and temporary files are local and are not part of the source tree sent to GitHub.

## Troubleshooting

**Setup says FFmpeg was not found.** Check that both `ffmpeg.exe` and `ffprobe.exe` exist in the path listed above, or update the FFmpeg path in both PowerShell scripts to match your installation.

**The browser cannot connect.** Keep the PowerShell window open and check that the server started at `http://127.0.0.1:8765`. If another program uses that port, configure `CUTCUT_PORT` before launching the server.

**Speech recognition is not ready on first launch.** The Parakeet model is downloaded when the app starts. Allow the download to finish and check that the data drive has free space and internet access.

**A YouTube link is refused.** YouTube may block automated requests from some networks. Try uploading a local video, or use a supported Twitch or Kick source.

**AI selection is unavailable.** Check the selected provider, model ID, and API key in **Settings → AI**. Provider requests require internet access. The local loudness-based video fallback remains available when AI is not configured.

## Attribution and license

CutCut is based on PeakCut and retains the upstream MIT license and copyright notice. See [LICENSE](LICENSE) for the complete license text.
