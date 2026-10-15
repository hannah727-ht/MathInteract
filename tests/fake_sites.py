




from pathlib import Path
from urllib.error import URLError

FIXTURES = Path(__file__).parent / "fixtures"
CEMC_PAGES = {13: "cemc_gauss_page0.html", 14: "cemc_pcf_page0.html", 23: "cemc_csimc_page0.html"}
EMPTY_TABLE = "<table><tbody></tbody></table>"

class FakeFetcher:
    def __init__(self, fail_downloads=(), broken=False, cemc_year_filter=False):
        self.cemc_year_filter = cemc_year_filter
        self.fail_downloads = set(fail_downloads)
        self.broken = broken
        self.requests: list[tuple[str, dict | None]] = []
        self.downloads: list[str] = []

    def text(self, url, params=None):
        self.requests.append((url, params))
        if self.broken:
            raise URLError("site down")
        if url.endswith("/resources/past-contests"):
            category, year = params["contest_category"], params.get("academic_year")
            if category == 14 and self.cemc_year_filter:
                if year is None:
                    return (FIXTURES / "cemc_pcf_page0_with_years.html").read_text() if params["page"] == 0 else EMPTY_TABLE
                name = {"31": "cemc_pcf_2023.html", "34": "cemc_pcf_2020.html"}.get(year)
                return (FIXTURES / name).read_text() if name and params["page"] == 0 else EMPTY_TABLE
            name = CEMC_PAGES.get(category)
            return (FIXTURES / name).read_text() if name and params["page"] == 0 else EMPTY_TABLE
        if url == "https://cms.math.ca/competitions/cmo/":
            return (FIXTURES / "cms_cmo.html").read_text()
        if url == "https://cms.math.ca/competitions/comc/":
            return (FIXTURES / "cms_comc_index.html").read_text()
        if url.startswith("https://cms.math.ca/competitions/comc/comc"):
            return (FIXTURES / f"cms_{url.rstrip('/').rsplit('/', 1)[-1]}.html").read_text()
        raise AssertionError(f"unexpected page {url}")

    def download(self, url, dest, max_bytes):
        self.downloads.append(url)
        if url in self.fail_downloads:
            raise URLError("broken link")
        content = b"%PDF-1.4 copy of " + url.encode()
        dest.write_bytes(content)
        return len(content)
