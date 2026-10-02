import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs

URL = "http://127.0.0.1:8000/buy/"


def buy(i):
    data = f"user_id=shopper{i}".encode()
    resp = urllib.request.urlopen(urllib.request.Request(URL, data=data))
    return parse_qs(urlparse(resp.geturl()).query)["msg"][0]


with ThreadPoolExecutor(max_workers=50) as pool:
    results = Counter(pool.map(buy, range(200)))

print(results)