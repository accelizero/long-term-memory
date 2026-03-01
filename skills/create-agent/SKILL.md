---
name: create-agent
description: Guide users through agent.yaml configuration, SOUL.md writing, and directory structure
license: MIT
metadata:
  author: gitagent
  version: "1.0.0"
  category: authoring
---

# Create & Configure Agents

## When to Use
When a user wants to customize their agent.yaml, write a good SOUL.md, add skills/tools/knowledge, or set up compliance.

## agent.yaml Reference

### Required Fields
```yaml
spec_version: "0.1.0"
name: my-agent          # Unique identifier
version: 1.0.0          # Semantic version
description: What this agent does
```

### Model Configuration
```yaml
model:
  preferred: claude-sonnet-4-5-20250929
  fallback:
    - claude-haiku-4-5-20251001
  constraints:
    temperature: 0.2     # 0.0 - 1.0
    max_tokens: 4096
    top_p: 0.9
```

### Skills & Tools
```yaml
skills:
  - code-review          # Must match directory name in skills/
  - security-audit

tools:
  - lint-check           # Must match filename in tools/ (without .yaml)
```

### Runtime
```yaml
runtime:
  max_turns: 20          # Max conversation turns
  timeout: 120           # Seconds
```

### Sub-Agents
```yaml
agents:
  reviewer:
    description: Reviews code quality
    delegation:
      mode: auto
      triggers:
        - "review this"
```

## Writing a Good SOUL.md

A SOUL.md should have these sections:
- **Core Identity** — Who is this agent? One clear sentence.
- **Communication Style** — How does it talk? (direct, friendly, formal, etc.)
- **Values & Principles** — What does it prioritize?
- **Domain Expertise** — What does it know?
- **Collaboration Style** — How does it work with the user?

## Writing RULES.md

Structure as:
- **Must Always** — Non-negotiable behaviors
- **Must Never** — Hard boundaries
- **Output Constraints** — Formatting rules
- **Interaction Boundaries** — Scope limits

## Adding Skills

Create `skills/<name>/SKILL.md`:
```markdown
---
name: my-skill
description: What this skill does
license: MIT
allowed-tools: Read Edit Grep
metadata:
  version: "1.0.0"
---

# Instructions
[Detailed instructions for using this skill]
```

## Adding Tools

Create `tools/<name>.yaml`:
```yaml
name: my-tool
description: What this tool does
input_schema:
  type: object
  properties:
    query:
      type: string
      description: Search query
  required:
    - query
```

## Adding Knowledge

Create `knowledge/index.yaml`:
```yaml
documents:
  - path: reference.md
    always_load: true    # Include in system prompt
  - path: appendix.md
    always_load: false   # Available on demand
```

## README.md (Required — Always Generate)

Every agent MUST have a README.md. Generate it after creating the agent:

```markdown
# <agent-name>

<description from agent.yaml>

## Run

\`\`\`bash
npx @open-gitagent/gitagent run -r https://github.com/<username>/<agent-name>
\`\`\`

## What It Can Do

- <list each skill/capability>

## Structure

\`\`\`
<agent-name>/
├── agent.yaml
├── SOUL.md
├── RULES.md
├── skills/
│   └── ...
└── knowledge/
    └── ...
\`\`\`

## Built with

[gitagent](https://github.com/open-gitagent/gitagent) — a git-native, framework-agnostic open standard for AI agents.
```

Use `<username>/<agent-name>` as placeholder. Update with the real URL after pushing to GitHub.

## Push to GitHub (Always Ask)

After creating the agent, always ask:

> "Would you like me to push this to GitHub?"

If yes:

```bash
cd <agent-dir>
git init
git add .
git commit -m "Initial agent"
gh repo create <agent-name> --public --source=. --push
```

Then update the README.md `npx` run command with the actual repo URL from `gh repo create` output.

## Register on gitagent Registry (Always Ask After Push)

After a successful GitHub push, always ask:

> "Would you like to register this on the gitagent registry at registry.gitagent.sh?"

If yes:

```bash
gitagent registry -r https://github.com/<username>/<agent-name> -c <category> -a <adapters>
```

This opens a PR against `open-gitagent/registry`. Once CI validates and a maintainer approves, the agent appears on [registry.gitagent.sh](https://registry.gitagent.sh) and anyone can discover and run it.
