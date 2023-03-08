# Functions to call the podcast index
# Thanks to CSB for the start.


import hashlib
import logging
import os
from datetime import datetime
from time import time
from typing import Optional
from uuid import UUID

import httpx
import requests

# import xmltodict
from pydantic import Field
from pydantic.main import BaseModel
from pydantic.networks import AnyUrl
from requests import Response

# setup some basic vars for the search api.
# for more information, see https://api.podcastindex.org/developer_docs

# import config

PODCASTINDEX_KEY = os.getenv("PODCASTINDEX_KEY")
PODCASTINDEX_SECRET = os.getenv("PODCASTINDEX_SECRET")

pod_index_info = {
    "id": 1242604,
    "podcastGuid": "59f7a269-181a-5148-ae79-9f811ef43f27",
    "title": "The 1des 0f 1deas",
    "url": "https://anchor.fm/s/1d9c3020/podcast/rss",
    "originalUrl": "https://anchor.fm/s/1d9c3020/podcast/rss",
    "link": "https://anchor.fm/jeremy-bentham",
    "description": "Building action atop the abandoned, betrayed, and defiantly possible notions in the world. Support this podcast: https://anchor.fm/jeremy-bentham/support",
    "author": "Jeremy Bentham",
    "ownerName": "Jeremy Bentham",
    "image": "https://d3t3ozftmdmh3i.cloudfront.net/production/podcast_uploaded/4867752/4867752-1587326768375-aacd69d65df2.jpg",
    "artwork": "https://d3t3ozftmdmh3i.cloudfront.net/production/podcast_uploaded/4867752/4867752-1587326768375-aacd69d65df2.jpg",
    "lastUpdateTime": 1615797601,
    "lastCrawlTime": 1628030925,
    "lastParseTime": 1628030935,
}


class PodcastIndexInfo(BaseModel):
    feedID: int = Field(alias="id")
    guid: UUID = Field(alias="podcastGuid")
    podcast: str = Field(alias="title")
    url: AnyUrl
    originalUrl: Optional[AnyUrl]
    link: Optional[str]
    description: Optional[str]
    author: Optional[str]
    ownerName: Optional[str]
    image: Optional[str]
    artwork: Optional[str]
    lastUpdateTime: datetime
    lastCrawlTime: datetime
    lastParseTime: datetime


BASE_URL = "https://api.podcastindex.org/api/1.0/"
apiCalls = {
    "byterm": "search/byterm?q=",
    "byfeed": "podcasts/byfeedurl?url=",
    "byfeedid": "podcasts/byfeedid?id=",
    "recentfeeds": "recent/feeds",
    "epbyfeedurl": "episodes/byfeedurl?url=",
    "epbyfeedid": "episodes/byfeedid?id=",
    "epbyid": "episodes/byid?id=",
    "search": "search/byterm?q=",
    "episodes": "episodes/byid?id=",
    "valueurl": "value/byfeedurl?url=",
    "bytag": "podcasts/bytag?",
    "eprecent": "recent/episodes?",
    "addfeedurl": "add/byfeedurl?url=",
    "notifyurl": "hub/pubnotify?url=",
}


async def get_podcast_index_info(url: AnyUrl) -> PodcastIndexInfo:
    """Fetch the podcastindex information for a podcast based on URL"""
    headers = get_headers()
    url_to_call = BASE_URL + f"podcasts/byfeedurl"
    params = {"url": url}
    async with httpx.AsyncClient() as client:
        # logging.info(f"Fetching PodcastIndex info for url: {url}")
        response = await client.post(url_to_call, headers=headers, params=params)
        if response.status_code == 200 and response.json()["status"] == "true":
            ans = response.json()["feed"]
            if ans:
                return PodcastIndexInfo.parse_obj(ans)
        return None


def get_headers() -> dict:
    """Return the query headers"""

    # the api follows the Amazon style authentication
    # see https://docs.aws.amazon.com/AmazonS3/latest/dev/S3_Authentication2.html
    # we'll need the unix time
    api_key = PODCASTINDEX_KEY
    api_secret = PODCASTINDEX_SECRET
    epoch_time = int(time())

    # our hash here is the api key + secret + time
    data_to_hash = api_key + api_secret + str(epoch_time)
    # which is then sha-1'd
    sha_1 = hashlib.sha1(data_to_hash.encode()).hexdigest()

    # now we build our request headers
    headers = {
        "X-Auth-Date": str(epoch_time),
        "X-Auth-Key": api_key,
        "Authorization": sha_1,
        "User-Agent": "v4v.app",
    }
    return headers


def do_call(call, query):
    """Takes in a call type see apiCalls above and returns the request or False"""
    if call in apiCalls:
        url = BASE_URL + apiCalls[call] + query
        r = requests.post(url, headers=get_headers())
        return r
    else:
        r = Response()
        r.status_code = "404"
        return r


def get_episode(pi_ep_id):
    """Get info for one episode based on PodcastIndex Ep ID"""
    query = f"{pi_ep_id}"
    return do_call("episodes", query)


def do_recent(max=40, since="", lang="", cat="", nocat=""):
    """Get max recent podcasts"""
    query = f"?max={max}&cat={cat}&lang={lang}"
    return do_call("recentfeeds", query)


def do_search(term):
    query = f"{term}"
    return do_call("search", query)


def get_episodes(feedURL, maX=None):
    """Get max episodes from a feed"""
    if maX is not None:
        query = f"{feedURL}&max={maX}"
    else:
        query = f"{feedURL}"
    return do_call("epbyfeedurl", query)


def get_episode(idd):
    """Get specific episode by episode id"""
    query = f"{idd}"
    return do_call("epbyid", query)


def get_recent_ep(max):
    """Get recent episodes"""
    query = f"max={max}"
    return do_call("eprecent", query)


def get_pod_info_id(idd):
    """Gets info about the specific podcast by ID"""
    query = f"{idd}"
    return do_call("byfeedid", query)


def get_pod_info_url(pod_url):
    """Gets podcast info by URL"""
    return do_call("byfeed", pod_url)


def get_value_url(pod_url):
    """Return value blocks by URL"""
    return do_call("valueurl", pod_url)


def get_all_value():
    """Returns every value tag listed podcast"""
    return do_call("bytag", "podcast-value=true")


def get_pod_info_by_id(pi_id):
    ans = get_pod_info_id(pi_id).json()
    if ans.get("description") == "Found matching feeds.":
        return ans
    else:
        return None


def get_episode_info_by_id(pi_ep_id):
    ans = get_episode(pi_ep_id).json()
    if ans.get("description") == "Found matching item.":
        return ans
    else:
        return None


def get_pod_id_by_url(pod_url):
    ans = get_pod_info_url(pod_url)
    if ans.status_code == 200:
        return ans.json().get("feed").get("id")
    else:
        return None


# def getLockedPodcasterEmail(pod_url):
#     """Gets the owner email if the feed is locked"""
#     rss = requests.get(pod_url)
#     d = xmltodict.parse(rss.text)
#     try:
#         email = d["rss"]["channel"]["podcast:locked"]["@owner"]
#     except:
#         email = ""
#     if email == "":
#         try:
#             email = d["rss"]["channel"]["itunes:owner"]["itunes:email"]
#         except:
#             email = ""
#     return email


def get_episode_hash(pod_url, guid):
    """Return a hash of the pod_url and episode GUID for database"""
    id_and_guid = f"{pod_url}_{guid}"
    # m = hashlib.md5()
    m = hashlib.sha256()
    m.update(id_and_guid.encode())
    hashstr = m.hexdigest()
    return hashstr


# def get_valueblock_from_feed(pod_url):
#     """Gets the value block from an XML feed"""
#     rss = requests.get(pod_url)
#     d = xmltodict.parse(rss.text)
#     try:
#         ans = d.get("rss").get("channel").get("podcast:value")
#     except:
#         ans = {}
#     return ans


if __name__ == "__main__":
    pass
