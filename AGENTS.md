# Repository Guidelines

## Project Structure & Module Organization

- `frontend/`: React, Vite, TypeScript, and Tailwind UI. Source is in `frontend/src/`; output goes to `frontend/dist/`.
- `backend/`: planned FastAPI API for problems, submissions, RDS persistence, and SQS enqueueing.
- `worker/`: planned stateless SQS worker for Docker-based judging and result writes.
- `docker/python-runner/`: isolated Python execution image.
- `docs/`: architecture and load-test notes. `scripts/`: helper scripts. `.github/`: templates and workflow docs.

## Build, Test, and Development Commands

Run frontend commands from `frontend/`:

```bash
npm install
npm run dev
npm run build
npm run preview
```

- `npm run dev` starts the Vite development server.
- `npm run build` runs `tsc --noEmit` and creates a production Vite build.
- `npm run preview` serves the built frontend locally.

On PowerShell setups where `npm` is blocked, use `npm.cmd`, for example `npm.cmd run build`.

Build the Python runner image from the repo root:

```bash
docker build -t hufsolve-python-runner docker/python-runner
```

Backend and worker runtime commands are not committed yet; document them in module READMEs when added.

## Coding Style & Naming Conventions

Use TypeScript ES modules. Name React components and prop interfaces with `PascalCase`; use `camelCase` for variables, setters, and helpers. Keep shared types in `frontend/src/types.ts` and mock data in `frontend/src/data.ts`. Prefer Tailwind utility classes.

Use 2-space indentation for TS/TSX and 4-space indentation for future Python code. No formatter or linter config is committed, so preserve nearby style and rely on `npm run build`.

## Testing Guidelines

There is no automated test suite yet. For frontend changes, run `npm run build` before opening a PR. When adding tests, place them beside covered code or under a module-local `tests/` folder, and document the command.

## Commit & Pull Request Guidelines

Follow the documented commit prefixes: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, and `test:`. Branch names should describe scope, for example `feature/frontend-initial-layout`, `fix/submission-status-polling`, or `docs/aws-architecture`.

PRs target `main` and should include a summary, changes, verification steps, and a linked issue using the existing template. Check for secrets before requesting review.

## Security & Configuration Tips

Do not commit `.env`, AWS keys, DB passwords, private keys, or PEM files. Use `.env.example` only for variable names and safe samples. The API server should enqueue submissions and never execute user code directly; execution belongs in the Docker runner path.
