# F5 Guardrail Evaluator on Windows

Run the app locally using Windows PowerShell and Python. Docker is optional and is not needed for this setup.

## Prerequisites

- Python 3.11 or newer, with the `py` command available.
- Git, if you want to clone the repository. You can also download and extract the repository ZIP or copy the project folder to Windows.
- Internet access to install the Python dependencies. Demo Data Mode runs offline after installation.

Open PowerShell and check your Python version:

```powershell
py -3 --version
```

The version must be 3.11 or newer. If `py` is unavailable but `python --version` reports a supported version, use `python` instead of `py -3` when creating the virtual environment below.

## Download the project

```powershell
git clone https://github.com/f5devcentral/f5-guardrail-evaluator.git
cd f5-guardrail-evaluator
```

If you already have the project, open PowerShell in its folder instead. For example, replace this path with your actual location:

```powershell
cd "C:\Projects\f5-guardrail-evaluator"
```

Run all subsequent commands from the project folder, which contains `pyproject.toml` and `app.py`. If you copied the project from another computer, create a fresh Windows virtual environment; do not reuse a copied `.venv` folder.

## Install

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

These commands use the virtual environment directly. Activation and PowerShell execution-policy changes are unnecessary.

## Launch

```powershell
.\.venv\Scripts\guardrail-evaluator.exe serve
```

Open **http://127.0.0.1:7860** in your browser. Keep PowerShell open while using the app. Press **Ctrl+C** in PowerShell to stop it.

An equivalent launch command is:

```powershell
.\.venv\Scripts\python.exe app.py
```

To start the app again later, open PowerShell in the project folder and repeat the launch command. You do not need to reinstall it each time.

## Try Demo Data Mode

No F5 token or `.env` file is required for an offline demo. No LLM is called; demo results and timings are fixed synthetic data.

1. Open the **Evaluate** tab.
2. Keep **Input prompts** and the sample library selected.
3. Click **Continue to setup**.
4. Keep **Demo Data Mode** selected and click **Start evaluation**.
5. After completion, click **View results & download reports**.

## Configure live F5 scans

Stop the app before changing its environment configuration. On first setup, copy the example configuration and open it in Notepad:

```powershell
Copy-Item .env.example .env
notepad .env
```

If `.env` already exists, open it directly instead of copying over it.

Set these values for your tenant:

```dotenv
F5_BASE_URL=https://your-tenant.example.com
F5_TOKEN=your-api-token
F5_PROJECT=your-project-id
```

Replace the example URL and token with your actual values. `F5_PROJECT` is optional; you can select a project in the UI. Keep your token private and do not commit `.env` to source control. Existing environment variables override values in `.env`.

Save the file, restart the app, and select **Live API Mode** in the evaluation setup.

Alternatively, enter the tenant URL and token in **Settings**, save, and select **Test connection & load projects**. Settings entered in the UI are session-local. A successful project lookup verifies authentication and project discovery, but does not establish scan permission or guardrail effectiveness.

## Optional offline CLI evaluation

This example runs the demo dataset and writes CSV, JSONL, and HTML reports into `results`:

```powershell
.\.venv\Scripts\guardrail-evaluator.exe evaluate --demo --mode defence-in-depth --strategy comparison --dataset datasets/demo_scenarios.jsonl --output-dir results
```

## Troubleshooting

| Problem | What to do |
|---|---|
| `py` is not recognized | Try `python --version`. If neither command works, install Python with command-line access enabled, then open a new PowerShell window. |
| Python is older than 3.11 | Install a supported version and create the virtual environment with that interpreter. For example, `py -3.11 -m venv .venv` explicitly selects an installed Python 3.11. |
| `.venv\Scripts\python.exe` is missing | Confirm you are in the project folder and that virtual environment creation completed successfully. |
| `guardrail-evaluator.exe` is missing | Run `.\.venv\Scripts\python.exe -m pip install -e .` from the project folder and check for installation errors. |
| PowerShell blocks `Activate.ps1` | Use the commands in this guide, which do not require activation. |
| Port 7860 is already in use | Run `.\.venv\Scripts\guardrail-evaluator.exe serve --port 7861`, then open **http://127.0.0.1:7861**. |
| Live scans return HTTP 401 or 403 | Check the tenant URL, token expiry, project access, and scan permissions. |
| Live scans cannot reach a corporate proxy | The F5 client ignores ambient proxy variables. It requires direct access or an explicitly adapted transport configuration. |

See the [main README](README.md) for dataset formats, metrics, and further CLI examples, and [Troubleshooting](docs/TROUBLESHOOTING.md) for API and evaluation issues. Shell examples in the main README use Unix syntax; the commands in this guide use PowerShell.

These instructions are derived from the project's configuration and entry points. Windows execution has not yet been validated.
