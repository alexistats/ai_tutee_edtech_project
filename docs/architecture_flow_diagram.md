# AI Tutee Tool - Architecture Flow Diagram

## System Architecture Overview

```mermaid
flowchart TB
    subgraph UI["User Interface Layer"]
        CLI[CLI Interface<br/>main_cli.py]
        Teacher[Teacher Input<br/>Interactive/Scripted]
    end

    subgraph Config["Configuration Layer"]
        Scenarios[Scenario YAMLs<br/>4 Teaching Scenarios]
        Schema[Schema Validator<br/>scenario.schema.json]
        Env[Environment Config<br/>.env]
    end

    subgraph Orchestration["Orchestration & Session Management"]
        Session[Session Manager<br/>Turn-by-turn dialogue]
        Messages[Message History<br/>Management]
        Logger[Transcript Logger<br/>JSONL/JSON]
    end

    subgraph AIEngine["AI Student Engine"]
        SysPrompt[System Prompt Template<br/>system_ai_student.md]
        PromptFiller[Prompt Filler<br/>Placeholder Injection]
        OpenAI[OpenAI API<br/>GPT Models]
    end

    subgraph Utils["Utility Layer"]
        IO[File I/O<br/>YAML/JSON/JSONL]
        PromptLoader[Prompt Loader<br/>Template Processing]
    end

    subgraph Output["Output & Evaluation"]
        Transcripts[Session Transcripts<br/>JSONL Format]
        Summary[Summary Reports<br/>JSON Format]
        Rubric[Evaluation Rubric<br/>rubrics.md]
    end

    %% Connections
    Teacher --> CLI
    CLI --> Session
    Session --> Messages

    Scenarios --> Schema
    Schema --> IO
    IO --> Session
    Env --> Session

    Session --> PromptLoader
    PromptLoader --> SysPrompt
    SysPrompt --> PromptFiller
    PromptFiller --> Messages

    Messages --> OpenAI
    OpenAI --> Messages

    Messages --> Logger
    Logger --> Transcripts
    Logger --> Summary

    Transcripts --> Rubric

    %% Styling
    classDef uiClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef configClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef orchestrationClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef aiClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef utilClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef outputClass fill:#fff9c4,stroke:#f57f17,stroke-width:2px

    class CLI,Teacher uiClass
    class Scenarios,Schema,Env configClass
    class Session,Messages,Logger orchestrationClass
    class SysPrompt,PromptFiller,OpenAI aiClass
    class IO,PromptLoader utilClass
    class Transcripts,Summary,Rubric outputClass
```

---

## Session Flow Diagram

```mermaid
flowchart TD
    Start([START SESSION]) --> ParseArgs[Parse CLI Arguments<br/>scenario, turns, model, policy]

    ParseArgs --> LoadScenario[Load Scenario YAML<br/>subskills, misconceptions, tasks]

    LoadScenario --> BuildConfig[Build Prompt Configuration<br/>Merge CLI overrides + scenario defaults]

    BuildConfig --> FillPrompt[Fill System Prompt<br/>Replace placeholders with config values]

    FillPrompt --> InitSession[Initialize Session<br/>Create message history]

    InitSession --> GenOpening[Generate Student Opening<br/>AI asks clarifying question]

    GenOpening --> LogOpening[Log Opening Message]

    LogOpening --> DialogueLoop{More Turns?}

    DialogueLoop -->|Yes| GetTeacher[Get Teacher Prompt<br/>Interactive or Scripted]

    GetTeacher --> AddPolicy[Add Policy Reminder<br/>if applicable]

    AddPolicy --> SendToAI[Send to OpenAI API<br/>Full message history]

    SendToAI --> ReceiveResponse[Receive AI Student Response]

    ReceiveResponse --> LogExchange[Log Teacher & Student Messages]

    LogExchange --> Display[Display to Teacher]

    Display --> DialogueLoop

    DialogueLoop -->|No| WriteTranscript[Write Full Transcript<br/>JSONL Format]

    WriteTranscript --> WriteSummary[Write Summary Report<br/>JSON Format]

    WriteSummary --> End([END SESSION])

    %% Styling
    classDef startEnd fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
    classDef process fill:#2196f3,stroke:#0d47a1,stroke-width:2px,color:#fff
    classDef decision fill:#ff9800,stroke:#e65100,stroke-width:2px,color:#fff
    classDef io fill:#9c27b0,stroke:#4a148c,stroke-width:2px,color:#fff

    class Start,End startEnd
    class ParseArgs,LoadScenario,BuildConfig,FillPrompt,InitSession,GenOpening,GetTeacher,AddPolicy,SendToAI,ReceiveResponse,Display process
    class DialogueLoop decision
    class LogOpening,LogExchange,WriteTranscript,WriteSummary io
```

---

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph Input["Input Sources"]
        ScenarioFile[Scenario YAML<br/>Configuration]
        TeacherInput[Teacher Prompts<br/>Interactive/Tasks]
        EnvVars[Environment Variables<br/>API Keys, Model Config]
    end

    subgraph Processing["Core Processing"]
        Config[Configuration<br/>Merger]
        Template[Template<br/>Engine]
        API[OpenAI<br/>API Client]
    end

    subgraph Memory["Session State"]
        MsgHistory[Message<br/>History]
        Metadata[Session<br/>Metadata]
    end

    subgraph Output["Output Artifacts"]
        JSONL[Transcript<br/>JSONL]
        JSON[Summary<br/>JSON]
    end

    %% Flow
    ScenarioFile --> Config
    TeacherInput --> Config
    EnvVars --> API

    Config --> Template
    Template --> MsgHistory

    MsgHistory --> API
    API --> MsgHistory

    MsgHistory --> Metadata
    Metadata --> JSONL
    Metadata --> JSON

    %% Styling
    classDef inputClass fill:#bbdefb,stroke:#1976d2,stroke-width:2px
    classDef processClass fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
    classDef memoryClass fill:#fff9c4,stroke:#f9a825,stroke-width:2px
    classDef outputClass fill:#f8bbd0,stroke:#c2185b,stroke-width:2px

    class ScenarioFile,TeacherInput,EnvVars inputClass
    class Config,Template,API processClass
    class MsgHistory,Metadata memoryClass
    class JSONL,JSON outputClass
```

---

## Component Interaction Diagram

```mermaid
flowchart TB
    subgraph Scenarios["4 Teaching Scenarios"]
        S1[Data Types<br/>Classification]
        S2[Type to Chart<br/>Mapping]
        S3[Chart to Task<br/>Alignment]
        S4[Data Preparation<br/>Cleaning]
    end

    subgraph StudentBehavior["AI Student Behavior"]
        B1[Clarification<br/>Ask Questions]
        B2[Diagnostic Errors<br/>Surface Misconceptions]
        B3[Policy Adherence<br/>Withhold/Guide/Solve]
        B4[Positive Tone<br/>Encouraging]
        B5[Reflection<br/>Learning Summary]
    end

    subgraph Evaluation["Evaluation Framework"]
        R1[Clarification Rate<br/>Score 0-2]
        R2[Diagnostic Quality<br/>Score 0-2]
        R3[Policy Adherence<br/>Score 0-2]
        R4[Positive Reinforcement<br/>Score 0-2]
        R5[Reflection Quality<br/>Score 0-2]
    end

    %% Connections
    S1 --> B1
    S1 --> B2
    S2 --> B1
    S2 --> B2
    S3 --> B1
    S3 --> B2
    S4 --> B1
    S4 --> B2

    B1 --> B3
    B2 --> B3
    B3 --> B4
    B4 --> B5

    B1 --> R1
    B2 --> R2
    B3 --> R3
    B4 --> R4
    B5 --> R5

    %% Styling
    classDef scenarioClass fill:#e1bee7,stroke:#6a1b9a,stroke-width:2px
    classDef behaviorClass fill:#c5e1a5,stroke:#558b2f,stroke-width:2px
    classDef evalClass fill:#ffccbc,stroke:#d84315,stroke-width:2px

    class S1,S2,S3,S4 scenarioClass
    class B1,B2,B3,B4,B5 behaviorClass
    class R1,R2,R3,R4,R5 evalClass
```

---

## Technology Stack

```mermaid
graph TB
    subgraph Frontend["User Interface"]
        CLI[Python CLI<br/>argparse]
    end

    subgraph Backend["Core Application"]
        Python[Python 3.11+<br/>Core Runtime]
        IO[PyYAML<br/>JSON Processing]
        Prompt[Template Engine<br/>Placeholder Filling]
    end

    subgraph AI["AI Services"]
        OpenAI[OpenAI API<br/>GPT Models]
    end

    subgraph Storage["Data Storage"]
        JSONL[JSONL Files<br/>Transcripts]
        JSON[JSON Files<br/>Summaries]
        YAML[YAML Files<br/>Scenarios]
    end

    subgraph Quality["Code Quality"]
        Pytest[pytest<br/>Testing]
        Ruff[ruff<br/>Linting]
        Black[black<br/>Formatting]
    end

    CLI --> Python
    Python --> IO
    Python --> Prompt
    Python --> OpenAI

    IO --> JSONL
    IO --> JSON
    IO --> YAML

    Python --> Pytest
    Python --> Ruff
    Python --> Black

    %% Styling
    classDef frontendClass fill:#81d4fa,stroke:#01579b,stroke-width:2px
    classDef backendClass fill:#a5d6a7,stroke:#2e7d32,stroke-width:2px
    classDef aiClass fill:#ffab91,stroke:#d84315,stroke-width:2px
    classDef storageClass fill:#ce93d8,stroke:#6a1b9a,stroke-width:2px
    classDef qualityClass fill:#fff59d,stroke:#f57f17,stroke-width:2px

    class CLI frontendClass
    class Python,IO,Prompt backendClass
    class OpenAI aiClass
    class JSONL,JSON,YAML storageClass
    class Pytest,Ruff,Black qualityClass
```

---

## How to Use This Diagram in PowerPoint

### Option 1: Online Mermaid Editor (Recommended)
1. Visit https://mermaid.live/
2. Copy the Mermaid code from any diagram above
3. Paste it into the editor
4. Click "Download" and choose PNG or SVG format
5. Insert the image into your PowerPoint presentation

### Option 2: VS Code Extension
1. Install "Markdown Preview Mermaid Support" extension
2. Open this file in VS Code
3. Use Preview mode to view rendered diagrams
4. Take screenshots or export as images

### Option 3: Command Line (requires npm)
```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Convert to PNG
mmdc -i docs/architecture_flow_diagram.md -o diagram.png

# Convert to SVG (vector, better for scaling)
mmdc -i docs/architecture_flow_diagram.md -o diagram.svg
```

### Option 4: GitHub Integration
1. Push this file to GitHub
2. GitHub automatically renders Mermaid diagrams
3. Take screenshots from the rendered view

---

## Diagram Descriptions

### 1. System Architecture Overview
Shows the five main layers of the AI Tutee system and how they interact:
- **User Interface Layer**: CLI and teacher input
- **Configuration Layer**: Scenarios, schemas, and environment variables
- **Orchestration Layer**: Session management and logging
- **AI Engine Layer**: Prompt processing and OpenAI integration
- **Utility Layer**: File I/O and template processing
- **Output Layer**: Transcripts, summaries, and evaluation rubrics

### 2. Session Flow Diagram
Illustrates the complete lifecycle of a teaching session:
- Initialization (parsing args, loading scenarios, building config)
- Session setup (filling prompts, initializing history)
- Main dialogue loop (teacher prompts → AI responses)
- Session completion (writing transcripts and summaries)

### 3. Data Flow Diagram
Shows how data moves through the system:
- **Input**: Scenario files, teacher prompts, environment variables
- **Processing**: Configuration merging, template filling, API calls
- **Memory**: Message history and session metadata
- **Output**: JSONL transcripts and JSON summaries

### 4. Component Interaction Diagram
Demonstrates the relationship between:
- **4 Teaching Scenarios**: Different skill focuses
- **AI Student Behaviors**: Clarification, diagnostics, policy adherence, tone, reflection
- **Evaluation Framework**: 5 rubric criteria with 0-2 scoring

### 5. Technology Stack
Maps the technologies used at each layer:
- Frontend: Python CLI
- Backend: Python 3.11+, PyYAML, template engine
- AI Services: OpenAI API
- Storage: JSONL, JSON, YAML files
- Code Quality: pytest, ruff, black
