# Logs node

## Purpose and quick use

`logs` emits one bounded structured message to exactly one workflow destination without serializing image data or credentials.

**Use when:** you need an operator popup, a backend terminal message, or a durable plain-text diagnostic in data/logs/workflow-log.txt at a specific workflow step.

**Quick flow:** `image-input` → `logs` → `image-output`

## Node structure

```text
(no input)
    │
    ▼
[logs]
    │
    └── (no output)
```

The system trigger activates `logs`; successful delivery emits success and validation or delivery errors emit failure. The node has no data ports.

## How the algorithm works

- Validate destination, severity, and bounded message text.
- Route the message to exactly one configured destination.
- Return a structured event for popup or file delivery while terminal delivery uses the backend logger.

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `logs` |
| Category | Debugging |
| Status | `debug` |
| Execution target | `local-cpu` |
| Capabilities | `structured-logging` |

> **DEBUG notice:** Executable for development/research, not approved for production.

## How to provide inputs and read outputs

| Key | Direction | Type | Required | Variadic | Label |
|---|---|---|---|---|---|
| — | — | — | — | — | No ports |

### Provide inputs

This node has no input.

### Read outputs

- —

## How to enter parameters

| Key | Kind | Default | Min | Max | Options | How to enter / Meaning |
|---|---|---|---|---|---|---|
| `destination` | `select` | `popup` | — | — | `popup`, `terminal`, `file` | Choose exactly one destination: popup, terminal, or file. |
| `level` | `select` | `info` | — | — | `info`, `warning`, `error` | Choose info, warning, or error severity. |
| `message` | `text` | `Workflow reached this node.` | — | — | — | Enter non-secret text between 1 and 1000 characters. |

## Copy-ready usage example

**Goal:** Display an operator warning when execution reaches the logs node.

**Workflow:** `image-input` → `logs` → `image-output`

- Drag Logs onto the canvas.
- Connect the upstream success output to the Logs trigger.
- Select popup, warning, and enter the bounded message.
- Connect Logs success to the next node and run the workflow.

**Paste into the config panel:**

```json
{
  "destination": "popup",
  "level": "warning",
  "message": "Alignment requires review."
}
```

**Example input:** No data input is required; activation arrives through the system trigger port.

**Expected output:** One warning popup appears and the node emits success.

## Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| No popup appears | The node was not reached or another destination is selected. | Check the control edge and select popup. |
| The node is red | The message or destination failed validation or delivery. | Inspect the node error and restore supported values. |
| A log file line is missing | File was not selected or the write failed. | Select file and inspect data/logs/workflow-log.txt plus backend health. |

## Limitations and production checks

- The node is DEBUG and not production-approved.
- Messages are limited to 1000 characters.
- Image bytes, credentials, secrets, and request payloads must never be logged.

### Production checklist

- Review every configured message for sensitive information.
- Verify popup behavior with operators and accessibility tools.
- Apply rotation and access controls to data/logs/workflow-log.txt.
