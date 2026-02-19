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
```
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
```
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129
uv pip install vllm --torch-backend=auto
```

## Detail of Algorithm
AIEngineCore.py is a main processing program of an interview. 
[Flow Chart](AIEngineCoreFlowChart.md)


