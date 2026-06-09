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
uv pip install ollama dotenv requests flask flask_cors flask_socketio SpeechRecognition pydub
```

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

