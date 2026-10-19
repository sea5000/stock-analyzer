#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/frontend"

echo "=========================================================="
echo " Starting AI Stock & Portfolio Assistant - Frontend"
echo "=========================================================="

if [ ! -d "node_modules" ]; then
    echo "Installing frontend npm dependencies..."
    npm install
fi

echo "Launching Vite development server on http://localhost:3000..."
npm run dev
