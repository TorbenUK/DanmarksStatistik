# DanmarksStatistik – README

Et Python-script, der henter følgende tal fra 01/2024 og frem fra tabeller i Statistikbanken.  
Python-script henter følgende tal fra 01/2024 og frem fra tabeller i Statistikbanken. 

Befolkning (folk1am.py)  
Forbrugerforventninger (forv1.py)  
Producentprisindekset (pris4321p.py)  
Importprisindekset (pris4321i.py)  
Forbrugerprisindekset (pris111.py)  


## Installation

**Én linje (pip):**
```bash
pip install --upgrade pip denstatbank pandas 
```






FIRST TIME:  
pip install denstatbank pandas 
python3 -m venv .venv

SECOND TIME:  
source .venv/bin/activate  
python3 folk1am.py && python3 forv1.py && python3 pris4321.py && python3 pris111.py

ONE-LINE:  
cd Documents/python/DanmarksStatistik && source .venv/bin/activate && python3 folk1am.py && python3 forv1.py && python3 pris4321p.py && python3 pris4321i.py && python3 pris111.py  


