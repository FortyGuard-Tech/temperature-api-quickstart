"""The intelligence engine end to end, without touching Meta or FortyGuard.

Covers getHyperlocalTemperature, evaluateRiderSafetyStatus, and the unified
webhook controller that chains them.

Run:  venv/bin/python tests/test_rider_status.py
"""
import hashlib, hmac, json, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Pin everything OFFLINE before importing the app. Without these the suite
# picks up a real FORTYGUARD_API_KEY / WHATSAPP_ACCESS_TOKEN from .env and
# makes billable calls. Empty strings rather than pops: an unset name lets
# config.py's load_dotenv() refill it from .env, while an empty value is
# "present" to dotenv and "unset" to config._env().
os.environ["SAFETY_RIDER_LIVE_HEAT"] = "0"
os.environ["SAFETY_RIDER_MOCK_TEMPERATURE"] = "1"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-verify-token"
os.environ["WHATSAPP_APP_SECRET"] = "test-app-secret"
os.environ["WHATSAPP_ACCESS_TOKEN"] = ""
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = ""

from fastapi.testclient import TestClient

from safety_rider.app import app
from safety_rider.rider_status import (
    DANGER_THRESHOLD_C, SafetyStatus, WARNING_THRESHOLD_C,
    evaluate_rider_safety_status, evaluateRiderSafetyStatus,
)
from safety_rider.temperature_service import (
    SOURCE_MOCK, get_hyperlocal_temperature, getHyperlocalTemperature,
)
from safety_rider.whatsapp import graph_client, webhook
from safety_rider.whatsapp.parser import coordinates_from_text

client = TestClient(app)
ok = True

def check(label, cond):
    global ok
    ok = ok and cond
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


print("\n[1] Band edges — the boundary is where bugs live")
check("aliases point at the same callables",
      evaluateRiderSafetyStatus is evaluate_rider_safety_status
      and getHyperlocalTemperature is get_hyperlocal_temperature)
check(f"thresholds are {WARNING_THRESHOLD_C}/{DANGER_THRESHOLD_C}",
      WARNING_THRESHOLD_C == 35.0 and DANGER_THRESHOLD_C == 40.0)

cases = [
    (10.0,  SafetyStatus.SAFE),
    (34.9,  SafetyStatus.SAFE),     # just under
    (35.0,  SafetyStatus.WARNING),  # inclusive lower edge
    (37.5,  SafetyStatus.WARNING),
    (39.0,  SafetyStatus.WARNING),  # the spec's stated top of Warning
    (39.9,  SafetyStatus.WARNING),  # the gap the spec left open
    (40.0,  SafetyStatus.DANGER),   # inclusive lower edge
    (55.0,  SafetyStatus.DANGER),
]
for temp, expected in cases:
    got = evaluate_rider_safety_status(temp).status
    check(f"{temp:>5} C -> {expected.value:<7} (got {got.value})", got is expected)

print("\n[2] No gap, no overlap across the whole line")
# 601 evaluations at INFO would bury the rest of the run; the per-evaluation
# log line is wanted in production, just not 601 times here.
import logging
_rs_log = logging.getLogger("safety_rider.rider_status")
_rs_log.setLevel(logging.WARNING)
bands = [evaluate_rider_safety_status(t / 10).status for t in range(0, 601)]
_rs_log.setLevel(logging.NOTSET)
check("every temperature 0-60 C lands in a real band",
      SafetyStatus.UNKNOWN not in bands)
check("bands only ever escalate as temperature rises",
      bands == sorted(bands, key=[SafetyStatus.SAFE, SafetyStatus.WARNING,
                                  SafetyStatus.DANGER].index))

print("\n[3] Unknown input degrades, never raises")
for bad in (None, float("nan"), float("inf"), "not a number", object()):
    st = evaluate_rider_safety_status(bad)
    check(f"{bad!r:<20} -> unknown, no exception", st.status is SafetyStatus.UNKNOWN)
check("unknown still gives the rider something to do",
      len(evaluate_rider_safety_status(None).actions) > 0)

print("\n[4] Danger triggers the protocol flags")
danger = evaluate_rider_safety_status(42.0)
check("rest_protocol is set", danger.rest_protocol is True)
check("reroute is set", danger.reroute is True)
check("actions mention stopping", any("Stop riding" in a for a in danger.actions))
warn = evaluate_rider_safety_status(36.0)
check("Warning does NOT set rest_protocol", warn.rest_protocol is False)
check("Warning recommends hydration", any("Drink" in a for a in warn.actions))
safe = evaluate_rider_safety_status(20.0)
check("Safe carries no actions (no nagging)", safe.actions == [])

print("\n[5] Duration promotes Safe, but never fabricates Danger")
check("34 C + 6h sustained -> warning",
      evaluate_rider_safety_status(34.0, hours_above_threshold=6.0).status
      is SafetyStatus.WARNING)
check("34 C + 1h -> stays safe",
      evaluate_rider_safety_status(34.0, hours_above_threshold=1.0).status
      is SafetyStatus.SAFE)
check("38 C + 12h stays WARNING (40 C cutoff is not overridden)",
      evaluate_rider_safety_status(38.0, hours_above_threshold=12.0).status
      is SafetyStatus.WARNING)
check("long exposure adds a timing tip",
      any("before 10am" in a for a in
          evaluate_rider_safety_status(38.0, hours_above_threshold=12.0).actions))

print("\n[6] getHyperlocalTemperature (mock mode — no network)")
r1 = get_hyperlocal_temperature(37.3318, -121.8899)
r2 = get_hyperlocal_temperature(37.3318, -121.8899)
check(f"returns a reading (source={r1.source}, {r1.celsius} C)",
      r1.source == SOURCE_MOCK and r1.ok)
check("deterministic: same point twice -> same value", r1.celsius == r2.celsius)
far = get_hyperlocal_temperature(40.7128, -74.0060)
check(f"different city -> different value ({far.celsius} C)",
      far.celsius != r1.celsius)
check("float(reading) works", float(r1) == r1.celsius)
check(f"fahrenheit conversion ({r1.fahrenheit:.1f} F)",
      abs(r1.fahrenheit - (r1.celsius * 9 / 5 + 32)) < 1e-9)
check("min < mean < peak", r1.daily_min_c < r1.daily_mean_c < r1.celsius)
check("observed_date is set and is NOT today",
      r1.observed_date is not None and r1.observed_date != __import__("datetime").date.today().isoformat())
check("describe() flags the reading as simulated", "SIMULATED" in r1.describe())
check(f"note records why it was simulated ({r1.note!r})", bool(r1.note))

bad = get_hyperlocal_temperature(float("nan"), -121.0)
check("non-finite coords -> unavailable, no exception", not bad.ok)
check("unavailable reading -> unknown status",
      evaluate_rider_safety_status(bad.celsius if bad.ok else None).status
      is SafetyStatus.UNKNOWN)

print("\n[7] Typed coordinates parse; prose does not")
loc = coordinates_from_text("37.3318, -121.8899")
check("'37.3318, -121.8899' parses", loc is not None
      and abs(loc.latitude - 37.3318) < 1e-9 and abs(loc.longitude + 121.8899) < 1e-9)
check("whitespace-separated parses", coordinates_from_text("37.33 -121.88") is not None)
check("prose containing numbers is rejected",
      coordinates_from_text("I'll be there in 5, 10 minutes") is None)
check("out-of-range latitude rejected", coordinates_from_text("991.0, -121.0") is None)
check("empty text -> None", coordinates_from_text("") is None)

print("\n[8] Unified controller: POST -> temperature -> band -> reply")
SENT = []
_real_send = graph_client.send_text
async def _capture(to_number, body, **kw):
    SENT.append((to_number, body))
    return {"messages": [{"id": "wamid.FAKE"}]}
graph_client.send_text = _capture

def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()

def post_location(lat, lon, wamid):
    payload = {"object": "whatsapp_business_account", "entry": [{"id": "1", "changes": [
        {"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "15550001111", "phone_number_id": "106540352242922"},
            "contacts": [{"profile": {"name": "Asha"}, "wa_id": "14155551234"}],
            "messages": [{"from": "14155551234", "id": wamid, "timestamp": "1740000000",
                          "type": "location", "location": {"latitude": lat, "longitude": lon}}]}}]}]}
    raw = json.dumps(payload).encode()
    return client.post("/webhook/whatsapp", content=raw,
                       headers={"X-Hub-Signature-256": sign(raw),
                                "Content-Type": "application/json"})

# Force the Danger band so the assertion does not depend on which mock value
# this particular grid cell hashes to.
os.environ["SAFETY_RIDER_MOCK_TEMP_C"] = "41.5"
import importlib
from safety_rider import config as cfg
importlib.reload(cfg)
import safety_rider.temperature_service as tsvc
tsvc.settings = cfg.settings

SENT.clear()
r = post_location(37.3318, -121.8899, "wamid.CTRL1")
check(f"POST acked 200 (got {r.status_code})", r.status_code == 200)
check(f"two messages sent (ack + verdict), got {len(SENT)}", len(SENT) == 2)
verdict = SENT[-1][1] if SENT else ""
check("verdict addressed to the sender", bool(SENT) and SENT[-1][0] == "14155551234")
check("Danger band reached at 41.5 C", "🔴" in verdict)
check("rest protocol text present", "Stop riding" in verdict)
check("temperature quoted in the reply", "41.5 °C" in verdict)
check("provenance line marks it SIMULATED", "SIMULATED" in verdict)

os.environ["SAFETY_RIDER_MOCK_TEMP_C"] = "22.0"
importlib.reload(cfg); tsvc.settings = cfg.settings
SENT.clear()
r = post_location(37.4000, -121.9000, "wamid.CTRL2")
verdict = SENT[-1][1] if SENT else ""
check("Safe band at 22 C", "🟢" in verdict and "Clear to ride" in verdict)
check("Safe reply carries no rest protocol", "Stop riding" not in verdict)

print("\n[9] A failing Graph call must not kill the flow")
async def _boom(to_number, body, **kw):
    SENT.append((to_number, "<raised>"))
    raise graph_client.WhatsAppSendError("Graph 401: token expired")
graph_client.send_text = _boom
SENT.clear()
r = post_location(37.5, -121.95, "wamid.CTRL3")
check(f"webhook still returns 200 when Graph 401s (got {r.status_code})",
      r.status_code == 200)
check("both sends were attempted despite the first failing", len(SENT) == 2)

graph_client.send_text = _real_send
os.environ.pop("SAFETY_RIDER_MOCK_TEMP_C", None)

print("\n[10] Duplicate delivery does not double-reply")
graph_client.send_text = _capture
SENT.clear()
post_location(37.6, -121.7, "wamid.DUP")
first = len(SENT)
post_location(37.6, -121.7, "wamid.DUP")
check(f"same wamid twice -> no extra sends ({first} then {len(SENT)})",
      len(SENT) == first and first > 0)
graph_client.send_text = _real_send

print("\n--- sample Danger reply ---")
os.environ["SAFETY_RIDER_MOCK_TEMP_C"] = "41.5"
importlib.reload(cfg); tsvc.settings = cfg.settings
demo_reading = get_hyperlocal_temperature(37.3318, -121.8899)
print(evaluate_rider_safety_status(
    demo_reading.celsius,
    hours_above_threshold=demo_reading.hours_above_threshold,
).to_whatsapp_text(demo_reading))
os.environ.pop("SAFETY_RIDER_MOCK_TEMP_C", None)

print("\n" + ("ALL ENGINE CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
raise SystemExit(0 if ok else 1)
