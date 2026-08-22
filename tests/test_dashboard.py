"""Dashboard API: page, state, SSE, and the guarded demo simulator.

Run:  venv/bin/python tests/test_dashboard.py
"""
import json, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Offline and non-sending, pinned BEFORE the app import. See tests/README.md.
os.environ["SAFETY_RIDER_LIVE_HEAT"] = "0"
os.environ["SAFETY_RIDER_MOCK_TEMPERATURE"] = "1"
os.environ["SAFETY_RIDER_DEV_TOOLS"] = "1"
os.environ["SAFETY_RIDER_DEMO_NUMBER"] = ""      # empty => simulate sends nothing
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-verify-token"
os.environ["WHATSAPP_APP_SECRET"] = "test-app-secret"
os.environ["WHATSAPP_ACCESS_TOKEN"] = ""
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = ""

from fastapi.testclient import TestClient

from safety_rider.app import app
from safety_rider.events import Event, Hub, RiderState, hub, mask_number

client = TestClient(app)
ok = True

def check(label, cond):
    global ok
    ok = ok and cond
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


print("\n[1] Page and vendored assets")
r = client.get("/dashboard")
check(f"GET /dashboard -> 200 html (got {r.status_code})",
      r.status_code == 200 and "<title>Safety Rider" in r.text)
for asset in ("leaflet.js", "leaflet.css"):
    a = client.get(f"/dashboard/static/vendor/{asset}")
    check(f"{asset} served locally ({a.status_code}, {len(a.content)} bytes)",
          a.status_code == 200 and len(a.content) > 1000)
check("page references the local vendor copy, not a CDN",
      "/dashboard/static/vendor/leaflet.js" in r.text
      and "unpkg.com/leaflet" not in r.text)

print("\n[2] Phone masking")
check("masks a real number", mask_number("14155550123") == "+14155****123")
check("full number never appears in the mask", "5550123" not in mask_number("14155550123"))
check("short number handled", mask_number("12345") == "+12345")
check("non-numeric label passes through", mask_number("demo") == "demo")

print("\n[3] State endpoint")
hub.clear()
s = client.get("/api/dashboard/state").json()
check("has riders/events/center", {"riders","events","center"} <= set(s))
check(f"centre defaults to San Jose ({s['center']['lat']}, {s['center']['lon']})",
      abs(s["center"]["lat"] - 37.3318) < 0.01)
check("starts empty after clear", s["riders"] == [] and s["events"] == [])
check("reports mock mode so the UI can label it", s["mock_mode"] is True)

print("\n[4] Simulate heat spike")
r = client.post("/api/dashboard/simulate",
                json={"temperature_c": 41.5, "send_whatsapp": True})
d = r.json()
check(f"200 (got {r.status_code})", r.status_code == 200)
check(f"reaches DANGER at 41.5 (got {d['status']})", d["status"] == "danger")
check("rest protocol flagged", d["rest_protocol"] is True)
check("no demo number configured -> nothing sent", d["whatsapp_sent"] is False)
check("says why nothing was sent", d["error"] and "DEMO_NUMBER" in d["error"])
check("returns the exact reply text for the demo", "Stop riding" in d["reply_preview"])
check("reply carries SIMULATED provenance", "SIMULATED" in d["reply_preview"])

s = client.get("/api/dashboard/state").json()
check(f"rider appears on the map ({len(s['riders'])})", len(s["riders"]) == 1)
check("rider carries the danger status", s["riders"][0]["status"] == "danger")
check("feed quotes the SAME temperature the rider was sent (41.5, not 42)",
      any("41.5 °C" in e["text"] for e in s["events"]))

print("\n[5] The simulator cannot be turned into a spam relay")
import inspect
from safety_rider.dashboard.routes import SimulateRequest
fields = set(SimulateRequest.model_fields)
check(f"request body has no recipient field ({sorted(fields)})",
      not fields & {"to", "to_number", "recipient", "phone", "number"})

print("\n[6] Dev tools can be switched off")
from safety_rider import config as cfg
import safety_rider.dashboard.routes as droutes
saved = droutes.settings
class _Off:
    def __getattr__(self, n): return getattr(saved, n)
    dev_tools = False
droutes.settings = _Off()
r = client.post("/api/dashboard/simulate", json={"temperature_c": 41.5})
check(f"simulate -> 403 when disabled (got {r.status_code})", r.status_code == 403)
r = client.post("/api/dashboard/reset")
check(f"reset -> 403 when disabled (got {r.status_code})", r.status_code == 403)
droutes.settings = saved

print("\n[7] SSE stream")
# Exercised through the endpoint directly, not TestClient.stream: the generator
# is an infinite loop by contract, so a blocking client read never returns and
# the suite hangs. A stub request lets us drive the disconnect deterministically.
import asyncio
from safety_rider.dashboard.routes import dashboard_stream

class FakeRequest:
    """Reports connected for the first N polls, then disconnected."""
    def __init__(self, polls=2):
        self.polls, self.seen = polls, 0
    async def is_disconnected(self):
        self.seen += 1
        return self.seen > self.polls

async def drive_stream():
    resp = await dashboard_stream(FakeRequest(polls=2))
    frames, it = [], resp.body_iterator
    frames.append(await anext(it))                       # opening frame
    hub.publish(Event(kind="evaluation", text="stream check",
                      status="danger", rider_id="+14155****123",
                      latitude=37.3, longitude=-121.8, temperature_c=41.5))
    frames.append(await anext(it))                       # the published event
    await it.aclose()
    return resp, frames

resp, frames = asyncio.run(drive_stream())
check(f"content-type is text/event-stream (got {resp.headers.get('content-type')})",
      "text/event-stream" in resp.headers.get("content-type", ""))
check("proxy buffering disabled (X-Accel-Buffering: no)",
      resp.headers.get("x-accel-buffering") == "no")
check("caching disabled", "no-cache" in resp.headers.get("cache-control", ""))
check(f"opens with an SSE frame ({frames[0][:24]!r})",
      frames[0].startswith(":") or frames[0].startswith("data:"))
check("published event reaches the stream", "stream check" in frames[1])
check("frames are SSE-terminated (blank line)", frames[1].endswith("\n\n"))
payload = json.loads(frames[1].split("data: ", 1)[1].strip())
check(f"event carries coordinates for the map ({payload['latitude']}, {payload['longitude']})",
      payload["latitude"] == 37.3 and payload["longitude"] == -121.8)
check("event carries the danger status for the blinking marker",
      payload["status"] == "danger")
check("subscriber released after the stream closes", hub.subscriber_count == 0)

print("\n[8] Hub fan-out and backpressure")
h = Hub()
h.upsert_rider(RiderState(rider_id="r1", latitude=1.0, longitude=2.0, status="safe"))
check("rider stored", len(h.riders()) == 1)
h.upsert_rider(RiderState(rider_id="r1", latitude=3.0, longitude=4.0, status="danger"))
check("same id updates in place, no duplicate", len(h.riders()) == 1
      and h.riders()[0]["status"] == "danger")
for i in range(150):
    h.publish(Event(kind="system", text=f"e{i}"))
check(f"history is capped ({len(h.history())} <= 100)", len(h.history()) <= 100)
check("keeps the newest", h.history()[-1]["text"] == "e149")

async def saturate():
    async with h.subscribe() as q:
        check("subscriber registered", h.subscriber_count == 1)
        for i in range(500):          # far beyond QUEUE_MAXSIZE
            h.publish(Event(kind="system", text=f"flood{i}"))
        return h.subscriber_count
left = asyncio.run(saturate())
check(f"a subscriber that never drains is dropped, not allowed to block (count={left})",
      left == 0)
check("hub is empty again after the context exits", h.subscriber_count == 0)

print("\n[9] Rider state serialises cleanly for the browser")
st = RiderState(rider_id="+14155****123", latitude=37.3, longitude=-121.8,
                status="danger", temperature_c=41.5)
js = json.dumps(st.to_dict())
check("JSON round-trips", json.loads(js)["temperature_c"] == 41.5)
check("carries an ISO timestamp", "T" in json.loads(js)["updated_at"])

hub.clear()
print("\n" + ("ALL DASHBOARD CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
raise SystemExit(0 if ok else 1)
