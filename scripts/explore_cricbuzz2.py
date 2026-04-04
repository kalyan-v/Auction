"""Find actual Cricbuzz match IDs for IPL 2026 and check run out data."""
import requests, re, json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 1. Find Cricbuzz IPL 2026 schedule page
print("=== Finding Cricbuzz IPL 2026 matches ===")
schedule_urls = [
    "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2026/matches",
    "https://www.cricbuzz.com/cricket-series/9238/indian-premier-league-2026/matches",
    "https://www.cricbuzz.com/cricket-series/9100/indian-premier-league-2026/matches",
    "https://www.cricbuzz.com/cricket-series/9300/indian-premier-league-2026/matches",
]

for url in schedule_urls:
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200 and ("csk" in resp.text.lower() or "chennai" in resp.text.lower()):
            print(f"  FOUND: {url}")
            # Find match links with CSK
            links = re.findall(r'href="(/cricket-scores/\d+/[^"]*)"', resp.text)
            for link in links[:20]:
                print(f"    {link}")
            break
        else:
            print(f"  Not found: {url} (status={resp.status_code})")
    except Exception as e:
        print(f"  Error: {e}")

# 2. Try a broader search via Cricbuzz schedule API
print("\n\n=== Cricbuzz schedule API ===")
api_urls = [
    "https://www.cricbuzz.com/api/cricket-schedule/upcoming",
    "https://www.cricbuzz.com/api/cricket-schedule/archive",
]
for url in api_urls:
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            # Search for IPL
            if "Indian Premier" in resp.text or "IPL" in resp.text:
                print(f"  Has IPL data: {url}")
    except:
        pass

# 3. Direct Google search approach: find Cricbuzz scorecard URL
print("\n\n=== Try Cricbuzz match finder ===")
# The match happened on April 3, 2026
# Try to find it via the Cricbuzz live scores page
live_url = "https://www.cricbuzz.com/cricket-match/live-scores"
try:
    resp = requests.get(live_url, headers=headers, timeout=10)
    if resp.status_code == 200:
        # Find any IPL 2026 match links
        links = re.findall(r'href="(/live-cricket-scores/\d+/[^"]*ipl[^"]*2026[^"]*)"', resp.text, re.IGNORECASE)
        if not links:
            links = re.findall(r'href="(/live-cricket-scores/\d+/[^"]*)"', resp.text)
        print(f"  Live score links: {len(links)}")
        for link in links[:10]:
            print(f"    {link}")
except Exception as e:
    print(f"  Error: {e}")

# 4. Try the scorecard for recent matches via Cricbuzz recent results
print("\n\n=== Cricbuzz recent results ===")
recent_url = "https://www.cricbuzz.com/cricket-match/live-scores/recent-matches"
try:
    resp = requests.get(recent_url, headers=headers, timeout=10)
    if resp.status_code == 200:
        links = re.findall(r'href="(/live-cricket-scores/(\d+)/[^"]*)"', resp.text)
        print(f"  Recent match links: {len(links)}")
        for link, mid in links[:15]:
            if "ipl" in link.lower() or "premier" in link.lower():
                print(f"    IPL: {link}")
            else:
                print(f"    {link}")
except Exception as e:
    print(f"  Error: {e}")

# 5. Maybe try ESPN scoreboard which returned data
print("\n\n=== ESPN scoreboard (worked earlier) ===")
url = "https://site.web.api.espn.com/apis/site/v2/sports/cricket/8676/scoreboard"
try:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        events = data.get("events", [])
        print(f"  Events: {len(events)}")
        for ev in events[:5]:
            name = ev.get("name", "")
            eid = ev.get("id", "")
            status = ev.get("status", {}).get("type", {}).get("description", "")
            print(f"    {name} (id={eid}, status={status})")
            
            # Check for completed matches
            if status.lower() in ("final", "complete", "result"):
                # Try to get scorecard
                sc_url = f"https://site.web.api.espn.com/apis/site/v2/sports/cricket/8676/summary?event={eid}"
                sc_resp = requests.get(sc_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, timeout=10)
                if sc_resp.status_code == 200:
                    sc_data = sc_resp.json()
                    sc_text = json.dumps(sc_data)
                    if "run out" in sc_text.lower() or "runOut" in sc_text:
                        print(f"      Has run out data!")
                        for pat in ["run out", "runOut", "run_out"]:
                            idx = sc_text.lower().find(pat.lower())
                            if idx >= 0:
                                print(f"      ...{sc_text[max(0,idx-100):idx+300]}...")
                                break
except Exception as e:
    print(f"  Error: {e}")
