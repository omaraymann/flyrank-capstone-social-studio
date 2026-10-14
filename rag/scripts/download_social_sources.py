"""Download the public campaign-source pages into data/raw/social_studio_eval."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

OUTPUT = Path(__file__).resolve().parents[1] / "data/raw/social_studio_eval"
SOURCES = [
    ("tracers_launch_2025", "NASA Launches Mission to Study Earth’s Magnetic Shield", "https://www.nasa.gov/news-release/nasa-launches-mission-to-study-earths-magnetic-shield/", "NASA public information; retain source attribution; third-party material excluded"),
    ("mars_potential_biosignature_2025", "NASA Says Mars Rover Discovered Potential Biosignature Last Year", "https://www.nasa.gov/news-release/nasa-says-mars-rover-discovered-potential-biosignature-last-year/", "NASA public information; retain source attribution; third-party material excluded"),
    ("im2_partial_mission_2025", "NASA Receives Some Data Before Intuitive Machines Ends Lunar Mission", "https://www.nasa.gov/news-release/nasa-receives-some-data-before-intuitive-machines-ends-lunar-mission/", "NASA public information; retain source attribution; third-party material excluded"),
    ("nisar_launch_2025", "NASA-ISRO Satellite Lifts Off to Track Earth’s Changing Surfaces", "https://www.nasa.gov/news-release/nasa-isro-satellite-lifts-off-to-track-earths-changing-surfaces/", "NASA public information; retain source attribution; third-party material excluded"),
    ("x59_first_flight_2025", "NASA’s X-59 Completes First Flight, Prepares for More Flight Testing", "https://www.nasa.gov/centers-and-facilities/armstrong/nasas-x-59-completes-first-flight-prepares-for-more-flight-testing/", "NASA public information; retain source attribution; third-party material excluded"),
    ("python_314_release", "Python 3.14.0 release", "https://www.python.org/downloads/release/python-3140/", "Python documentation: PSF License Version 2; retain attribution"),
    ("postgresql_18_release", "PostgreSQL 18 Released!", "https://www.postgresql.org/about/news/postgresql-18-released-3142/", "PostgreSQL announcement; local research copy; terms not confirmed; do not redistribute"),
    ("cc_chooser_refactor_part1", "Refactoring and Releasing the new CC Chooser: Part 1", "https://opensource.creativecommons.org/blog/entries/2025-07-11-refactoring-the-cc-chooser-pt-1/", "Creative Commons website content: CC BY 4.0 unless otherwise marked"),
    ("cc_chooser_refactor_part2", "Refactoring and Releasing the new CC Chooser: Part 2", "https://opensource.creativecommons.org/blog/entries/2025-10-06-refactoring-the-cc-chooser-pt-2/", "Creative Commons website content: CC BY 4.0 unless otherwise marked"),
    ("cc_api_sunset_2026", "Sunsetting api.creativecommons.org", "https://opensource.creativecommons.org/blog/entries/2026-05-06-sunsetting-api/", "Creative Commons website content: CC BY 4.0 unless otherwise marked"),
    ("cc_work_programs_2026", "Deprioritizing work programs", "https://opensource.creativecommons.org/blog/entries/2026-03-11-deprioritizing-work-programs/", "Creative Commons website content: CC BY 4.0 unless otherwise marked"),
    ("cc_quantifying_commons_2026", "Quantifying the Commons: The end of an era", "https://opensource.creativecommons.org/blog/entries/2026-30-03-the-end-of-an-era/", "Creative Commons website content: CC BY 4.0 unless otherwise marked"),
]


def fetch(source):
    request = Request(source[2], headers={"User-Agent": "FlyRank-Social-Studio/1.0 (offline campaign research)"})
    with urlopen(request, timeout=30) as response:
        raw = response.read(5_000_001)
        if len(raw) > 5_000_000:
            raise ValueError("page exceeds 5 MB")
        html = raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "aside", "figure", "noscript", "svg"]):
        element.decompose()
    candidates = soup.find_all(["article", "main"])
    candidates.extend(soup.select("[role='main']"))
    article = max(candidates, key=lambda item: len(item.get_text(" ", strip=True))) if candidates else soup.body
    text = "\n".join(line.strip() for line in article.get_text("\n").splitlines() if line.strip()) if article else ""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 100:
        raise ValueError("could not extract article text from article/main page content")
    if len(text) < 100:
        raise ValueError("could not extract article text")
    return text[:100_000]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    for item in SOURCES:
        identifier, title, url, reuse = item
        path = OUTPUT / f"{identifier}.txt"
        try:
            if path.exists() and path.stat().st_size > 100 and not path.read_text(encoding="utf-8", errors="ignore").lstrip().startswith("var gform"):
                text = path.read_text(encoding="utf-8")
            else:
                text = fetch(item)
                path.write_text(text + "\n", encoding="utf-8")
            records.append({"_id": identifier, "title": title, "text": text, "metadata": {
                "source_url": url, "publisher": "NASA" if "nasa.gov" in url else "Python Software Foundation" if "python.org" in url else "PostgreSQL Global Development Group" if "postgresql.org" in url else "Creative Commons",
                "retrieved_date": date.today().isoformat(), "reuse_notes": reuse, "local_text_file": path.name,
            }})
            print(f"Downloaded {identifier}: {len(text.split())} words")
        except Exception as exc:
            print(f"FAILED {identifier}: {exc}")
    (OUTPUT / "corpus.jsonl").write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    print(f"Saved {len(records)} documents to {OUTPUT}")


if __name__ == "__main__":
    main()
