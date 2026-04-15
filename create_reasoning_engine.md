

# Deploy Google ADK Agent to Vertex AI Agent Engine

## Step 1 — Authenticate using gcloud

Install Google Cloud SDK if not installed.

Login to Google Cloud:

```bash
gcloud auth login
```

Set default project (optional but recommended):

```bash
gcloud config set project trusty-solution-405810
```

Verify authentication:

```bash
gcloud auth list
```

---

## Step 2 — Create PyCharm Project

Create a new Python project in **PyCharm**.

Then open terminal inside the project.

---

## Step 3 — Install Google ADK

```bash
pip install google-adk[vertexai]
```

Verify installation:

```bash
pip show google-adk
```

---

## Step 4 — Create Agent

```bash
adk create my_fourth_agent
```

This creates a starter agent project:

```
my_fourth_agent/
    agent.py
    requirements.txt
    ...
```

---

## Step 5 — Set Environment Variables (Windows CMD)

```bash
set PROJECT_ID=trusty-solution-405810
set LOCATION_ID=us-central1
```

---

## Step 6 — Deploy Agent to Vertex AI Agent Engine

```bash
adk deploy agent_engine --project=%PROJECT_ID% --region=%LOCATION_ID% --display_name="My fourth Agent" my_fourth_agent
```

---

## Common Error (Windows)

If you see error:

```
Deploy failed: [WinError 2] The system cannot find the file specified
```

Solution:

1. Close current terminal
2. Open new CMD
3. Run again:

```bash
set PROJECT_ID=trusty-solution-405810
set LOCATION_ID=us-central1

adk deploy agent_engine --project=%PROJECT_ID% --region=%LOCATION_ID% --display_name="My fourth Agent" my_fourth_agent
```

---

## After Successful Deployment

You will get output similar to:

```
remote_app.resource_name =
projects/trusty-solution-405810/locations/us-central1/reasoningEngines/1234567890123456789
```

This is your **Reasoning Engine ID**.

---

## Agent Engine Console Link

Open Agent Engine dashboard:

[https://console.cloud.google.com/vertex-ai/agents/agent-engines](https://console.cloud.google.com/vertex-ai/agents/agent-engines)

Select your project:

```
trusty-solution-405810
```

You will see your deployed agent.

---

## Final Example Reasoning Engine Resource Name

```
projects/trusty-solution-405810/locations/us-central1/reasoningEngines/1234567890123456789
```

Use this in code:

```python
REASONING_ENGINE_APP_NAME="projects/trusty-solution-405810/locations/us-central1/reasoningEngines/1234567890123456789"
```

---
