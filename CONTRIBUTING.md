<div align="center">

# Contributing to Phrasia

### Help make private, local-first writing tools better.

Thank you for your interest in contributing to Phrasia. Whether you are improving the writing engine, refining the interface, adding tests, or reporting a bug, your contributions are welcome.

<p>
  <img src="https://img.shields.io/badge/Python-3.11--3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11–3.13" />
  <img src="https://img.shields.io/badge/Node.js-20%2B-339933?style=for-the-badge&logo=nodedotjs&logoColor=white" alt="Node.js 20+" />
  <img src="https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/Frontend-TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
</p>

<p>
  <a href="#-development-setup">Development setup</a> ·
  <a href="#-code-style">Code style</a> ·
  <a href="#-engine-rules-and-data">Engine rules</a> ·
  <a href="#-pull-request-checklist">Pull requests</a> ·
  <a href="#-reporting-a-bug">Report a bug</a>
</p>

</div>

---

## 🌱 Development setup

Before making changes, prepare the local development environment.

### Requirements

- Python **3.11–3.13**
- Node.js **20 or newer**

### Get started

1. Install the required Python and Node.js versions.
2. Create a Python virtual environment and install `requirements.txt` together with `requirements-dev.txt`.
3. Open the `frontend/` directory and install frontend dependencies with `npm ci`.
4. Start the backend using `python run.py --no-browser`.
5. In a second terminal, start the frontend development server with `npm run dev`.

### Run the checks

Before opening a pull request, run the project checks:

```bash
python -m pytest
cd frontend
npm run typecheck
npm run build
```

Please make sure the relevant checks pass before submitting your changes.

## 🎨 Code style

Keep contributions consistent with the project's existing conventions:

- Use **typed Python** and keep runtime logic in `backend/`.
- Keep TypeScript strict and avoid unchecked DOM or API assumptions.
- Keep rules deterministic, local, and safe for names, numbers, links, quotations, hedges, and negations.
- Use UTF-8 and follow the indentation rules in `.editorconfig`.

## 🧠 Engine rules and data

Changes to writing rules or catalog entries should be focused, tested, and safe.

When adding or changing a rule or catalog entry:

1. Update the relevant file in `backend/engine/` or `backend/engine/data/`.
2. Add a focused test for the change.
3. Add or update a fixture in `tests/fixtures/` when the change affects end-to-end text.
4. Check both a positive case and a protected or unsafe case.

**Keep safety in mind:** rules should not unintentionally alter names, numbers, links, quotations, hedges, or negations.

## 📬 Pull request checklist

Before submitting your pull request, check each item:

- [ ] Python tests pass and TypeScript type checking is green.
- [ ] Every new dependency has a reason recorded in `DECISIONS.md`.
- [ ] User-facing text makes no detector-performance claim.
- [ ] A maintainer has rebuilt `frontend/dist/` if the frontend changed.
- [ ] `CHANGELOG.md` includes a line for every user-visible change.

A clear pull request description explaining what changed and why will also help maintainers review your contribution.

## 🐛 Reporting a bug

Please use the **bug-report template** when reporting an issue.

Include the following information so the problem can be reproduced:

- Operating system
- Python version
- Exact command used
- A minimal input that reproduces the issue
- Expected behavior
- Full error message, with any private text removed

Please remove personal, confidential, or sensitive text before sharing logs or reproduction examples.

---

<div align="center">

**Thank you for helping improve Phrasia.**

<sub>Thoughtful contributions make better tools for everyone.</sub>

</div>
