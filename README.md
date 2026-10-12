# STARS Observatory — Daily Data Archive

Companion archive for [STARS Observatory](https://starsobservatory.org) ([source](https://github.com/hallamburnapp-cloud/stars-observatory)).

Every hour, a scheduled workflow in this repository checks the observatory's deployed dataset. The first time it sees a new snapshot, it attaches it to the rolling [`data-archive`](https://github.com/hallamburnapp-cloud/stars-observatory-data/releases/tag/data-archive) release as `snapshot-YYYY-MM-DD.tar.gz` and lists it in [`snapshots.csv`](snapshots.csv) with its SHA-256 checksum. The observatory refreshes once a day, but GitHub can start scheduled runs hours late, so the archive does not assume a time of day.

- **Archived files are never replaced.** If a different dataset is later published under a date that is already archived, for example after a late re-run, it is kept alongside as `snapshot-YYYY-MM-DD-HHMMZ.tar.gz`, where HHMM is the time that dataset was fetched (UTC).
- **Coverage.** The archive starts on 23 September 2026. It has no file for 25 September 2026: under the earlier once-a-day schedule, that snapshot went live after the day's archive run and was replaced before the next one.

## Why

STARS Observatory's OSCOLA citation identifies the software by an archived, DOI-registered release and the evidence by a **data snapshot date**. The live site refreshes daily, so without this archive a cited snapshot would become irretrievable the next morning. Each `snapshot-YYYY-MM-DD.tar.gz` preserves the exact generated dataset behind that day's figures:

- `sats.json` — the propagated object population (element sets, ownership, registration join)
- `stats.json` — catalog-wide statistics (by type, owner, registration, constellation)
- `citation.json` — the citation manifest deployed that day (version, DOIs, snapshot date)

Snapshots made before STARS Observatory v1.8.0 also contain `national_law.json`, the national space legislation join, which was withdrawn from the instrument in v1.8.0.

## Retrieving a cited snapshot

If a source cites *STARS Observatory (version 1.6.0, data snapshot 23 September 2026 …)*, download `snapshot-2026-09-23.tar.gz` from the [data-archive release](https://github.com/hallamburnapp-cloud/stars-observatory-data/releases/tag/data-archive) to obtain the dataset behind every figure shown that day. To confirm that a download is the archived original, compare its SHA-256 checksum (for example `sha256sum snapshot-2026-09-23.tar.gz`) with the `sha256` column of [`snapshots.csv`](snapshots.csv). The `sats_generated` column gives the time the dataset was fetched (UTC).

## Licence

Generated data: [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) (attribution: Hallam Burnapp, STARS Observatory). Upstream sources retain their own terms: CelesTrak GP/SATCAT, Jonathan McDowell's GCAT (CC-BY), UNOOSA public documents.
