# DocFlow Agent

Office document processing agent. Handle Word, Excel, and PDF files through a controlled workflow.

## Features

- **Word**: Read, extract structure, insert text by anchor, fill template fields
- **Excel**: Read cells, write cells, append rows
- **PDF**: Read text, classify type, export results
- **Controlled Workflow**: Plan → Confirm → Execute → Verify

## Quick Start

```bash
# 1. Install dependencies
pip install -e .

# 2. Copy and edit config
cp .env.example .env
# Edit .env with your LLM API key

# 3. Start API server
make run-api
```

## Project Structure

```
docflow-agent/
├── apps/
│   ├── api/              # FastAPI backend
│   └── web/              # Next.js frontend (TODO)
├── packages/
│   ├── agent_core/       # Agent core logic
│   │   ├── orchestrator  # Workflow orchestration
│   │   ├── router        # Task classification
│   │   ├── analyzer      # File analysis
│   │   ├── planner       # Plan generation (LLM)
│   │   ├── executor      # Tool execution
│   │   └── verifier      # Result verification
│   ├── tooling/          # Document processing tools
│   │   ├── word/
│   │   ├── excel/
│   │   └── pdf/
│   └── schemas/          # Data models (Pydantic)
├── storage/              # Files and database
└── tests/
```

## API Endpoints

### Tasks

- `POST /api/tasks/` - Create task and generate plan
- `GET /api/tasks/{task_id}` - Get task status
- `POST /api/tasks/{task_id}/confirm` - Confirm and execute
- `GET /api/tasks/{task_id}/audit` - Get audit log

### Files

- `POST /api/files/upload` - Upload file
- `GET /api/files/download/{filename}` - Download output file

## Workflow

```
upload → analyze → plan → await_confirm → execute → verify → done
```

## License

MIT
