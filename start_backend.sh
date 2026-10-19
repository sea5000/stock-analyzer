#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================================="
echo " Starting AI Stock & Portfolio Assistant - Backend"
echo "=========================================================="

if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment in .venv..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Ensuring backend dependencies are installed..."
pip install -q -r backend/requirements.txt

if [ ! -f "backend/.env" ]; then
    echo "Copying backend/.env.example to backend/.env..."
    cp backend/.env.example backend/.env
fi

echo "Verifying AI provider configuration..."
python3 -c "
import os, urllib.request, json
from pathlib import Path
from dotenv import load_dotenv

env_path = Path('backend/.env')
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

provider = os.getenv('LLM_PROVIDER', 'ollama').lower()
model = os.getenv('MODEL_NAME', 'unknown')

if provider == 'thesys':
    key = os.getenv('OPENAI_API_KEY', '')
    masked_key = key[:10] + '...' if len(key) > 10 else 'NOT_SET'
    print(f'  [Provider] Active: THESYS C1 Cloud')
    print(f'  [Model]    {model}')
    print(f'  [API Key]  {masked_key}')
else:
    print(f'  [Provider] Active: Local OLLAMA (Model: {model})')
    try:
        with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2) as response:
            data = json.loads(response.read().decode())
            models = [m.get('name') for m in data.get('models', [])]
            print('  [Ollama Status] ONLINE! Available models:', ', '.join(models) if models else 'None')
    except Exception:
        print('  [Ollama Status] WARNING: Ollama not detected at http://localhost:11434.')
        print('  Please ensure Ollama is running if switching back to local AI.')
"

echo "Launching FastAPI server on http://localhost:8888..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8888 --reload
