




from __future__ import annotations

SECTIONS: dict[str, dict] = {
    "us": {
        "name": "US Competitions",
        "blurb": "AMC 8/10/12, AIME, USAJMO, and USAMO past papers.",
        "source_note": "Problems and answer keys open on the AoPS Wiki, because the MAA does not publish free past papers and its problems may not be copied.",
        "links": [
            {"label": "MAA American Mathematics Competitions", "url": "https://maa.org/student-programs/amc/"},
            {"label": "AoPS Wiki contest archive", "url": "https://artofproblemsolving.com/wiki/index.php/AMC_Problems_and_Solutions"},
        ],
        "contests": {
            "amc8": "AMC 8",
            "amc10": "AMC 10",
            "amc12": "AMC 12",
            "aime": "AIME",
            "usajmo": "USAJMO",
            "usamo": "USAMO",
        },
    },
    "canada": {
        "name": "Canada Competitions",
        "blurb": "CEMC contests (Gauss, Euclid…), COMC, CJMO, and CMO.",
        "source_note": "CEMC papers are copies of the originals by the Centre for Education in Mathematics and Computing, University of Waterloo, shared under the CC BY-NC 4.0 licence. COMC, CJMO, and CMO papers open on the CMS website, because the CMS allows personal copies only.",
        "links": [
            {"label": "CEMC past contests", "url": "https://cemc.uwaterloo.ca/resources/past-contests"},
            {"label": "CMS competitions", "url": "https://cms.math.ca/competitions/"},
            {"label": "CC BY-NC 4.0 licence", "url": "https://creativecommons.org/licenses/by-nc/4.0/"},
        ],
        "contests": {
            "gauss": "Gauss",
            "pcf": "Pascal / Cayley / Fermat",
            "fgh": "Fryer / Galois / Hypatia",
            "euclid": "Euclid",
            "csimc": "CSIMC",
            "comc": "COMC",
            "cjmo": "CJMO",
            "cmo": "CMO",
        },
    },
    "ib": {
        "name": "IB Math",
        "blurb": "Math AA and AI, SL and HL, plus IA resources.",
        "source_note": "IB past papers are copyrighted and sold by the IBO, so this section only has files shared by our admins.",
        "links": [
            {"label": "IB Diploma Programme mathematics", "url": "https://www.ibo.org/programmes/diploma-programme/curriculum/mathematics/"},
            {"label": "Follett IB Store (sells IB past papers)", "url": "https://www.follettibstore.com/"},
        ],
        "contests": {
            "aa_sl": "Math AA SL",
            "aa_hl": "Math AA HL",
            "ai_sl": "Math AI SL",
            "ai_hl": "Math AI HL",
            "ia": "IA",
        },
    },
    "ossd": {
        "name": "OSSD Math",
        "blurb": "Ontario high school math, from MTH1W to MCV4U.",
        "source_note": "Ontario has no public provincial math exams, so this section only has files shared by our admins.",
        "links": [
            {"label": "Ontario mathematics curriculum", "url": "https://www.dcp.edu.gov.on.ca/en/curriculum"},
        ],
        "contests": {
            "mth1w": "MTH1W (Grade 9)",
            "mpm2d": "MPM2D (Grade 10)",
            "mcr3u": "MCR3U (Grade 11)",
            "mcf3m": "MCF3M (Grade 11)",
            "mhf4u": "MHF4U (Grade 12)",
            "mcv4u": "MCV4U (Grade 12)",
            "mdm4u": "MDM4U (Grade 12)",
        },
    },
}


KINDS: dict[str, str] = {
    "problems": "Problems",
    "solutions": "Solutions",
    "answers": "Answer key",
    "results": "Results",
    "notes": "Notes",
    "other": "Other",
}


QA_TOPICS: dict[str, str] = {
    "general": "General",
    "us": "US",
    "canada": "Canada",
    "ib": "IB",
    "ossd": "OSSD",
}


SOURCES: dict[str, str] = {
    "upload": "Uploaded",
    "aops": "AoPS Wiki",
    "cemc": "CEMC",
    "cms": "CMS",
}


def is_valid(section: str, contest: str | None = None) -> bool:
    if section not in SECTIONS:
        return False
    return contest is None or contest in SECTIONS[section]["contests"]


def public_catalog() -> dict:

    return {
        "sections": {
            key: {
                "name": s["name"],
                "blurb": s["blurb"],
                "source_note": s["source_note"],
                "links": s["links"],
                "contests": [{"key": k, "name": n} for k, n in s["contests"].items()],
            }
            for key, s in SECTIONS.items()
        },
        "kinds": [{"key": k, "name": n} for k, n in KINDS.items()],
        "sources": SOURCES,
    }
