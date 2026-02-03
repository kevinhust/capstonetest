#!/usr/bin/env bash
set -e

# Antigravity Workspace Template Installer for Linux/macOS
# This script sets up the development environment automatically

echo "🪐 Antigravity Workspace Template - Installer"
echo "=============================================="
echo ""

# Check for Python 3.12
if ! command -v python3.12 &> /dev/null; then
    echo "⚠️  Python 3.12 not found. Attempting to install via Homebrew..."
    if command -v brew &> /dev/null; then
        echo "📦 Installing Python 3.12..."
        brew install python@3.12
        
        # Verify installation
        if ! command -v python3.12 &> /dev/null; then
             echo "❌ Error: Python 3.12 installation failed."
             exit 1
        fi
        echo "✅ Python 3.12 installed"
    else
        echo "❌ Error: Homebrew is not installed. Please install Python 3.12 manually from https://www.python.org/downloads/"
        exit 1
    fi
else
    echo "✅ Python 3.12 detected"
fi

# Check if Git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Error: Git is not installed."
    echo "Please install Git from https://git-scm.com/downloads"
    exit 1
fi

echo "✅ Git $(git --version | cut -d' ' -f3) detected"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment 'capstoneenv'..."
if [ -d "capstoneenv" ]; then
    echo "⚠️  Virtual environment 'capstoneenv' already exists. Skipping creation."
else
    python3.12 -m venv capstoneenv
    echo "✅ Virtual environment 'capstoneenv' created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source capstoneenv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# Initialize configuration
echo "🔧 Setting up configuration..."

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Antigravity Workspace Configuration
# Copy this file and configure your API keys

# Google Gemini API Key (Required)
GOOGLE_API_KEY=your_api_key_here

# Optional: OpenAI API Key for alternative LLM
# OPENAI_API_KEY=your_openai_key_here

# Optional: Model Configuration
# MODEL_NAME=gemini-2.0-flash-exp
EOF
    echo "✅ Created .env file (please configure your API keys)"
else
    echo "⚠️  .env file already exists. Skipping creation."
fi

# Create artifacts directory if it doesn't exist
if [ ! -d "artifacts" ]; then
    mkdir -p artifacts
    echo "✅ Created artifacts directory"
fi

echo ""
echo "=============================================="
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Configure your API keys in .env file:"
echo "   nano .env"
echo ""
echo "2. Activate the virtual environment:"
echo "   source capstone/bin/activate"
echo ""
echo "3. Run the agent:"
echo "   python src/agent.py"
echo ""
echo "📚 Documentation: docs/framework/en/QUICK_START.md"
echo "=============================================="
