#!/usr/bin/env python3
"""Archive the STARS Observatory snapshot that is live now, unless it is archived already.

Run every hour by .github/workflows/archive.yml. The observatory refreshes once a
day, but GitHub can start its scheduled run hours late, so the archive assumes no
time of day: it checks the deployed dataset and archives each snapshot the first
time it sees it.

Rules
- An archived file is never replaced: uploads never overwrite, and GitHub refuses
  an upload whose name already exists.
- A snapshot is identified by its dataset timestamp: the "generated" field of
  stats.json (sats.json carries its own timestamp from the same build).
- The first dataset of a date is archived as snapshot-YYYY-MM-DD.tar.gz. A
  different dataset published later under the same date (for example after a
  late re-run) is kept alongside as snapshot-YYYY-MM-DD-HHMMZ.tar.gz, HHMM being
  the time the dataset was fetched (UTC).
- Every archived file is listed in snapshots.csv with its SHA-256 checksum. The
  workflow commits that file, which is also repository activity, so GitHub never
  switches off this schedule (it does so after 60 days without commits).

Usage:
  archive.py                 archive the live snapshot if needed and update snapshots.csv
  archive.py --dry-run       report what would happen; upload and write nothing
  archive.py --rebuild-index rebuild snapshots.csv from the files already in the release
"""
import csv, gzip, hashlib, io, json, os, sys, tarfile, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime

REPO = os.environ.get("GITHUB_REPOSITORY", "hallamburnapp-cloud/stars-observatory-data")
LIVE = "https://starsobservatory.org/data/"
TAG = "data-archive"
INDEX = "snapshots.csv"
FIELDS = ["file", "snapshot_date", "sats_generated", "stats_generated", "sha256", "archived_utc"]
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
# The release description; the workflow keeps the live release in step with it.
NOTES = ("Rolling archive of STARS Observatory's generated daily datasets. Each snapshot-YYYY-MM-DD.tar.gz is the "
         "exact dataset behind the OSCOLA citation's 'data snapshot' date for that day (sats, stats, citation "
         "manifest; snapshots made before v1.8.0 also contain the withdrawn national-law join). Archived files are "
         "never replaced: a different dataset published later under an archived date is kept alongside as "
         "snapshot-YYYY-MM-DD-HHMMZ.tar.gz. snapshots.csv in the repository lists every file with its SHA-256 "
         "checksum. Generated data: CC-BY 4.0.")
UA = {"User-Agent": "stars-observatory-archive"}


def request(url, data=None, headers=None, method=None, tries=3):
    """GET (or send) with retries on network errors and 5xx; 4xx raise at once."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})}, method=method)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        if i + 1 < tries:
            time.sleep(30 * (i + 1))
    raise last


def api(path, data=None, method=None, content_type="application/json", host="api.github.com"):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if data is not None:
        headers["Content-Type"] = content_type
    return json.loads(request(f"https://{host}/{path}", data=data, headers=headers, method=method) or b"null")


def live(name):
    # A unique query string bypasses the CDN cache, so a fresh deploy is seen at once.
    return request(f"{LIVE}{name}?archive={int(time.time())}")


def member(tar_bytes, name):
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as t:
        m = next(m for m in t.getmembers() if os.path.basename(m.name) == name)
        return json.load(t.extractfile(m))


def row_for(name, data, archived):
    sats_gen, stats_gen = member(data, "sats.json")["generated"], member(data, "stats.json")["generated"]
    return {"file": name, "snapshot_date": sats_gen[:10], "sats_generated": sats_gen, "stats_generated": stats_gen,
            "sha256": hashlib.sha256(data).hexdigest(), "archived_utc": archived}


def read_index():
    if not os.path.exists(INDEX):
        return []
    with open(INDEX, newline="") as f:
        return list(csv.DictReader(f))


def write_index(rows):
    rows = sorted(rows, key=lambda r: (r["snapshot_date"], r["file"]))
    with open(INDEX, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def build_tar(files, generated):
    """A reproducible tar.gz: fixed order, owner and times, so its checksum depends only on the data."""
    mtime = int(datetime.fromisoformat(generated.replace("Z", "+00:00")).timestamp())
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as t:
        for name in ("sats.json", "stats.json", "citation.json"):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode, info.uid, info.gid = len(files[name]), mtime, 0o644, 0, 0
            t.addfile(info, io.BytesIO(files[name]))
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


def release(dry):
    try:
        return api(f"repos/{REPO}/releases/tags/{TAG}")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    if dry:
        print(f"Would create the {TAG} release.")
        return {"id": None}
    return api(f"repos/{REPO}/releases", json.dumps({"tag_name": TAG, "name": "Daily data snapshots", "body": NOTES}).encode(), "POST")


def assets_of(rel):
    if not rel.get("id"):
        return {}
    out, page = {}, 1
    while True:
        batch = api(f"repos/{REPO}/releases/{rel['id']}/assets?per_page=100&page={page}")
        out.update({a["name"]: a for a in batch})
        if len(batch) < 100:
            return out
        page += 1


def output(key, value):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"{key}={value}\n")


def archive_once(dry):
    """Returns 'done' or 'changed' (the site was redeployed while it was being read)."""
    rel = release(dry)
    if rel.get("id") and rel.get("body") != NOTES:
        if dry:
            print("Would update the release description to match the archive's rules.")
        else:
            api(f"repos/{REPO}/releases/{rel['id']}", json.dumps({"body": NOTES}).encode(), "PATCH")
            print("Updated the release description to match the archive's rules.")
    assets = assets_of(rel)
    index = read_index()
    gen = json.loads(live("stats.json"))["generated"]
    date = gen[:10]
    print(f"Live snapshot {date}, dataset generated {gen}")
    hit = next((r for r in index if r["stats_generated"] == gen), None)
    if hit:
        print(f"Already archived as {hit['file']}.")
        return "done"
    # A file of this date already in the release but missing from the index (for example
    # after a failed commit) is added to the index, never uploaded again.
    for name, a in sorted(assets.items()):
        if name.startswith(f"snapshot-{date}") and name.endswith(".tar.gz") and name not in {r["file"] for r in index}:
            data = request(a["browser_download_url"])
            if member(data, "stats.json")["generated"] == gen:
                print(f"Already archived as {name}; adding it to {INDEX}.")
                if not dry:
                    write_index(index + [row_for(name, data, a["updated_at"])])
                    output("archived", name)
                return "done"
    files = {n: live(n) for n in ("sats.json", "stats.json", "citation.json")}
    sats_gen = json.loads(files["sats.json"])["generated"]
    stats_gen = json.loads(files["stats.json"])["generated"]
    span = abs(datetime.fromisoformat(sats_gen.replace("Z", "+00:00")) - datetime.fromisoformat(stats_gen.replace("Z", "+00:00")))
    if stats_gen != gen or span.total_seconds() > 300 or sats_gen[:10] != date:
        print(f"The site changed while it was being read (stats {stats_gen}, sats {sats_gen}).")
        return "changed"
    name = f"snapshot-{date}.tar.gz"
    if name in assets:
        name = f"snapshot-{date}-{sats_gen[11:16].replace(':', '')}Z.tar.gz"
        print(f"{date} is already archived with a different dataset; this one is kept alongside as {name}.")
        if name in assets:
            sys.exit(f"::error::{name} already exists and holds a different dataset; nothing was replaced.")
    data = build_tar(files, sats_gen)
    if dry:
        print(f"Would archive {name}: {len(data):,} bytes, sha256 {hashlib.sha256(data).hexdigest()}")
        return "done"
    q = urllib.parse.quote(name)
    asset = api(f"repos/{REPO}/releases/{rel['id']}/assets?name={q}", data, "POST", "application/gzip", host="uploads.github.com")
    write_index(index + [row_for(name, data, asset["updated_at"])])
    output("archived", name)
    print(f"Archived {name} ({len(data):,} bytes).")
    return "done"


def main():
    args = set(sys.argv[1:])
    dry = "--dry-run" in args
    if "--rebuild-index" in args:
        rows = [row_for(n, request(a["browser_download_url"]), a["updated_at"])
                for n, a in sorted(assets_of(release(True)).items()) if n.startswith("snapshot-") and n.endswith(".tar.gz")]
        write_index(rows)
        print(f"{INDEX}: {len(rows)} files")
        return
    if archive_once(dry) == "changed":
        time.sleep(90)
        if archive_once(dry) == "changed":
            sys.exit("::error::The site kept changing while it was being read; nothing was archived.")


if __name__ == "__main__":
    main()
