#!/usr/bin/env python3
"""
CLI wrapper around Sprout Social’s code‑search API.
Communicates via StrongDM proxy.

Usage

# Through StrongDM proxy
$ ./btsearch.py -i "BusPublisher"
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Optional

SEARCH_ENDPOINT = "https://codesearcher.sproutsocial.sdm.network/search/results.json"


def build_opener(proxy: Optional[str] = None) -> urllib.request.OpenerDirector:
    """
    Return an urllib opener that honours *proxy* (format HOST:PORT).
    Falls back to no proxy if *proxy* is falsy.
    """
    if proxy:
        if not proxy.startswith(("http://", "https://")):
            proxy = "http://" + proxy  # urllib expects a scheme
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        return urllib.request.build_opener(handler)
    return urllib.request.build_opener()


def get_vcs_prefix(vcs_loc: str) -> str:
    mapping = {"bitbucket": "bb", "github": "gh"}
    try:
        return mapping[vcs_loc]
    except KeyError:
        raise ValueError(f"unknown vcs_loc: {vcs_loc}")


def as_text(obj) -> str:
    """Convert bytes → str safely, leave str unchanged."""
    return obj.decode("utf-8", errors="replace") if isinstance(obj, bytes) else str(obj)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Sprout Social’s code index and list the matches."
    )
    parser.add_argument("PATTERN", help="Regular expression to search for")
    parser.add_argument(
        "-i", "--ignore-case", help="Ignore case distinctions", action="store_true"
    )
    # parser.add_argument(
        # "--proxy",
        # metavar="HOST:PORT",
        # help="Send the HTTP(S) request through the given proxy",
    # )
    args = parser.parse_args()

    params = urllib.parse.urlencode(
        {
            "q": args.PATTERN,
            "case": "insensitive" if args.ignore_case else "sensitive",
        }
    )
    url = f"{SEARCH_ENDPOINT}?{params}"

    # opener = build_opener(
        # args.proxy
        # or os.getenv("HTTP_PROXY")
        # or os.getenv("http_proxy")
        # or os.getenv("HTTPS_PROXY")
        # or os.getenv("https_proxy")
    # )
    opener = build_opener("localhost:65230")

    try:
        with opener.open(url, timeout=30) as resp:
            payload = resp.read()
    except urllib.error.URLError as exc:
        sys.stderr.write(f"error: request failed — {exc}\n")
        sys.stderr.write("are you sure you're connected to StrongDM (sdm login && sdm connect --all) and the VPN?\n")
        sys.exit(2)

    # ...
    results = json.loads(payload).get("data", {}).get("results") or {}
    if not results:
        print("no results found.")
        sys.exit(1)

    for repo in sorted(results):
        # strip leading "sproutsocial/" when present
        repo_display = repo.split("/", 1)[1] if repo.startswith("sproutsocial/") else repo

        for vcs_loc, repo_dict in results[repo].items():
            for file in sorted(repo_dict.get("files", {})):
                for hit in repo_dict["files"][file]:
                    if (src := hit.get("srcline")) is None or (ln := hit.get("lineno")) is None:
                        continue
                    print(
                        f"{get_vcs_prefix(vcs_loc)}:"
                        f"{repo_display}:"
                        f"{as_text(file)}:"
                        f"{ln}:"
                        f"{as_text(src).rstrip()}"
                    )

if __name__ == "__main__":
    main()

