# DanmarksStatistik – README

A Python script that retrieves the following figures from 01/2024 and onwards from tables in Statistics Denmark’s StatBank.  

The following tables can be retrieved:

Befolkning (folk1am.py)  
Forbrugerforventninger (forv1.py)  
Producentprisindekset (pris4321p.py)  
Importprisindekset (pris4321i.py)  
Forbrugerprisindekset (pris111.py)  

## Installation

**Creating a virtual environment and installing packages:**
```zsh
python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip denstatbank pandas && deactivate
```

## Run python scripts

**Run from terminal:**
```zsh
cd Documents/python/DanmarksStatistik && source .venv/bin/activate && python3 folk1am.py && python3 forv1.py && python3 pris4321p.py && python3 pris4321i.py && python3 pris111.py && deactivate && cd ../../../
```

**Run from folder:**
```zsh
source .venv/bin/activate && python3 folk1am.py && python3 forv1.py && python3 pris4321p.py && python3 pris4321i.py && python3 pris111.py && deactivate
```
