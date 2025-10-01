#!/bin/bash

# Investment Portfolio Tracker - Setup Script
# This script initializes the project structure and dependencies

set -e  # Exit on error

echo "🚀 Setting up Investment Portfolio Tracker..."
echo ""

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "✅ UV installed successfully"
else
    echo "✅ UV is already installed"
fi

echo ""
echo "📁 Creating project structure..."

# Create directory structure
mkdir -p core data ui utils

# Create __init__.py files
touch core/__init__.py
touch data/__init__.py
touch ui/__init__.py
touch utils/__init__.py

echo "✅ Project structure created"
echo ""

# Create virtual environment and install dependencies
echo "📦 Installing dependencies with UV..."
uv venv
source .venv/bin/activate 2>/dev/null || . .venv/Scripts/activate 2>/dev/null

uv pip install -e .

echo "✅ Dependencies installed"
echo ""

echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source .venv/bin/activate"
echo "2. Set up Google Sheets API (see README.md)"
echo "3. Prepare your Google Sheet with transactions"
echo "4. Run the app: streamlit run app.py"
echo ""
echo "⚠️  IMPORTANT: Never commit your Google credentials JSON file!"
echo "    The .gitignore is configured to protect you, but always double-check."
echo ""