---
name: register-agent
description: Help users register their agent on the gitagent public registry at registry.gitagent.sh
license: MIT
metadata:
  author: gitagent
  version: "1.0.0"
  category: publishing
---

# Register Agent on the gitagent Registry

## When to Use
After a user has created an agent and pushed it to GitHub. Always ask after the GitHub push step: "Would you like to register this agent on the gitagent registry?"

## What is the Registry
The gitagent registry at [registry.gitagent.sh](https://registry.gitagent.sh) is the public marketplace for gitagent agents. Anyone can browse, search, and run agents listed there. Submitting an agent opens a PR against `open-gitagent/registry` — CI validates it, a maintainer reviews, and the agent goes live.

## Prerequisites
Before registering, the user must have:
1. A valid gitagent agent (agent.yaml + SOUL.md)
2. The agent pushed to a **public** GitHub repository
3. `gh` CLI installed and authenticated (`gh auth status`)
4. `gitagent` CLI installed (`npm install -g gitagent`)

## How to Register

### One Command
```bash
gitagent registry -r https://github.com/<username>/<agent-name> -c <category> -a <adapters>
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-r, --repo <url>` | Public GitHub repo URL (**required**) | — |
| `-d, --dir <dir>` | Local agent directory to validate | `.` |
| `-c, --category <cat>` | Agent category | `developer-tools` |
| `-a, --adapters <list>` | Comma-separated adapters | `claude-code,system-prompt` |

### Valid Categories
`developer-tools`, `data-engineering`, `devops`, `compliance`, `security`, `documentation`, `testing`, `research`, `productivity`, `finance`, `customer-support`, `creative`, `education`, `other`

### Example

```bash
# From inside the agent directory
gitagent registry \
  -r https://github.com/shreyas-lyzr/my-agent \
  -c developer-tools \
  -a claude-code,openai,lyzr,system-prompt
```

### What It Does
1. Validates the local agent (agent.yaml + SOUL.md)
2. Detects your GitHub username via `gh api`
3. Builds `metadata.json` from agent.yaml fields
4. Forks `open-gitagent/registry`
5. Creates `agents/<username>__<agent-name>/` with metadata.json + README.md
6. Pushes to your fork and opens a PR against the registry
7. CI validates — once approved, agent appears on registry.gitagent.sh

### After Submission
- The PR will be validated by CI (schema check, repo clone, agent.yaml + SOUL.md verification)
- A maintainer reviews and merges
- The agent appears on [registry.gitagent.sh](https://registry.gitagent.sh) within minutes
- Anyone can then run it: `npx @open-gitagent/gitagent run -r <repo-url>`

## Post-Creation Flow Integration

After creating an agent, the full flow should be:

1. Create the agent (agent.yaml, SOUL.md, skills, etc.)
2. Generate README.md
3. Ask: "Would you like me to push this to GitHub?" → `gh repo create`
4. Ask: "Would you like to register this on the gitagent registry?" → `gitagent registry -r <repo-url>`

Always present step 4 after a successful GitHub push.
