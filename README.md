# Semester Quest

A playful semester-learning hub for Newton School of Technology students, styled with a Codédex-inspired pixel look and the requested Newton-style palette.

- **Light mode:** light clay canvas, soft sky-blue panels, deep navy text and controls.
- **Dark mode:** near-black canvas, navy surfaces and light-blue accents.
- **Sign-in:** Pune ADYPU email addresses ending in `@adypu.edu.in`, password and a six-digit email verification code.
- **Learning worlds:** Maths Arcade, System & AI Essentials, and Python Quest.
- **Practice:** quiz grading and XP, ten Python missions, and a six-mission virtual terminal with a virtual Git workflow.
- **Class library:** text extraction from PDF, DOCX, PPTX and supported text/code files, plus retrieval for the study tutor and draft flashcards.
- **Progress:** custom grade-scale CGPA calculator and a personal study planner.

The topic map and 21 starter questions are a starting point, not an official Newton/ADYPU syllabus. The app does not assume the university's CGPA conversion rules. Add your faculty material and enter the official grade bands before relying on course-specific results.

## Run locally on macOS / Linux

1. Install Python 3.11 or newer.
2. In Terminal, open the project folder and run:

   ```bash
   ./setup.sh
   ```

3. Setup creates `.env` with a fresh local secret. For local development, `DEV_SHOW_CODE=1` is enabled, so the six-digit sign-in code appears in the browser. This is only for local testing.
4. Start the application:

   ```bash
   ./run.sh
   ```

   On macOS, you can also double-click `run.command` after extracting the ZIP. The first launch installs the backend dependencies; later launches start the app directly.

5. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The backend serves the tested, self-contained browser UI from `backend/app/static`, so the app can be run without Node/npm. API documentation is at `/docs`.

## ADYPU email verification

The default `.env.example` is configured for development, not real email delivery. To send verification codes to student inboxes, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` and `SMTP_FROM`, then set:

```env
DEV_SHOW_CODE=0
```

The API validates the `@adypu.edu.in` domain and only signs in after the email code is verified. Do not expose development codes in a deployed environment.

## Python Lab sandbox

The Python runner is intentionally **fail-closed**. It never executes student code inside the FastAPI process. It requires Docker and starts a fresh container with:

- network disabled (`--network=none`);
- read-only container root and read-only source mount;
- 128 MB memory, 0.5 CPU and a 32-process limit;
- no Linux capabilities, `no-new-privileges`, and an unprivileged container user;
- a short execution timeout and bounded output.

Before using the lab, install and start Docker Desktop, then pull the image once:

```bash
docker pull python:3.13-alpine
```

In environments without a Docker daemon, the Run button returns a setup message and **does not execute code**. Do not replace this with unsandboxed `exec`, `eval`, or host subprocess execution. For a multi-user production deployment, run the sandbox as a separate isolated worker service rather than granting the web app broad access to a host Docker socket.

## Virtual Terminal

The Terminal Lab implements a small safe virtual shell and filesystem. It supports practice commands such as `pwd`, `ls`, `cd`, `mkdir`, `touch`, `cat`, `echo`, `cp`, `mv`, `rm`, `chmod`, `grep`, `head`, `wc`, `find` and a virtual Git workflow (`init`, `status`, `add`, `commit`, `log`). It does not invoke the host shell or run arbitrary commands.

## Optional AI tutor model

Without a model configured, the tutor retrieves relevant passages from the student's own uploaded materials and labels this as built-in extractive behaviour. To enable generated explanations, set an OpenAI-compatible endpoint, for example:

```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=your-model-name
```

The same interface can connect to Ollama, LM Studio, vLLM or another OpenAI-compatible service. The model is optional; uploads and retrieval work without it.

## React + TypeScript source

A Vite + React + TypeScript frontend is included in `frontend/`. Once npm can reach the package registry, install and run it with:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`. To build the React app into the backend's static directory:

```bash
npm run build
```

This workspace did not have npm registry connectivity, so the React bundle could not be installed or built here. The default served UI is the dependency-free browser fallback in `backend/app/static` and was syntax-checked; the React source is included for normal local development/building.

## Tests

From the backend directory:

```bash
cd backend
python -m pytest -q
```

The test suite covers ADYPU auth and OTP, themes, worlds, quiz grading and XP idempotency, fail-closed Python execution, virtual-shell safety and Git, text uploads and retrieval, flashcard scheduling, planner CRUD, custom grade scales and material privacy.

## Configuration and data

- SQLite database: `backend/data/semester_quest.db` by default.
- Upload storage: `backend/data/uploads/<user-id>/` by default.
- Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL to use Postgres. Installations include the `psycopg` driver.
- Set `SQ_DATA_DIR` and `SQ_UPLOAD_DIR` to move persistent data outside the source tree.
- Each account's uploaded materials and virtual-shell state are scoped by user ID.

## Important production checklist

- Set a unique `SQ_SECRET_KEY`; do not use the example/development value.
- Set `DEV_SHOW_CODE=0` and test SMTP delivery.
- Use HTTPS and configure `SQ_CORS_ORIGINS` to exact trusted origins.
- Use PostgreSQL, regular backups, upload size limits and a retention policy for production.
- Keep the Python sandbox isolated from the web worker. Review infrastructure and rate limits before opening sign-up to multiple users.
- Verify your official syllabus, exam dates and grade scale before treating sample content as authoritative.


## Verification

The delivered backend test suite currently passes **9/9 tests**. A local smoke test also confirmed that the server starts, `/api/health` responds, and the home page is served. The React + TypeScript source is included; npm dependencies were not installed in this build environment, so the included dependency-free browser UI is the default runnable frontend.
