"""고덕지도 링크에서 좌표를 찾아 data.json의 일정에 loc(위치)를 채웁니다.

GitHub Actions에서 data.json이 바뀔 때마다 실행돼요.
- 직접 찍은 위치(loc에 src가 없는 것)는 건드리지 않아요.
- 링크가 바뀌면 자동으로 찾은 위치(src="amap")를 다시 찾아요.
- 못 찾은 곳은 amap-status.json에 이유와 함께 적어 둬요.
- 저장소 Settings → Secrets에 AMAP_KEY(고덕 웹서비스 키)를 넣으면
  검색 링크·가게 ID·주소까지 더 잘 찾아요. 없어도 동작해요.
"""
import json, os, re, sys, time, urllib.parse, urllib.request, datetime

DATA = "data.json"
STATUS = "amap-status.json"
KEY = os.environ.get("AMAP_KEY", "").strip()
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

# 대련 주변 범위 (잘못된 숫자를 좌표로 착각하지 않게)
LAT = (38.5, 39.8)
LNG = (120.8, 122.8)


def in_dalian(lat, lng):
    return LAT[0] <= lat <= LAT[1] and LNG[0] <= lng <= LNG[1]


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # 리다이렉트는 자동으로 따라감
        body = r.read(400_000).decode("utf-8", "replace")
        return r.geturl(), body


def find_pair(text):
    """텍스트 안에서 대련 범위의 (위도, 경도) 한 쌍을 찾음. 고덕 좌표(GCJ-02) 그대로."""
    t = urllib.parse.unquote(urllib.parse.unquote(text))
    pats = [
        # p=POI,lat,lng  (공유 링크)
        (r"[?&#]p=[^,&]*,(\d{2}\.\d+),(\d{3}\.\d+)", "latlng"),
        # position=lng,lat / location=lng,lat / lnglat=lng,lat
        (r"(?:position|location|lnglat|center|coord|dest|to|from)\"?\s*[=:]\s*\"?(\d{3}\.\d+)\s*,\s*(\d{2}\.\d+)", "lnglat"),
        (r"[?&]q=(\d{2}\.\d+),(\d{3}\.\d+)", "latlng"),
        (r"\"lng\"\s*:\s*\"?(\d{3}\.\d+)\"?\s*,\s*\"lat\"\s*:\s*\"?(\d{2}\.\d+)", "lnglat"),
        (r"\"lat\"\s*:\s*\"?(\d{2}\.\d+)\"?\s*,\s*\"lng\"\s*:\s*\"?(\d{3}\.\d+)", "latlng"),
        (r"\"x\"\s*:\s*\"?(\d{3}\.\d+)\"?\s*,\s*\"y\"\s*:\s*\"?(\d{2}\.\d+)", "lnglat"),
        # 마지막 수단: 대련 범위의 경도,위도 숫자쌍
        (r"(12[0-2]\.\d{4,})\s*[,，]\s*(3[89]\.\d{4,})", "lnglat"),
        (r"(3[89]\.\d{4,})\s*[,，]\s*(12[0-2]\.\d{4,})", "latlng"),
    ]
    for pat, order in pats:
        for m in re.finditer(pat, t):
            a, b = float(m.group(1)), float(m.group(2))
            lat, lng = (a, b) if order == "latlng" else (b, a)
            if in_dalian(lat, lng):
                return round(lat, 6), round(lng, 6)
    return None


def poi_id(text):
    m = re.search(r"\b(B0[0-9A-Z]{8})\b", urllib.parse.unquote(text))
    return m.group(1) if m else None


def by_key(url, final, body):
    """AMAP_KEY가 있을 때: 가게 ID · 검색어로 좌표 찾기"""
    if not KEY:
        return None
    pid = poi_id(url) or poi_id(final) or poi_id(body[:20000])
    if pid:
        u = "https://restapi.amap.com/v3/place/detail?" + urllib.parse.urlencode({"id": pid, "key": KEY})
        j = json.loads(fetch(u)[1])
        pois = j.get("pois") or []
        if pois and pois[0].get("location"):
            lng, lat = map(float, pois[0]["location"].split(","))
            return round(lat, 6), round(lng, 6)
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(final or url).query)
    kw = (qs.get("keyword") or qs.get("keywords") or qs.get("query") or [None])[0]
    if kw:
        u = "https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(
            {"keywords": kw, "city": "大连", "citylimit": "true", "offset": 1, "key": KEY})
        j = json.loads(fetch(u)[1])
        pois = j.get("pois") or []
        if pois and pois[0].get("location"):
            lng, lat = map(float, pois[0]["location"].split(","))
            return round(lat, 6), round(lng, 6)
    return None


def resolve(url):
    """(위치 or None, 못 찾은 이유)"""
    hit = find_pair(url)
    if hit:
        return hit, ""
    final, body = url, ""
    try:
        final, body = fetch(url)
    except Exception as e:  # noqa: BLE001
        return None, f"링크를 열지 못했어요 ({e.__class__.__name__})"
    hit = find_pair(final) or find_pair(body)
    if hit:
        return hit, ""
    # 가게 ID가 보이면 고덕 상세 정보 시도 (키 없이)
    pid = poi_id(url) or poi_id(final) or poi_id(body[:20000])
    if pid:
        for u in (f"https://www.amap.com/detail/get/detail?id={pid}",
                  f"https://ditu.amap.com/detail/get/detail?id={pid}"):
            try:
                hit = find_pair(fetch(u)[1])
                if hit:
                    return hit, ""
            except Exception:  # noqa: BLE001
                pass
    try:
        hit = by_key(url, final, body)
        if hit:
            return hit, ""
    except Exception as e:  # noqa: BLE001
        return None, f"고덕 키로 찾기 실패 ({e.__class__.__name__})"
    if "search" in final or "keyword" in final:
        return None, "검색 링크라 정확한 위치가 없어요. 고덕 앱에서 가게를 연 뒤 '공유'로 받은 링크를 넣어 주세요."
    return None, "이 링크에는 좌표가 없어요. 고덕 앱에서 가게를 연 뒤 '공유 → 링크 복사'로 받은 링크를 넣어 주세요."


def is_map(link):
    return link.get("kind") == "map" or re.search(r"(^|\.)amap\.com|gaode\.com", urllib.parse.urlparse(link.get("url", "")).netloc or "")


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    changed, unresolved, done = False, [], []
    for day in data.get("days", []):
        for it in day.get("items", []):
            links = [l for l in it.get("links", []) if is_map(l)]
            loc = it.get("loc")
            if not links:
                if loc and loc.get("src") == "amap":  # 링크를 지웠으면 자동 위치도 지움
                    del it["loc"]; changed = True
                continue
            if loc and loc.get("src") != "amap":
                continue  # 직접 찍은 위치는 그대로
            url = links[0]["url"]
            if loc and loc.get("from") == url:
                continue  # 이미 찾음
            hit, why = resolve(url)
            time.sleep(1)
            if hit:
                it["loc"] = {"lat": hit[0], "lng": hit[1], "src": "amap", "from": url}
                changed = True
                done.append(it.get("title", ""))
                print("찾음:", it.get("title"), hit)
            else:
                if loc and loc.get("src") == "amap":
                    del it["loc"]; changed = True
                unresolved.append({"id": it.get("id"), "title": it.get("title", ""), "url": url, "reason": why})
                print("못 찾음:", it.get("title"), "-", why)
    status = {"updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds"),
              "found": done, "unresolved": unresolved}
    old = None
    if os.path.exists(STATUS):
        try:
            old = json.load(open(STATUS, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            old = None
    if changed:
        with open(DATA, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    if changed or not old or old.get("unresolved") != unresolved:
        with open(STATUS, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
