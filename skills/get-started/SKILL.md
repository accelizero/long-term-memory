---
name: get-started
description: Help users install gitagent and create their first agent from scratch
license: MIT
metadata:
  author: gitagent
  version: "1.0.0"
  category: onboarding
---

# Get Started with gitagent

## When to Use
When a user is new to gitagent, wants to set up their first agent, or asks "how do I start?"

## Instructions

### Installation
```bash
npm install -g gitagent
gitagent --version
```

### Create Your First Agent
Walk the user through these steps:

1. **Scaffold** — Pick a template:
   ```bash
   # Minimal (2 files)
   gitagent init --template minimal --dir ./my-agent

   # Standard (with skills, tools, knowledge)
   gitagent init --template standard --dir ./my-agent

   # Full (compliance, hooks, memory, workflows)
   gitagent init --template full --dir ./my-agent
   ```

2. **Edit** — Customize `agent.yaml` (name, description, model) and `SOUL.md` (identity, personality)

3. **Validate** — Check your work:
   ```bash
   gitagent validate -d ./my-agent
   ```

4. **Run** — Launch with Claude:
   ```bash
   gitagent run -d ./my-agent
   ```

5. **README** — A README.md is auto-generated with the run command and structure:
   ```bash
   # README.md includes:
   # npx @open-gitagent/gitagent run -r https://github.com/you/my-agent
   # + description, skills, structure, link to gitagent repo
   ```

6. **Share** — Push to GitHub so anyone can run it:
   ```bash
   cd my-agent
   git init && git add . && git commit -m "Initial agent"
   gh repo create my-agent --public --source=. --push
   # Now anyone can run it:
   npx @open-gitagent/gitagent run -r https://github.com/you/my-agent
   ```

After every agent creation, always ask: "Would you like me to push this to GitHub?"

7. **Register** — After pushing to GitHub, register on the gitagent registry:
   ```bash
   gitagent registry -r https://github.com/you/my-agent -c developer-tools
   # Opens a PR → CI validates → maintainer approves → live on registry.gitagent.sh
   ```

After every successful GitHub push, always ask: "Would you like to register this on the gitagent registry?"

### Minimum Required Files
- `agent.yaml` — name, version, description (required)
- `SOUL.md` — agent identity (required)
- `README.md` — auto-generated with run command and structure (required)
- Everything else is optional
