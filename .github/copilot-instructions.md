# Copilot Instructions for DanmarksStatistik

## Project Overview
This project consists of Python scripts that retrieve and process statistical data from Statistics Denmark’s StatBank. Each script targets a specific dataset/table, e.g.:
- `folk1am.py`: Population
- `forv1.py`: Consumer expectations
- `pris4321p.py`: Producer price index
- `pris4321i.py`: Import price index
- `pris111.py`: Consumer price index
- `lbesk04.py`: Employment
- `sblon1.py`: (Purpose not described in README)

## Key Patterns & Conventions
- Each script is standalone and fetches data from StatBank using the `denstatbank`, `pandas`, and `pyjstat` libraries.
- Scripts are named after the StatBank table they process.
- Data retrieval typically starts from January 2024 (`01/2024`).
- Output format and storage conventions are not standardized—review individual scripts for output details.

## Developer Workflows
- **Environment setup:**
  - Use a Python virtual environment (`.venv`).
  - Install dependencies: `pip install --upgrade pip denstatbank pandas pyjstat`.
- **Running scripts:**
  - Activate the virtual environment: `source .venv/bin/activate`.
  - Run scripts individually: `python3 <scriptname>.py`.
  - To run all scripts in sequence, use the command from the README.
- **No build or test automation is present.**

## Integration & Dependencies
- Relies on external packages: `denstatbank`, `pandas`, `pyjstat`.
- No cross-script imports or shared modules—scripts are independent.
- No database or web server integration; all data is fetched live from StatBank APIs.

## Project-Specific Guidance
- When adding new scripts, follow the naming pattern `<statbank_table>.py` and use the same data retrieval approach as existing scripts.
- Keep the README updated with new scripts and their purposes.
- If standardizing output or adding shared utilities, consider refactoring into modules.

## References
- See `README.md` for setup and usage examples.
- Each script is self-contained; review them for specific data handling logic.
