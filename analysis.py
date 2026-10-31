"""BC post-secondary enrolment trends, with an international-student highlight.

Question: How have post-secondary admissions and enrolment in British Columbia
trended, and what do international student enrolment trends in BC and Canada
show within that picture?

Data: Statistics Canada table 37-10-0018-01 (Postsecondary enrolments, by
registration status, institution type, status of student in Canada and gender),
full-table CSV download. This script filters to: total institution type, total
registration status, total field of study, total gender, Number of enrolments,
for British Columbia and Canada, split by status of student in Canada.

Run: python analysis.py  (downloads the StatCan zip if not already present,
filters it, prints findings, and writes charts to charts/)
"""
import os
import zipfile
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SCRATCH = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRATCH, "data")
CHART_DIR = os.path.join(SCRATCH, "charts")
ZIP_URL = "https://www150.statcan.gc.ca/n1/tbl/csv/37100018-eng.zip"
ZIP_PATH = os.path.join(SCRATCH, "statcan_37100018.zip")
CSV_NAME = "37100018.csv"

KEEP_GEO = {"British Columbia", "Canada"}
KEEP_STATUS = {
    "Total, status of student in Canada",
    "Canadian students",
    "International students",
}


def load_filtered():
    if not os.path.exists(ZIP_PATH):
        print("Downloading StatCan table 37-10-0018-01 ...")
        urllib.request.urlretrieve(ZIP_URL, ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        with zf.open(CSV_NAME) as fh:
            chunks = []
            for ch in pd.read_csv(
                fh,
                usecols=[
                    "REF_DATE", "GEO", "Institution type",
                    "Registration status",
                    "International Standard Classification of Education (ISCED)",
                    "Field of study", "Gender",
                    "Status of student in Canada", "Selected statistics", "VALUE",
                ],
                chunksize=500_000,
                low_memory=False,
            ):
                m = (
                    ch["GEO"].isin(KEEP_GEO)
                    & (ch["Institution type"] == "Total, institution type")
                    & (ch["Registration status"] == "Total, registration status")
                    & (ch["International Standard Classification of Education (ISCED)"]
                       == "Total, International Standard Classification of Education (ISCED)")
                    & (ch["Field of study"] == "Total, field of study")
                    & (ch["Gender"] == "Total, gender")
                    & ch["Status of student in Canada"].isin(KEEP_STATUS)
                    & (ch["Selected statistics"] == "Number")
                )
                chunks.append(ch[m])
    df = pd.concat(chunks, ignore_index=True)
    df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
    return df.dropna(subset=["VALUE"])


def main():
    df = load_filtered()
    piv = df.pivot_table(
        index="REF_DATE",
        columns=["GEO", "Status of student in Canada"],
        values="VALUE",
        aggfunc="sum",
    )
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CHART_DIR, exist_ok=True)
    piv.to_csv(os.path.join(DATA_DIR, "bc_canada_enrolment.csv"))

    def s(geo, status):
        return piv[(geo, status)]

    bc_tot, bc_dom, bc_int = s("British Columbia", "Total, status of student in Canada"), \
        s("British Columbia", "Canadian students"), s("British Columbia", "International students")
    ca_tot, ca_int = s("Canada", "Total, status of student in Canada"), \
        s("Canada", "International students")
    bc_share = bc_int / bc_tot * 100
    ca_share = ca_int / ca_tot * 100

    print("=== FINDINGS (from the downloaded data) ===")
    print(f"Years covered: {piv.index.min()} to {piv.index.max()}")
    print(f"BC total enrolment 1992/1993: {bc_tot.iloc[0]:,.0f}; 2024/2025: {bc_tot.iloc[-1]:,.0f}")
    print(f"BC international 1992/1993: {bc_int.iloc[0]:,.0f} ({bc_share.iloc[0]:.1f}%); "
          f"peak 2023/2024: {bc_int.loc['2023/2024']:,.0f} ({bc_share.loc['2023/2024']:.1f}%); "
          f"2024/2025: {bc_int.iloc[-1]:,.0f} ({bc_share.iloc[-1]:.1f}%)")
    print(f"BC domestic 2010/2011: {bc_dom.loc['2010/2011']:,.0f}; 2024/2025: {bc_dom.iloc[-1]:,.0f}")
    print(f"BC total peak 2019/2020: {bc_tot.loc['2019/2020']:,.0f}; 2023/2024: {bc_tot.loc['2023/2024']:,.0f}")
    print(f"Canada international 1992/1993: {ca_int.iloc[0]:,.0f} ({ca_share.iloc[0]:.1f}%); "
          f"peak 2023/2024: {ca_int.loc['2023/2024']:,.0f} ({ca_share.loc['2023/2024']:.1f}%); "
          f"2024/2025: {ca_int.iloc[-1]:,.0f} ({ca_share.iloc[-1]:.1f}%)")
    print(f"BC international change 2023/2024 -> 2024/2025: {(bc_int.iloc[-1]/bc_int.loc['2023/2024']-1)*100:.1f}%")
    print(f"Canada international change 2023/2024 -> 2024/2025: {(ca_int.iloc[-1]/ca_int.loc['2023/2024']-1)*100:.1f}%")
    print(f"BC international change 2019/2020 -> 2020/2021: {(bc_int.loc['2020/2021']/bc_int.loc['2019/2020']-1)*100:.1f}%")

    years = [y.split("/")[0] for y in piv.index]
    x = range(len(piv.index))
    # Index of 2000/2001: the year student-status reporting becomes
    # near-complete (unclassified BC enrolments fall from ~87k to ~6k).
    break_idx = list(piv.index).index("2000/2001")

    plt.figure(figsize=(10, 5.5))
    plt.plot(x, bc_tot, label="Total enrolment", linewidth=2)
    plt.plot(x, bc_dom, label="Canadian students", linewidth=2)
    plt.plot(x, bc_int, label="International students", linewidth=2)
    plt.axvline(x=break_idx, color="grey", linestyle="--", linewidth=1)
    plt.text(break_idx + 0.3, 290000, "status reporting\nbreak (2000/01)",
             fontsize=8, color="grey")
    plt.xticks(list(x)[::4], years[::4], rotation=45)
    plt.ylabel("Enrolments")
    plt.title("BC post-secondary enrolment, 1992/93\u20132024/25")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_DIR, "bc_enrolment_trends.png"), dpi=150)
    plt.savefig(os.path.join(CHART_DIR, "bc_enrolment_trends.svg"))
    plt.close()

    plt.figure(figsize=(10, 5.5))
    plt.plot(x, bc_share, label="British Columbia", linewidth=2)
    plt.plot(x, ca_share, label="Canada", linewidth=2)
    plt.axvline(x=break_idx, color="grey", linestyle="--", linewidth=1)
    plt.text(break_idx + 0.3, 24.5, "status reporting\nbreak (2000/01)",
             fontsize=8, color="grey")
    plt.xticks(list(x)[::4], years[::4], rotation=45)
    plt.ylabel("International share of enrolment (%)")
    plt.title("International students as a share of enrolment, BC vs Canada")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_DIR, "international_share_bc_canada.png"), dpi=150)
    plt.savefig(os.path.join(CHART_DIR, "international_share_bc_canada.svg"))
    plt.close()
    print("Charts written to", CHART_DIR)


if __name__ == "__main__":
    main()
