---
name: long-term-memory
description: Persistent long-term memory using sqlite-vec + FTS5 with BGE embedding. Provides cross-session memory storage, retrieval, and maintenance.
license: MIT
allowed-tools: Read Edit Bash Grep Glob
metadata:
  author: gitagent-community
  version: "1.0.0"
  category: memory
---

# Long-Term Memory

This skill gives you persistent memory across conversation sessions. Memories are stored in a local sqlite-vec + FTS5 database and retrieved automatically when relevant.

## 1. Setup Check (Every Session Start)

At the beginning of each session, silently check if setup is complete:

```bash
[ -f ~/.agents/long-term-memory/.setup_complete ] && echo "ready" || echo "needs_setup"
```

### If needs_setup

Locate the setup script in the current agent's skill directory, then run it:

```bash
bash "$(find ~/.gitagent ~/. -maxdepth 6 -path '*/long-term-memory/scripts/setup_env.sh' -print -quit 2>/dev/null)" light
```

If `find` returns nothing, try the current working directory:

```bash
bash ./skills/long-term-memory/scripts/setup_env.sh light
```

Wait for setup to complete (2-10 minutes depending on network). If it fails, report the error but continue the conversation without memory features.

### If ready

Read the runtime config once and remember the paths for this session:

```bash
cat ~/.agents/long-term-memory/config.json
```

From the output, note `venv_python` and `scripts_dir`. All subsequent commands use these two paths. For convenience, the wrapper `~/.agents/long-term-memory/ltm` is also available.

## 2. Session ID

At the start of each conversation, construct a session ID yourself using the format `YYYYMMDD_HHMMSS` (e.g., `20260308_143022`). Use the current date and approximate time. Reuse this same ID for all `--session-id` arguments throughout the session. Do NOT run a bash command to generate it.

## 3. Memory Query

### When to Query

Query memory when ANY of these conditions are true:
- User references past interactions: keywords like "之前", "上次", "以前", "我们讨论过", "还记得", "you mentioned", "last time", "previously"
- The first substantive message of a new session (not greetings like "hi"/"你好")
- User asks a question where you feel you should have context but don't
- User references a project, preference, or decision you don't recall from the current session

### When NOT to Query

- Simple greetings or chitchat
- The user provides complete context in their message
- Continuation of a topic already discussed in the current session
- Code execution requests where all information is present

### How to Query

Use heredoc to safely pass the query text (avoids shell escaping issues):

```bash
~/.agents/long-term-memory/.venv/bin/python \
  ~/.agents/long-term-memory/scripts/memory_query.py \
  --stdin --top-k 5 --threshold 0.6 <<'QUERY'
paste the user's question here verbatim
QUERY
```

Or with wrapper:

```bash
~/.agents/long-term-memory/ltm memory_query \
  --stdin --top-k 5 <<'QUERY'
paste the user's question here verbatim
QUERY
```

### Output Format

```json
{
  "results": [
    {
      "id": 1,
      "content": "memory text...",
      "summary": "short summary",
      "category": "decision",
      "importance": 8,
      "score": 0.82,
      "method": "fts5",
      "created_at": "2025-01-15 10:30:00",
      "session_id": "20250115_103000"
    }
  ],
  "count": 3,
  "mode": "hybrid",
  "vec_available": true
}
```

### How to Use Results

- If `count > 0`: Read each result's `content`. Integrate ONLY the relevant parts into your thinking. Reference memory-sourced information naturally — do NOT prefix with "[历史记忆]" or otherwise reveal the memory system to the user unless they ask about it.
- If `count == 0`: Proceed normally.
- If results contradict current conversation: Trust the current conversation. Memories may be outdated.
- NEVER dump raw query results to the user.

## 4. Memory Write

### When to Write

Write a memory when ANY of these conditions are true:

| Condition | Category | Importance |
|-----------|----------|------------|
| User explicitly says "记住", "remember", "以后都这样" | `preference` | 9 |
| User states a preference about tools/style/workflow | `preference` | 8 |
| A technical or architectural decision is made | `decision` | 8 |
| A task or follow-up is identified | `task` | 8 |
| A complex problem is solved | `solution` | 7 |
| A key fact about the user/project is established | `fact` | 6 |
| ~15 turns of substantive conversation have passed without a write | `conversation` | 5 |

### When NOT to Write

- Trivial exchanges, greetings, or small talk
- Information that already exists in memory (query first if unsure)
- Temporary debugging details or one-off commands
- Anything the user explicitly asks you NOT to remember

### How to Write

YOU generate the summary text. Use heredoc via `--stdin` to safely pass content (avoids shell escaping issues with quotes, $, backticks, etc.):

```bash
~/.agents/long-term-memory/.venv/bin/python \
  ~/.agents/long-term-memory/scripts/memory_write.py \
  --stdin --category decision --importance 8 \
  --session-id "THE_SESSION_ID" <<'CONTENT'
Your concise summary of what to remember.
Can be multiple lines. Special characters like $, ", ' are safe here.
CONTENT
```

Or with wrapper:

```bash
~/.agents/long-term-memory/ltm memory_write \
  --stdin --category decision --importance 8 \
  --session-id "THE_SESSION_ID" <<'CONTENT'
Your concise summary here.
CONTENT
```

### Writing Good Summaries

- Be concise: 1-3 sentences, max 500 characters
- Include context: what, why, and the outcome
- Be specific: "User prefers pytest over unittest" not "User has testing preferences"
- For decisions: include the alternatives considered and why this was chosen
- For tasks: include deadline or priority if mentioned

## 5. Session Status Check

At the start of a new session, after the setup check, also check the database status:

```bash
~/.agents/long-term-memory/ltm memory_status
```

If `recent_sessions` shows a session with 0 entries but you sense there should have been memories from that conversation, note this internally — the previous session may have ended abruptly.

## 6. Maintenance

Run maintenance when `db_size_mb > 50` or `total_memories > 3000`:

```bash
~/.agents/long-term-memory/ltm memory_maintain \
  --max-entries 5000 \
  --decay-days 30 \
  --merge-threshold 0.92
```

This decays old memories' importance, merges near-duplicates, and prunes low-value entries.

## 7. Rules

1. Memory operations are invisible to the user. Never say "let me check my memory" or "I'm saving this to memory" unless the user explicitly asks about the memory system.
2. If a script fails or times out, continue the conversation normally. Memory is an enhancement, not a requirement.
3. Always use the full venv Python path — Claude Code Bash runs in fresh shells.
4. The session ID must stay consistent within one conversation.
5. Do not write to memory more than once every 5 turns unless the user explicitly asks to remember something.
6. When in doubt about whether to query, query. The FTS5 path is fast (< 100ms).
7. When in doubt about whether to write, don't. Low-value memories dilute retrieval quality.
8. Always use `--stdin` with heredoc for passing content and queries. NEVER pass user text directly in `--content` or `--query` arguments — shell metacharacters will break the command.
