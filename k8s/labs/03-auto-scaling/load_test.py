import time
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen

URL = "http://localhost:8080/predict"
PAYLOAD = {"features": [5.1, 3.5, 1.4, 0.2]}


def send_one() -> None:
    body = json.dumps(PAYLOAD).encode("utf-8")
    req = Request(URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=3):
        pass


def main() -> None:
    seconds = 20
    workers = 40
    start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(send_one) for _ in range(seconds * workers)]
        for f in futures:
            f.result()
    elapsed = time.time() - start
    print(f"{len(futures) / elapsed:.2f} req/s")


if __name__ == "__main__":
    main()
