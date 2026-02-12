# L2 Application Architecture
# Personal Health Butler AI

> **Version**: 1.1
> **Last Updated**: 2026-01-16
> **Parent Document**: [PRD v1.1](./PRD-Personal-Health-Butler.md)
> **TOGAF Layer**: L2 - Application Architecture

---

## 1. System Overview

### 1.1 C4 Level 1: System Context

```mermaid
graph TB
    %% Styles
    classDef user fill:#FFD700,stroke:#333,stroke-width:2px,color:black,rx:10,ry:10;
    classDef system fill:#87CEEB,stroke:#2b4b6f,stroke-width:2px,color:black,rx:5,ry:5;
    classDef external fill:#D3D3D3,stroke:#666,stroke-width:2px,color:black,stroke-dasharray: 5 5;
    classDef ai fill:#FFB6C1,stroke:#C71585,stroke-width:2px,color:black;

    User["User (Alex)"]:::user
    subgraph "Personal Health Butler System"
        PHB["Health Butler App"]:::system
    end
    ExternalKB["External Knowledge<br/>(USDA, Open Food Facts)"]:::external
    LLM["LLM Provider<br/>(Gemini 2.5 / DeepSeek)"]:::ai

    User -->|Uploads Image/Chat| PHB
    PHB -->|Queries| ExternalKB
    PHB -->|Inference| LLM
    PHB -->|Response| User
```

### 1.2 C4 Level 2: Container Diagram

```mermaid
graph TB
    %% Styles
    classDef user fill:#FFD700,stroke:#333,stroke-width:2px,color:black,rx:10,ry:10;
    classDef ui fill:#ADD8E6,stroke:#4682B4,stroke-width:2px,color:black;
    classDef logic fill:#98FB98,stroke:#2E8B57,stroke-width:2px,color:black;
    classDef db fill:#DDA0DD,stroke:#800080,stroke-width:2px,color:black,shape:cylinder;

    User[User]:::user
    
    subgraph "Dockerized Swarm Cluster"
        direction TB
        UI["Discord Bot Interface<br/>(discord.py)"]:::ui
        Coord["Coordinator Agent<br/>(Gemini Routing)"]:::logic
        Vision["Vision Singleton<br/>(YOLOv8 + Gemini Engine)"]:::logic
        NutSvc["Nutrition Agent<br/>(Hybrid Vision + RAG)"]:::logic
        FitSvc["Fitness Agent<br/>(Safety-First + BMR)"]:::logic
        
        UI -->|Events| Coord
        Coord -->|Execute| NutSvc
        Coord -->|Execute| FitSvc
        NutSvc -->|Shared| Vision
    end
    
    VDB[("ChromaDB / Vector Index")]:::db
    NutSvc --> VDB
    FitSvc --> VDB
```

---

## 2. Component Design (Modular MVP)

### 2.1 Service Catalog

| Agent | Responsibility | Key Tech | Status |
|---------|----------------|----------|--------|
| **Discord Bot** | Multi-modal entry point, Onboarding | discord.py | Deployed |
| **Coordinator** | Task Decomposition, LLM Routing | Google GenAI | High Fidelity |
| **Nutrition Agent**| Food Identity & Macro Breakdown | YOLOv8n, Gemini Flash | Hybrid Implemented |
| **Fitness Agent** | Safety-filtered coaching | Enhanced RAG, MSJ BMR | Context-Aware |

### 2.2 Component: Hybrid Vision System
**The core "Eye" of the system, shared via Singleton pattern.**
- **Stage 1: YOLOv8 (Physical)**: Detects food boundaries and count (locally).
- **Stage 2: Gemini Flash (Semantic)**: Detailed identification of ingredients, portions, and hidden macros.
- **RAG Verification**: Cross-references Gemini output with USDA nutritional database for verification.

### 2.3 Component: Safety-First Fitness
**Protects the user using medical-grade filtering logic.**
- **Condition Mapping**: Links health conditions (e.g. Heart Disease) to forbidden exercise patterns.
- **Dynamic BMR**: Calculates daily expenditure using user profile metrics.
- **Surplus/Deficit Logic**: Adjusts exercise intensity based on real-time nutrition logs.

---

## 3. Technology Stack & Integration

### 3.1 LLM Strategy (Tiered)

| Tier | Model | Use Case | Justification |
|------|-------|----------|---------------|
| **Primary** | **Gemini 2.5 Flash** | General Reasoning, Synthesis | Low cost, high speed, multimodal native |
| **Fallback** | **DeepSeek-V3 / GLM-4** | Complex reasoning (if needed) | Open weight / Cost effective |
| **Embedding** | **e5-large-v2** | Knowledge Retrieval | Best-in-class open embedding |

### 3.2 Computer Vision

- **Model**: **YOLO26 (Nano/Small)**
- **Optimization**: ONNX Runtime or TorchScript for CPU inference optimization.
- **Dataset**: Pre-trained on COCO, Fine-tuned on **Food-101**.

---

## 4. State Management

### 4.1 Implementation
- **Session State**: Managed in-memory via Streamlit Session State (ephemeral).
- **Conversation Memory**: `LangChain.memory.ConversationBufferWindowMemory` (k=5 rounds).

### 4.2 Data Flow

1. **User Upload** -> UI stores in RAM.
2. UI calls **Coordinator** with inputs.
3. Coordinator maintains short-term conversational context.
4. Coordinator calls **Nutrition Agent**.
5. Nutrition Agent runs **YOLO** (stateless).
6. Result returns to UI for display.
7. **No persistent DB** for user data (Privacy by Design).

---

## 5. Security Architecture (Zero Trust Lite)

- **API Security**: Although internal, services use strict Pydantic validation.
- **Secret Management**: `.env` files for keys (Gemini API, etc.), strictly git-ignored.
- **Input Sanitization**: All text inputs scanned for prompt injection markers before LLM processing.

---

## 6. Deployment View (Cloud Run)

```yaml
# Simplified Structure
services:
  app:
    image: health-butler-mvp:latest
    ports: [8080]
    env_file: .env
    resources:
      memory: 4GB  # Enough for YOLO + FAISS
```

**Scalability Strategy**:
- Cloud Run automatically scales to 0 when unused (Cost saving).
- Stateless design allows horizontal scaling if demo traffic spikes.

---

**Document Status**: 🟢 Draft v1.1 - Modular MVP Design
