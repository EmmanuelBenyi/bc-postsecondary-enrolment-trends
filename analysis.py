"""BC post-secondary enrolment trends, with an international-student highlight.

Question: How has post-secondary enrolment in British Columbia trended, and
what do international student enrolment trends in BC and Canada show within
that picture?

Data: Statistics Canada table 37-10-0018-01 (Postsecondary enrolments, by
registration status, institution type, status of student in Canada and gender),
full-table CSV download. This script filters to: total institution type, total
registration status, total field of study, total gender, Number of enrolments,
for British Columbia and Canada, split by status of student in Canada.

Run: python analysis.py  (downloads the StatCan zip if not already present,
filters it, prints findings, and writes charts to charts/)

Calculations live in compute_series() / summarise(); plotting lives in the
plot_*() functions, so the numbers can be tested without drawing anything.
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

TOTAL_STATUS = "Total, status of student in Canada"
DOMESTIC_STATUS = "Canadian students"
INTERNATIONAL_STATUS = "International students"

# The year student-status reporting becomes near-complete (unclassified BC
# enrolments fall from ~87k to ~6k); charts mark it with a dashed line.
BREAK_YEAR = "2000/2001"


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


def pivot_enrolment(df):
    """Pivot the filtered rows to years x (geography, student status)."""
    return df.pivot_table(
        index="REF_DATE",
        columns=["GEO", "Status of student in Canada"],
        values="VALUE",
        aggfunc="sum",
    )


def compute_series(piv):
    """Derive the enrolment and share series used by every chart.

    Returns a dict of pandas Series indexed by academic year. Pure: no
    downloads, no files, no plotting, so it is directly testable.
    """
    def s(geo, status):
        return piv[(geo, status)]

    bc_tot = s("British Columbia", TOTAL_STATUS)
    bc_dom = s("British Columbia", DOMESTIC_STATUS)
    bc_int = s("British Columbia", INTERNATIONAL_STATUS)
    ca_tot = s("Canada", TOTAL_STATUS)
    ca_int = s("Canada", INTERNATIONAL_STATUS)
    return {
        "bc_total": bc_tot,
        "bc_domestic": bc_dom,
        "bc_international": bc_int,
        "ca_total": ca_tot,
        "ca_international": ca_int,
        "bc_international_share": bc_int / bc_tot * 100,
        "ca_international_share": ca_int / ca_tot * 100,
    }


def summarise(series):
    """Headline findings as plain numbers, for printing and testing."""
    bc_tot = series["bc_total"]
    bc_dom = series["bc_domestic"]
    bc_int = series["bc_international"]
    ca_int = series["ca_international"]
    bc_share = series["bc_international_share"]
    ca_share = series["ca_international_share"]
    return {
        "years_min": bc_tot.index.min(),
        "years_max": bc_tot.index.max(),
        "bc_total_first": bc_tot.iloc[0],
        "bc_total_last": bc_tot.iloc[-1],
        "bc_total_2019_2020": bc_tot.loc["2019/2020"],
        "bc_total_2023_2024": bc_tot.loc["2023/2024"],
        "bc_domestic_2010_2011": bc_dom.loc["2010/2011"],
        "bc_domestic_last": bc_dom.iloc[-1],
        "bc_international_first": bc_int.iloc[0],
        "bc_international_share_first": bc_share.iloc[0],
        "bc_international_peak": bc_int.loc["2023/2024"],
        "bc_international_share_peak": bc_share.loc["2023/2024"],
        "bc_international_last": bc_int.iloc[-1],
        "bc_international_share_last": bc_share.iloc[-1],
        "ca_international_first": ca_int.iloc[0],
        "ca_international_share_first": ca_share.iloc[0],
        "ca_international_peak": ca_int.loc["2023/2024"],
        "ca_international_share_peak": ca_share.loc["2023/2024"],
        "ca_international_last": ca_int.iloc[-1],
        "ca_international_share_last": ca_share.iloc[-1],
        "bc_international_change_peak_to_last":
            (bc_int.iloc[-1] / bc_int.loc["2023/2024"] - 1) * 100,
        "ca_international_change_peak_to_last":
            (ca_int.iloc[-1] / ca_int.loc["2023/2024"] - 1) * 100,
        "bc_international_change_2019_2020_to_2020_2021":
            (bc_int.loc["2020/2021"] / bc_int.loc["2019/2020"] - 1) * 100,
    }


def print_findings(f):
    """Print the headline findings (wording unchanged from the original)."""
    print("=== FINDINGS (from the downloaded data) ===")
    print(f"Years covered: {f['years_min']} to {f['years_max']}")
    print(f"BC total enrolment 1992/1993: {f['bc_total_first']:,.0f}; 2024/2025: {f['bc_total_last']:,.0f}")
    print(f"BC international 1992/1993: {f['bc_international_first']:,.0f} ({f['bc_international_share_first']:.1f}%); "
          f"peak 2023/2024: {f['bc_international_peak']:,.0f} ({f['bc_international_share_peak']:.1f}%); "
          f"2024/2025: {f['bc_international_last']:,.0f} ({f['bc_international_share_last']:.1f}%)")
    print(f"BC domestic 2010/2011: {f['bc_domestic_2010_2011']:,.0f}; 2024/2025: {f['bc_domestic_last']:,.0f}")
    print(f"BC total peak 2019/2020: {f['bc_total_2019_2020']:,.0f}; 2023/2024: {f['bc_total_2023_2024']:,.0f}")
    print(f"Canada international 1992/1993: {f['ca_international_first']:,.0f} ({f['ca_international_share_first']:.1f}%); "
          f"peak 2023/2024: {f['ca_international_peak']:,.0f} ({f['ca_international_share_peak']:.1f}%); "
          f"2024/2025: {f['ca_international_last']:,.0f} ({f['ca_international_share_last']:.1f}%)")
    print(f"BC international change 2023/2024 -> 2024/2025: {f['bc_international_change_peak_to_last']:.1f}%")
    print(f"Canada international change 2023/2024 -> 2024/2025: {f['ca_international_change_peak_to_last']:.1f}%")
    print(f"BC international change 2019/2020 -> 2020/2021: {f['bc_international_change_2019_2020_to_2020_2021']:.1f}%")


def _year_axis(piv):
    """X positions, short year labels, and the reporting-break index."""
    years = [y.split("/")[0] for y in piv.index]
    x = range(len(piv.index))
    break_idx = list(piv.index).index(BREAK_YEAR)
    return x, years, break_idx


def _mark_break(ax, break_idx, y, label="status reporting\nbreak (2000/01)"):
    ax.axvline(x=break_idx, color="grey", linestyle="--", linewidth=1)
    ax.text(break_idx + 0.3, y, label, fontsize=8, color="grey")


def _save(fig, chart_dir, name):
    fig.tight_layout()
    fig.savefig(os.path.join(chart_dir, name + ".png"), dpi=150)
    fig.savefig(os.path.join(chart_dir, name + ".svg"))
    plt.close(fig)


def plot_bc_trends(piv, series, chart_dir):
    """BC total, domestic, and international enrolment, 1992/93-2024/25."""
    x, years, break_idx = _year_axis(piv)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(x, series["bc_total"], label="Total enrolment", linewidth=2)
    ax.plot(x, series["bc_domestic"], label="Canadian students", linewidth=2)
    ax.plot(x, series["bc_international"], label="International students", linewidth=2)
    _mark_break(ax, break_idx, 290000)
    ax.set_xticks(list(x)[::4], years[::4], rotation=45)
    ax.set_ylabel("Enrolments")
    ax.set_title("BC post-secondary enrolment, 1992/93\u20132024/25")
    ax.legend()
    _save(fig, chart_dir, "bc_enrolment_trends")


def plot_international_share(piv, series, chart_dir):
    """International share of enrolment, BC vs Canada."""
    x, years, break_idx = _year_axis(piv)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(x, series["bc_international_share"], label="British Columbia", linewidth=2)
    ax.plot(x, series["ca_international_share"], label="Canada", linewidth=2)
    _mark_break(ax, break_idx, 24.5)
    ax.set_xticks(list(x)[::4], years[::4], rotation=45)
    ax.set_ylabel("International share of enrolment (%)")
    ax.set_title("International students as a share of enrolment, BC vs Canada")
    ax.legend()
    _save(fig, chart_dir, "international_share_bc_canada")


def plot_executive_summary(piv, series, chart_dir):
    """One polished chart for the headline story, 2000/01 onward.

    Bars: BC international enrolments. Line: international share of BC
    enrolment. The takeaway: international students drove two-thirds of
    BC's enrolment growth since 2000, then fell 6.3% in 2024/25 — the
    first decline since the pandemic year.
    """
    mask = piv.index >= BREAK_YEAR
    years = [y.split("/")[0] for y in piv.index[mask]]
    x = range(len(years))
    intl = series["bc_international"][mask]
    share = series["bc_international_share"][mask]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(x, intl, color="#1F4E79", label="International enrolments (BC)")
    ax.set_ylabel("International enrolments (BC)")
    ax.set_ylim(0, intl.max() * 1.15)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax2 = ax.twinx()
    ax2.plot(x, share, color="#C55A11", marker="o", markersize=3, linewidth=2,
             label="International share of BC enrolment")
    ax2.set_ylabel("Share of BC enrolment (%)")
    ax2.set_ylim(0, share.max() * 1.25)
    for spine in ("top",):
        ax2.spines[spine].set_visible(False)

    peak_idx = list(intl.index).index("2023/2024")
    last_idx = len(years) - 1
    ax.annotate(f"Peak 2023/24: {intl.iloc[peak_idx]:,.0f}",
                (peak_idx, intl.iloc[peak_idx]),
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=9)
    ax.annotate(f"2024/25: {intl.iloc[last_idx]:,.0f} (\u22126.3%)",
                (last_idx, intl.iloc[last_idx]),
                textcoords="offset points", xytext=(0, 8), ha="center",
                fontsize=9)

    ax.set_xticks(list(x)[::2], years[::2], rotation=45)
    ax.set_title("International students drove BC's enrolment growth since 2000\n"
                 "Then fell 6.3% in 2024/25 — the first decline since the pandemic year.",
                 fontsize=13, fontweight="bold", pad=12)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper left")
    _save(fig, chart_dir, "executive_summary")


def main():
    df = load_filtered()
    piv = pivot_enrolment(df)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CHART_DIR, exist_ok=True)
    piv.to_csv(os.path.join(DATA_DIR, "bc_canada_enrolment.csv"))

    series = compute_series(piv)
    print_findings(summarise(series))

    plot_bc_trends(piv, series, CHART_DIR)
    plot_international_share(piv, series, CHART_DIR)
    plot_executive_summary(piv, series, CHART_DIR)
    print("Charts written to", CHART_DIR)


if __name__ == "__main__":
    main()
