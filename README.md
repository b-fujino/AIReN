# AIReN

AI for Reporting a Nearmiss and incident with HTML interface.

## Preparation

### uv

install uv if before installing uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### viertual envrionment

crate virtual environment

```bash
uv venv
```

in this case, folder name is set defalt name (.venv)

Activate .venv

```bash
# Linux
source .venv/bin/activate

#Windows
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process # if need
.venv\Scripts\activate.ps1
```

### Required packages install

install package

```bash
uv pip install -r requirements.txt
```

or minimally:

```bash
uv pip install ollama openai pydantic python-dotenv requests flask flask_cors flask_socketio SpeechRecognition pydub pyngrok gradio_client soundfile faster-whisper
```

### Run the web app

```bash
python AIReN.py
```

The app is published through ngrok (set `NGROK_AUTH_TOKEN` and `FLASK_SECRET_KEY` in `.env`).
Debug mode (Werkzeug debugger) is off by default because the app is exposed publicly; set `FLASK_DEBUG=1` only for local debugging.

#### Online / offline mode

Set `AIREN_MODE` in `.env` (or the environment):

| | `AIREN_MODE=online` (default) | `AIREN_MODE=offline` |
|---|---|---|
| Speech recognition | Google Speech Recognition | local [faster-whisper](https://github.com/SYSTRAN/faster-whisper) |
| Publishing | ngrok tunnel | local only: http://127.0.0.1:5000 |

LLM (Ollama), TTS (VOICEVOX) and the browser libraries (`static/vendor/`: Recorder.js, socket.io-client 4.0.0, marked 15.0.12) are local in both modes.

Optional overrides: `ASR_ENGINE=google|whisper`, `USE_NGROK=1|0`,
`WHISPER_MODEL` (default `large-v3-turbo`, or a local model directory), `WHISPER_DEVICE` (`auto`/`cuda`/`cpu`), `WHISPER_COMPUTE_TYPE`.

In offline mode the Whisper model is not downloaded, so fetch it once while online:

```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3-turbo')"
```

Note: the browser only allows microphone access on `https://` or `localhost`, so in offline mode open the app on the same machine (`http://localhost:5000`).

**note**: ollama itself is necessary to be installed according to [ollama](https://ollama.com/download/linux).

if use vllm, install required packages as follwoing:

```bash
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129
uv pip install vllm --torch-backend=auto
```

## Detail of Algorithm

AIEngineCore.py is a main processing program of an interview.
[Flow Chart](AIEngineCoreFlowChart.md)

# Memo
## 2026-6-7

In call_openai_api_ollama py, "num_ctx" was revised from 16k to 32k.

In AIEnginceCore.py, "nu_predict" in Interviewer's chat response, Reporter's chat response, and Summrizer's caht response was set with  appropriate numbers.

Each agnet's system prompt was destributed into each python file from systemprompt_Agents_v2.py.

Supervisor's and Similarity Checker's system prompts were provided with instructions of output scheme and one shot examples.

In systemprompot_IncidentReportGudie_Pydantic.py, name of each model was changed from Japanese one to English.

