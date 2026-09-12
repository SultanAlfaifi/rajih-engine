# GitHub repository guide

Canonical public repository: `https://github.com/SultanAlfaifi/rajih-engine`.

Clone and install:

```powershell
git clone https://github.com/SultanAlfaifi/rajih-engine.git
Set-Location rajih-engine
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

Recommended GitHub settings:

- Require passing CI before merging changes.
- Enable private vulnerability reporting.
- Keep GitHub Actions permissions read-only unless a workflow needs more.
- Use GitHub Releases for canonical versioned source copies.
- Do not select an automated open-source license template; this repository already contains a custom source-available license.

The private research repository and its history are separate from this public engineering edition.
