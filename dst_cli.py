#!/usr/bin/env python3
# pip install denstatbank pandas matplotlib
# python dst_cli.py

from denstatbank import StatBankClient
import pandas as pd
import matplotlib.pyplot as plt
import sys
import textwrap

# ---------- Utility ----------
def hr():
    print("-" * 80)

def wrap(s, width=78):
    return "\n".join(textwrap.wrap(str(s), width=width))

def prompt(msg, default=None):
    if default is None:
        return input(msg).strip()
    val = input(f"{msg} [{default}]: ").strip()
    return val if val else default

def choose_from_list(items, show_cols=None, max_rows=20, title=None):
    """
    Viser en nummereret liste (eventuelt top-N) og lader brugeren vælge index.
    Returnerer valgt row (pd.Series).
    """
    if isinstance(items, pd.DataFrame):
        df = items.reset_index(drop=True)
    else:
        df = pd.DataFrame(items)

    if show_cols is None:
        show_cols = [c for c in df.columns if c.lower() in ("id", "text", "table", "description")] or list(df.columns)

    if title:
        print(title)
    hr()
    show = df[show_cols].head(max_rows).copy()
    show.insert(0, "#", range(1, len(show) + 1))
    print(show.to_string(index=False))
    hr()
    idx = prompt("Vælg nummer (#) eller Enter for at afbryde", "")
    if not idx:
        return None
    try:
        idx_int = int(idx) - 1
        if 0 <= idx_int < len(df):
            return df.iloc[idx_int]
    except ValueError:
        pass
    print("Ugyldigt valg.")
    return None

def safe_upper(s):
    return s.strip().upper() if isinstance(s, str) else s

# ---------- Core ----------
class DSTCLI:
    def __init__(self, lang="da"):
        self.sbc = StatBankClient(lang=lang)
        self.tables_df = None  # cache

    def refresh_tables(self):
        print("Henter tabelliste fra Statistikbanken…")
        self.tables_df = self.sbc.tables()  # DataFrame med mindst kolonnerne 'id' og 'text'
        # Normaliser hjælpekollonner til lokal søgning
        for col in ("id", "text"):
            if col in self.tables_df.columns:
                self.tables_df[col] = self.tables_df[col].astype(str)

    # ---------- Menuer ----------
    def main_menu(self):
        while True:
            hr()
            print("Danmarks Statistik — menu")
            print("1) Søg tabeller (tekst)")
            print("2) Gennemse top-tabeller")
            print("3) Indlæs tabel-ID direkte")
            print("4) Opdater tabelliste (refresh)")
            print("q) Afslut")
            choice = prompt("Vælg", "")
            if choice.lower() == "q":
                print("Farvel!")
                return
            elif choice == "1":
                self.search_tables_menu()
            elif choice == "2":
                self.browse_tables_menu()
            elif choice == "3":
                self.fetch_by_id_menu()
            elif choice == "4":
                self.refresh_tables()
            else:
                print("Ukendt valg.")

    def ensure_tables(self):
        if self.tables_df is None or self.tables_df.empty:
            self.refresh_tables()

    def search_tables_menu(self):
        self.ensure_tables()
        q = prompt("Søg i 'id' eller titel/tekst (fx 'befolkning' eller 'folk1a')", "")
        if not q:
            return
        ql = q.lower()
        df = self.tables_df
        # simpel lokal søgning i id og text
        mask = df["id"].str.contains(ql, case=False, na=False) | df["text"].str.contains(ql, case=False, na=False)
        hits = df.loc[mask].copy()
        if hits.empty:
            print("Ingen tabeller matchede søgningen.")
            return
        row = choose_from_list(hits, show_cols=[c for c in ["id", "text"] if c in hits.columns], max_rows=30, title="Søgeresultater (maks 30 vist)")
        if row is not None:
            self.table_workflow(row["id"])

    def browse_tables_menu(self):
        self.ensure_tables()
        # Vis “top” tabeller — bare de første 40 som en hurtig browse
        top_df = self.tables_df.head(40).copy()
        row = choose_from_list(top_df, show_cols=[c for c in ["id", "text"] if c in top_df.columns], max_rows=40, title="Top-tabeller (første 40)")
        if row is not None:
            self.table_workflow(row["id"])

    def fetch_by_id_menu(self):
        table_id = prompt("Indtast tabel-id (fx 'folk1a')", "")
        if not table_id:
            return
        self.table_workflow(table_id.strip())

    # ---------- Workflow for en valgt tabel ----------
    def table_workflow(self, table_id):
        hr()
        print(f"Tabel: {table_id}")
        try:
            # Metadata
            info_df = self.sbc.tableinfo(table_id, variables_df=True)
        except Exception as e:
            print("Kunne ikke hente metadata for tabellen:", e)
            return

        if info_df is None or info_df.empty:
            print("Ingen metadata fundet.")
            return

        # Vis et kort overblik
        cols_to_show = [c for c in ["variable", "id", "text"] if c in info_df.columns]
        print("Tilgængelige variabler og værdier (første 50 rækker):")
        print(info_df[cols_to_show].head(50).to_string(index=False))

        # Valg af variabler
        chosen = []
        print("\nVælg variabler (tryk ENTER for at afslutte valg).")
        all_vars = sorted(info_df["variable"].unique().tolist())
        # Hjælp: vis liste over variabel-koder
        print("Variabler fundet:", ", ".join(all_vars))
        while True:
            var_code = safe_upper(prompt("Variabel-kode (fx KØN, ALDER, TID) eller ENTER for at fortsætte", ""))
            if not var_code:
                break
            poss = info_df[info_df["variable"] == var_code][["id", "text"]].drop_duplicates()
            if poss.empty:
                print("Ukendt variabel-kode for denne tabel.")
                continue
            print("\nMulige værdier (første 30):")
            print(poss.head(30).to_string(index=False))
            vals_str = prompt("Værdier kommasepareret (brug * for alle)", "*")
            if vals_str.strip() == "*":
                vals = poss["id"].astype(str).tolist()
            else:
                vals = [v.strip() for v in vals_str.split(",") if v.strip()]
            chosen.append(self.sbc.variable_dict(code=var_code, values=vals))

        # Hent data
        try:
            print("\nHenter data…")
            df = self.sbc.data(table_id=table_id, variables=chosen if chosen else None)
        except Exception as e:
            print("Kunne ikke hente data:", e)
            return

        if df is None or df.empty:
            print("Tomt resultat.")
            return

        print("\nEksempel på data:")
        print(df.head(12).to_string(index=False))
        hr()

        # Gem til CSV?
        if prompt("Gem som CSV? (y/n)", "n").lower() == "y":
            path = prompt("Filnavn", f"{table_id}.csv")
            try:
                df.to_csv(path, index=False)
                print(f"Gemt: {path}")
            except Exception as e:
                print("Kunne ikke gemme CSV:", e)

        # Hurtigt plot
        do_plot = prompt("Lave et hurtigt plot? (y/n)", "y").lower() == "y"
        if do_plot:
            self.quick_plot(df, table_id)

    # ---------- Plot ----------
    def quick_plot(self, df, table_id):
        """
        Laver et enkelt plot, hvis muligt.
        Regler:
          - Hvis 'TID' findes, bruges den som x-akse.
          - Forsøger at vælge én kategorikolonne + 'INDHOLD' som værdi.
        """
        if "INDHOLD" not in df.columns:
            print("Kan ikke plotte automatisk (mangler kolonnen 'INDHOLD').")
            return

        # Gæt på tidsakse
        x_col = "TID" if "TID" in df.columns else None

        # Find en kategorikolonne at splitte på (andet end INDHOLD og TID)
        candidates = [c for c in df.columns if c not in ("INDHOLD",) + (() if x_col is None else ("TID",))]
        cat_col = candidates[0] if candidates else None

        try:
            if x_col and cat_col:
                pv = df.pivot_table(index=x_col, columns=cat_col, values="INDHOLD", aggfunc="first")
                pv.sort_index(inplace=True)
                pv.plot(marker="o")
                plt.title(f"{table_id}: {cat_col} over {x_col}")
                plt.xlabel(x_col)
                plt.ylabel("INDHOLD")
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.show()
            elif x_col:
                grp = df.groupby(x_col)["INDHOLD"].first().sort_index()
                grp.plot(marker="o")
                plt.title(f"{table_id} over {x_col}")
                plt.xlabel(x_col)
                plt.ylabel("INDHOLD")
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.show()
            else:
                # Ingen TID — plotter bare INDHOLD som søjler over rækkeindeks
                s = df["INDHOLD"].reset_index(drop=True)
                s.plot(kind="bar")
                plt.title(f"{table_id} (ingen 'TID' fundet)")
                plt.xlabel("Observation")
                plt.ylabel("INDHOLD")
                plt.tight_layout()
                plt.show()
        except Exception as e:
            print("Kunne ikke generere plot:", e)

# ---------- Entry ----------
def main():
    lang = "da"
    if len(sys.argv) > 1:
        # Tillad f.eks. `python dst_cli.py en` for engelsk metadata
        lang = sys.argv[1].strip().lower()[:2]
    cli = DSTCLI(lang=lang)
    try:
        cli.main_menu()
    except KeyboardInterrupt:
        print("\nAfbrudt. På gensyn!")

if __name__ == "__main__":
    main()
