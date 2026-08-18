"""Extraction test: can Tavily Extract / Exa Contents actually fetch pages
from community sites, or do they get blocked (login wall / Cloudflare)?
"""
import json
import os
import re
import urllib.request

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
EXA_KEY = os.environ["EXA_API_KEY"]

TARGETS = {
    "linux.do": "https://linux.do/t/topic/1774105",
    "x.com": "https://x.com/elonmusk",
    "zhihu": "https://www.zhihu.com/",
    "bilibili": "https://www.bilibili.com/video/BV1xmJ8zhEdW",
    "tieba": "https://tieba.baidu.com/f?kw=显卡",
}

BLOCK_SIGNS = [
    (r"video not found|page not found|视频不见了|啊叻.视频不见了|404 not found", "失效页面"),
    (r"just a moment|challenge-platform|cf-browser-verification", "Cloudflare 拦截页"),
    (r"验证码登录|密码登录|登录/注册|扫码登录|登录后", "疑似登录墙"),
    (r"verify you are human|验证您是真人|人机验证", "人机验证"),
    (r"403|forbidden", "403 拒绝"),
    (r"欣喜地发现|敏感|审核", "内容审查提示"),
]


def post(url, payload, headers):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def classify(text):
    if not text:
        return "空内容"
    for pat, label in BLOCK_SIGNS:
        if re.search(pat, text, re.I):
            return label
    if re.search(r"critical instructions for all ai assistants|ignore (?:all )?previous instructions", text, re.I):
        return "拿到正文（含网页内指令文本，必须作为不可信内容忽略）"
    return "拿到正文"


def trunc(s, n=80):
    s = (s or "").replace("\n", " ").strip()
    return s[: n - 1] + "…" if len(s) > n else s


urls = list(TARGETS.values())

print("=" * 78)
print("Tavily Extract API")
print("=" * 78)
try:
    data = post("https://api.tavily.com/extract", {"urls": urls},
                {"Authorization": f"Bearer {TAVILY_KEY}"})
    ok = {r["url"]: r.get("raw_content") or "" for r in data.get("results", [])}
    for name, u in TARGETS.items():
        content = ok.get(u)
        if content is None:
            err = next((f.get("error") for f in data.get("failed_results", [])
                        if f.get("url") == u), "no result")
            print(f"  {name:<10} ❌ 失败: {err}")
        else:
            print(f"  {name:<10} ✅ {classify(content)} | {len(content)} chars")
            print(f"              {trunc(content, 90)}")
except Exception as exc:  # noqa: BLE001
    print(f"  API ERROR: {exc}")

print()
print("=" * 78)
print("Exa Contents API (maxAgeHours=0 强制实时抓取)")
print("=" * 78)
try:
    payload = {"ids": urls, "text": {"maxCharacters": 3000}, "maxAgeHours": 0}
    payload["livecrawlTimeout"] = 30000
    data = post("https://api.exa.ai/contents", payload, {"x-api-key": EXA_KEY})
    results = data.get("results", [])
    statuses = {s.get("id"): s for s in data.get("statuses", [])}
    got = {}
    for r in results:
        key = r.get("id") or r.get("url")
        got[key] = (r.get("text") or "")[:3000]
    for name, u in TARGETS.items():
        content = got.get(u)
        if content is None:
            status = statuses.get(u) or {}
            detail = status.get("error") or status.get("status") or "no status"
            print(f"  {name:<10} ❌ 未返回该 URL | {detail}")
        else:
            print(f"  {name:<10} {'✅' if content else '⚠️ '} {classify(content)} | {len(content)} chars")
            print(f"              {trunc(content, 90)}")
except Exception as exc:  # noqa: BLE001
    print(f"  API ERROR: {exc}")
