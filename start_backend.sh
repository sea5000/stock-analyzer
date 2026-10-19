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

echo "Checking Ollama connectivity..."
python3 -c "
import urllib.request, json
try:
    with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2) as response:
        data = json.loads(response.read().decode())
        models = [m.get('name') for m in data.get('models', [])]
        print('  [Ollama Status] ONLINE! Available models:', ', '.join(models) if models else 'None')
        if any('qwen' in m for m in models):
            print('  [Model Check] Qwen model detected!')
        else:
            print('  [Model Note] Tip: Ensure qwen3.8:27b is pulled (run: ollama pull qwen3.8:27b)')
except Exception as e:
    print('  [Ollama Status] WARNING: Ollama not detected at http://localhost:11434.')
    print('  Please start Ollama in another terminal (run: ollama serve)')
"

echo "Launching FastAPI server on http://localhost:8888..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8888 --reload
