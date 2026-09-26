# STARS Observatory — Daily Data Archive

Companion archive for [STARS Observatory](https://starsobservatory.org) ([source](https://github.com/hallamburnapp-cloud/stars-observatory)).

Every day at 06:30 UTC, after the observatory's 06:00 UTC data refresh, a scheduled workflow in this repository downloads the deployed datasets and attaches them to the rolling [`data-archive`](https://github.com/hallamburnapp-cloud/stars-observatory-data/releases/tag/data-archive) release as `snapshot-YYYY-MM-DD.tar.gz`.

## Why

STARS Observatory's OSCOLA citation identifies the software by an archived, DOI-registered release and the evidence by a **data snapshot date**. The live site refreshes daily, so without this archive a cited snapshot would become irretrievable the next morning. Each `snapshot-YYYY-MM-DD.tar.gz` preserves the exact generated dataset behind that day's figures:

- `sats.json` — the propagated object population (element sets, ownership, registration join)
- `stats.json` — catalog-wide statistics (by type, owner, registration, constellation)
- `citation.json` — the citation manifest deployed that day (version, DOIs, snapshot date)

Snapshots made before STARS Observatory v1.8.0 also contain `national_law.json`, the national space legislation join, which was withdrawn from the instrument in v1.8.0.

## Retrieving a cited snapshot

If a source cites *STARS Observatory (version 1.6.0, data snapshot 23 September 2026 …)*, download `snapshot-2026-09-23.tar.gz` from the [data-archive release](https://github.com/hallamburnapp-cloud/stars-observatory-data/releases/tag/data-archive) to obtain the dataset behind every figure shown that day.

## Licence

Generated data: [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) (attribution: Hallam Burnapp, STARS Observatory). Upstream sources retain their own terms: CelesTrak GP/SATCAT, Jonathan McDowell's GCAT (CC-BY), UNOOSA public documents.
