# DanmarksStatistik – README

Et Python-script, der henter følgende tal fra 01/2024 og frem fra tabeller i Statistikbanken.  

Følgende tabller kan hentes:

Befolkning (folk1am.py)  
Forbrugerforventninger (forv1.py)  
Producentprisindekset (pris4321p.py)  
Importprisindekset (pris4321i.py)  
Forbrugerprisindekset (pris111.py)  

## Installation

**Oprettelse via virtuelt miljø:**
```zsh
python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip denstatbank pandas && python3 folk1am.py && python3 forv1.py && python3 pris4321.py && python3 pris111.py
```



**Én linje (pip):**
```bash
pip install --upgrade pip denstatbank pandas 
```

**Eller via venv + requirements.txt:**
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```




FIRST TIME:  
pip install denstatbank pandas 


SECOND TIME:  
source .venv/bin/activate  
python3 folk1am.py && python3 forv1.py && python3 pris4321.py && python3 pris111.py

ONE-LINE:  
cd Documents/python/DanmarksStatistik && source .venv/bin/activate && python3 folk1am.py && python3 forv1.py && python3 pris4321p.py && python3 pris4321i.py && python3 pris111.py  


