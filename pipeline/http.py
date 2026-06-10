from __future__ import annotations

import json
import time
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "regulatory-monitor (+https://github.com/beatrizvallina/regulatory_monitor)"


def get_text(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    retries: int = 2,
) -> str:
    if params:
        separator = "&" if "?" in url else "?"
        url = url + separator + urlencode(params)

    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)

    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers=request_headers)
            with urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(last_error))


def get_json(url: str, **kwargs: object) -> Dict[str, object]:
    return json.loads(get_text(url, **kwargs))
