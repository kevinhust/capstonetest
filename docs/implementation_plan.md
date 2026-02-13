# Implementation Plan: Discord Bot Deployment to Google Cloud Run

**Date**: 2026-02-11
**Project Status**: MVP complete, Refactored Swarm logic verified locally.
**Objective**: Deploy the Personal Health Butler Discord Bot to Google Cloud Run while maintaining persistent Gateway connections and optimizing a large (3GB+) Docker image.

## 1. Project Background & Architecture

### A. Context
The **Personal Health Butler AI** is a modular swarm-based system designed to provide nutrition and fitness advice. Users primarily interact through **Discord**, where they can upload meal photos or ask health questions. 

### B. Core Architecture (The Swarm)
The system follows a "Swarm Orchestration" pattern:
- **HealthSwarm (Orchestrator)**: Manages message flow, state, and retries.
- **CoordinatorAgent**: Analyzes user intent and delegates to specialists.
- **NutritionAgent**: Uses **VisionTool (ViT)** for food detection and **RagTool (ChromaDB)** for nutrition lookup.
- **FitnessAgent**: Generates personalized exercise plans based on caloric intake.

### C. Technical Stack
- **Languages**: Python 3.12+
- **Frameworks**: `discord.py`, `Streamlit` (UI), `LangChain/Swarm` (Logic).
- **Libraries**: `torch`, `scipy`, `sklearn`, `chromadb` (contributing to ~3GB image size).
- **Primary Interface**: Discord Bot Gateway (Persistent Websockets).

## 2. Deployment Rationale: Cloud Run vs. Bot Nature

### A. The Conflict
Discord Bots require a persistent connection to the Discord Gateway. Traditional Cloud Run is request-driven and scales to zero, which kills persistent connections.

### B. The Solution: "Always-on CPU"
We will deploy to Cloud Run with **CPU Second Generation** and **Min-instances = 1** with **No CPU Throttling**.
- **CPU Always Allocated**: Ensures the event loop stays alive for the Discord Heartbeat.
- **Minimum Instance**: Prevents scaling to zero.
- **Cloud Run Ingest**: GCP's Image Streaming will help handle the 3GB image size without massive startup delays.

## 3. Proposed Changes

### A. Docker Optimization
#### [MODIFY] [Dockerfile](file:///Users/kevinwang/Documents/20Projects/AIG200Capstone/Dockerfile)
- **Base**: `python:3.12-slim`.
- **Optimization**: Use a staged build or a dedicated `requirements_deploy.txt` to strip development tools.
- **Cloud Run Compliance**: Must listen on `$PORT` (using a dummy health check thread if necessary).
### C. English-Only Interface Refinement
#### [MODIFY] [bot.py](file:///Users/kevinwang/Documents/20Projects/AIG200Capstone/health_butler/discord_bot/bot.py)
- **Objective**: Replace all user-facing Chinese strings with English equivalents to align with the "English Only Delivery" rule.
- **Scope**:
    - Demo mode activation/deactivation announcements.
    - Demo rules and instructions.
    - Bot activity status ("[演示模式]" -> "[Demo Mode]").
    - Response prefixes ("[演示]" -> "[DEMO]").
    - Error messages and help prompts.
### D. Interactive Demo Registration Flow (v1 - Text Based)
- *Superseded by Section E*
- **Objective**: Initial implementation of multi-step registration.

### E. Comprehensive Demo UI Onboarding (5 Steps)
#### [MODIFY] [bot.py](file:///Users/kevinwang/Documents/20Projects/AIG200Capstone/health_butler/discord_bot/bot.py)
- **Objective**: Implement a high-fidelity, 5-step interactive flow to collect detailed user health profiles, matching the original architecture design.
- **Workflow**:
    1. **🚀 Welcome**: `/demo` → Send "Start Setup" button.
    2. **📋 Step 1 (Modal)**: Basic Information (Name, Age, Gender, Height, Weight).
    3. **🎯 Step 2 (Select)**: Health Goal (Lose Weight, Maintain, Gain Muscle).
    4. **🦵 Step 3 (Multi-Select)**: Health Conditions (Injury, Blood Pressure, etc.).
    5. **🏃 Step 4 (Select)**: Activity Level (Sedentary to Extra Active).
    6. **🥗 Step 5 (Multi-Select)**: Dietary Preferences (Vegetarian, Keto, etc.).
    7. **🎉 Activation**: Data summary + Demo Mode active.
- **Implementation**:
    - Update `HealthProfileModal` to include Name and Age.
    - Create View classes for subsequent steps (`GoalSelectView`, `ConditionSelectView`, `ActivitySelectView`, `DietSelectView`).
    - Chain these views to ensure a smooth transition between steps.
    - Ensure all strings are in English.

### B. CI/CD Pipeline & QA
#### [MODIFY] [deploy-bot.yml](file:///Users/kevinwang/Documents/20Projects/AIG200Capstone/.github/workflows/deploy-bot.yml)
- **QA Stage (New)**:
  - **Linting**: Basic Python syntax check.
  - **Secret Scanning**: Integrate `gitleaks` action to prevent accidental secret leaks.
  - **Unit Tests**: Run `pytest tests/test_health_swarm.py` to ensure core logic is intact.
- **Deployment Stage**:
  - Requires successful QA Stage (`needs: [qa]`).
  - Authenticate via Service Account, build to Artifact Registry, and deploy to Cloud Run with specific flags:
    `--no-cpu-throttling --min-instances 1 --memory 4Gi`.

## 4. Risks & Mitigations
- **Image Size**: 3GB+ is large. *Mitigation*: Enable GCP Artifact Registry Image Streaming and optimize layers.
- **Memory Usage**: RAG (ChromaDB) and Vision models are heavy. *Mitigation*: Start with 4GB RAM on Cloud Run.
- **Connectivity**: Discord Gateway timeouts. *Mitigation*: Handle `on_disconnect` with automatic restart in the entrypoint script.

## 5. Verification Plan

### Automated Tests - Exact commands you'll run, browser tests using the browser tool, etc.
- `venv/bin/pytest tests/test_health_swarm.py -v`: Verify core swarm logic locally.
- `gitleaks detect -v`: Ensure no secrets are leaked in the codebase.

### Local Docker Verification
- `docker-compose up --build -d`: Build and run the bot locally in a container.
- `curl -v http://localhost:8080/health`: Verify the health check endpoint is responding.
- Check container logs: `docker logs -f antigravity-bot`

### Manual Verification
- **Discord Interaction**: Activate `/demo` mode in Discord and verify response branding.
- **Image Analysis**: Upload a food photo and verify YOLO + Gemini detection flow.
- **Cloud Run URL**: Once deployed, verify the live URL in the GitHub Actions summary.
- **Runtime**: Check Cloud Run logs for successful Discord Login.
- **Live**: Test 3 typical user flows on Discord (Photo upload, Workout query, Nutrition chat).
