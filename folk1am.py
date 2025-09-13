from denstatbank import StatBankClient

sbc = StatBankClient(lang='da')

# Hent metadata for tabellen
meta = sbc.tableinfo('FOLK1AM', variables_df=True)

# Filtrér tidskoder (id) fra 2024M01 og frem
tid_df = meta[meta['variable'].str.lower() == 'tid']
all_times = tid_df['id'].tolist()
times_from_2024 = [t for t in all_times if t >= '2024M01']

vars_min = [
    sbc.variable_dict('OMRÅDE', ['000']),    # Hele landet
    sbc.variable_dict('KØN',    ['TOT']),    # Begge køn
    sbc.variable_dict('ALDER',  ['IALT']),   # I alt
    sbc.variable_dict('TID',    times_from_2024)
]

df = sbc.data('FOLK1AM', variables=vars_min)

serie = df.iloc[:, 0]

for tid, value in serie.items():
    print(f"{tid}: {value:,}".replace(",", "."))