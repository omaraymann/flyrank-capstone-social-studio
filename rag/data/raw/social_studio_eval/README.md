# Social Studio campaign source candidates

These official pages are a starter source collection for RAG and campaign-generation experiments. Their extracted text is stored beside this README as `.txt` files, with `corpus.jsonl` preserving title, publisher, canonical URL, retrieval date, and reuse notes. The pages remain the canonical sources.

## Science and public information: NASA

| ID | Source | Words | BGE chunks | Useful campaign/evaluation case |
|---|---|---:|---:|---|
| `tracers_launch_2025` | [NASA Launches Mission to Study Earth’s Magnetic Shield](https://www.nasa.gov/news-release/nasa-launches-mission-to-study-earths-magnetic-shield/) (July 23, 2025) | 1,121 | 8 | Mission launch, specific launch details, scientific purpose, and supporting payloads. Test whether drafts distinguish what launched from what the mission is expected to study. |
| `mars_potential_biosignature_2025` | [NASA Says Mars Rover Discovered Potential Biosignature Last Year](https://www.nasa.gov/news-release/nasa-says-mars-rover-discovered-potential-biosignature-last-year/) (September 10, 2025) | 1,074 | 8 | Strong uncertainty case. The article says the sample could preserve evidence of ancient microbial life and that non-biological explanations cannot be ruled out. Test whether a draft avoids claiming life was found. |
| `im2_partial_mission_2025` | [NASA Receives Some Data Before Intuitive Machines Ends Lunar Mission](https://www.nasa.gov/news-release/nasa-receives-some-data-before-intuitive-machines-ends-lunar-mission/) (March 7, 2025) | 845 | 7 | Mixed outcome and limitations. Some objectives were completed, while the mission ended early. Test whether the draft preserves both parts rather than presenting it as an unqualified success or failure. |
| `nisar_launch_2025` | [NASA-ISRO Satellite Lifts Off to Track Earth’s Changing Surfaces](https://www.nasa.gov/news-release/nasa-isro-satellite-lifts-off-to-track-earths-changing-surfaces/) (July 30, 2025) | 1,185 | 9 | International collaboration, measurements, and practical applications. Test exact numbers, units, and the difference between current capabilities and expected future benefits. |
| `x59_first_flight_2025` | [NASA’s X-59 Completes First Flight, Prepares for More Flight Testing](https://www.nasa.gov/centers-and-facilities/armstrong/nasas-x-59-completes-first-flight-prepares-for-more-flight-testing/) (November 19, 2025) | 1,222 | 8 | Milestone with important qualifiers: the first flight stayed below the speed of sound; supersonic tests and community response studies were future work. Test whether generation turns a future goal into a completed result. |

**NASA subset:** 5 documents, 5,447 extracted words, and 40 chunks with BGE-small, a 256-token limit, titles included, and one-sentence overlap.

Word counts use the article body after removing image figures/captions and contact details. Chunk counts use the current BGE tokenizer and our chunking code; they may change if the extraction or chunking rules change.

## Software releases and product announcements

| ID | Source | Campaign/evaluation case | Reuse note |
|---|---|---|---|
| `python_314_release` | [Python 3.14.0 release](https://www.python.org/downloads/release/python-3140/) (October 7, 2025) | Feature launch with several distinct changes. The page itself notes that 3.14.0 has since been superseded by 3.14.8, making it useful for testing release-date and version awareness. | Python documentation states its documentation is under the PSF License Version 2; preserve attribution and confirm page-specific terms before copying the release page. |
| `postgresql_18_release` | [PostgreSQL 18 Released!](https://www.postgresql.org/about/news/postgresql-18-released-3142/) (September 25, 2025) | Product release with performance claims that need their qualifiers, plus developer features, security details, and upgrade considerations. | The product's software license does not itself establish the license for this announcement text. Keep as a linked source unless page-content terms are confirmed. |

## Product, service, and community updates: Creative Commons

Creative Commons states that its website content is CC BY 4.0 unless otherwise marked. Keep author, date, source link, license, and any changes with each stored page. Check page-specific notices and keep logos or third-party material out of the text corpus.

| ID | Source | Campaign/evaluation case |
|---|---|---|
| `cc_chooser_refactor_part1` | [Refactoring and Releasing the new CC Chooser: Part 1](https://opensource.creativecommons.org/blog/entries/2025-07-11-refactoring-the-cc-chooser-pt-1/) (July 11, 2025) | Product release story with history, tradeoffs, and why the team changed direction. |
| `cc_chooser_refactor_part2` | [Refactoring and Releasing the new CC Chooser: Part 2](https://opensource.creativecommons.org/blog/entries/2025-10-06-refactoring-the-cc-chooser-pt-2/) (October 6, 2025) | Specific product and UX changes, including a reported 98% reduction in JavaScript and a separate estimate of effort; tests careful attribution of numbers and claims. |
| `cc_api_sunset_2026` | [Sunsetting api.creativecommons.org](https://opensource.creativecommons.org/blog/entries/2026-05-06-sunsetting-api/) (May 6, 2026) | Service shutdown with a firm future date, reasons, and migration alternatives. Good for deadline-preservation and action-oriented campaigns. |
| `cc_work_programs_2026` | [Deprioritizing work programs](https://opensource.creativecommons.org/blog/entries/2026-03-11-deprioritizing-work-programs/) (March 11, 2026) | Community program change: no plans to participate in future GSoC or Outreachy cycles, while expressing appreciation and continued support for their mission. |
| `cc_quantifying_commons_2026` | [Quantifying the Commons: The end of an era](https://opensource.creativecommons.org/blog/entries/2026-30-03-the-end-of-an-era/) (March 3, 2026) | Project milestone, contributor story, and next steps; useful for community and project-update campaigns. |

## How many to use first

The collection contains **12 downloaded documents, 12,816 words, and 94 passages** across three subject areas using BGE-small, a 256-token limit, titles, and one-sentence overlap. NASA pages are saved as article text without images; the other pages are saved as extracted page text. Run `python rag/scripts/download_social_sources.py` to refresh the corpus and its manifest. The PostgreSQL announcement is retained as a local research copy because page-content reuse terms were not confirmed; do not redistribute that text. For the first generation comparison, use a balanced subset across all three areas, with two campaign briefs per source. Expand toward 20–30 sources after labeling gold evidence passages.

## How to turn these into evaluation data

1. Use the extracted source text and its canonical URL, publisher, retrieval date, and reuse note in `corpus.jsonl`.
2. Create two or more campaign briefs per article in `generation_cases.jsonl`, varying audience and goal while keeping the source fixed.
3. Mark the exact evidence spans needed for each brief in `passage_qrels.tsv`. After applying the chosen chunker, map those spans to the chunks they overlap. Do not assume every unlabelled chunk is irrelevant.
4. Compare the current no-RAG drafts with RAG drafts using the same model and generation settings. Evaluate retrieval against the evidence labels, then compare supported, contradicted, and unsupported claims in the drafts.

Use this as a diverse starter catalog, then add more source organizations and campaign types before claiming the results generalize broadly.

## Reuse notes

Use these pages as attributed source material for offline development and evaluation. Before publishing generated campaigns externally, check the applicable page and media terms. Do not reuse page images, NASA insignia, or logos as campaign branding, and do not imply NASA endorsement. See [NASA’s media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) and [USAGov’s guidance on federal materials](https://www.usa.gov/government-copyright).
