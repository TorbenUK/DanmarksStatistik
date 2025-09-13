Python scripts der kan hente tal fra tabeller i Statistikbanken.

Befolkning (folk1am.py)  
Forventninger (forv1.py) 
Producentprisindkset (pris4321p.py)
Importprisindekset (pris4321i.py)  
Forbrugerprisindekset (pris111.py)  

FIRST TIME:  
pip install denstatbank  
python3 -m venv .venv

SECOND TIME:  
source .venv/bin/activate  
python3 folk1am.py && python3 forv1.py && python3 pris4321.py && python3 pris111.py

ONE-LINE:  
cd Documents/python/DanmarksStatistik && source .venv/bin/activate && python3 folk1am.py && python3 forv1.py && python3 pris4321p.py && python3 pris4321i.py && python3 pris111.py  


