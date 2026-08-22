"""End-to-end exercise of the webhook without touching Meta or FortyGuard.

Run:  ../venv/bin/python tests/test_whatsapp_webhook.py
"""
import hashlib, hmac, json, os, pathlib, sys

# Make the repo root importable however this file is invoked.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Hard-disable the live heat path BEFORE importing the app. Without this the
# webhook test picks up FORTYGUARD_API_KEY from .env and makes real, billable
# API calls — which also makes the suite hang on the polling loop.
os.environ["SAFETY_RIDER_LIVE_HEAT"] = "0"

os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-verify-token"
os.environ["WHATSAPP_APP_SECRET"] = "test-app-secret"
# Set to empty rather than popped. Popping leaves the name unset, so
# config.py's load_dotenv() happily fills it from a real .env and the suite
# starts making live Graph API calls. An empty value is still "present", so
# load_dotenv(override=False) leaves it alone, and config._env() reads it as
# unset -- which is exactly the unconfigured state these tests want.
os.environ["WHATSAPP_ACCESS_TOKEN"] = ""
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = ""

from fastapi.testclient import TestClient
from safety_rider.app import app

client = TestClient(app)
ok = True

def check(label, cond):
    global ok
    ok = ok and cond
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")

print("\n[1] GET verification")
r = client.get("/webhook/whatsapp", params={
    "hub.mode": "subscribe", "hub.verify_token": "test-verify-token",
    "hub.challenge": "1158201444"})
check(f"valid token -> 200 + bare challenge (got {r.status_code} {r.text!r})",
      r.status_code == 200 and r.text == "1158201444")

r = client.get("/webhook/whatsapp", params={
    "hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"})
check(f"wrong token -> 403 (got {r.status_code})", r.status_code == 403)

r = client.get("/webhook/whatsapp", params={
    "hub.mode": "unsubscribe", "hub.verify_token": "test-verify-token",
    "hub.challenge": "x"})
check(f"wrong mode -> 403 (got {r.status_code})", r.status_code == 403)

print("\n[2] POST signature enforcement")
def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()

LOCATION_PAYLOAD = {
  "object": "whatsapp_business_account",
  "entry": [{"id": "102290129340398", "changes": [{"field": "messages", "value": {
      "messaging_product": "whatsapp",
      "metadata": {"display_phone_number": "15550001111", "phone_number_id": "106540352242922"},
      "contacts": [{"profile": {"name": "Asha"}, "wa_id": "14155551234"}],
      "messages": [{"from": "14155551234", "id": "wamid.LOC1", "timestamp": "1740000000",
                    "type": "location",
                    "location": {"latitude": 37.3318, "longitude": -121.8899,
                                 "name": "Diridon Station", "address": "San Jose, CA"}}]}}]}]}

body = json.dumps(LOCATION_PAYLOAD).encode()
r = client.post("/webhook/whatsapp", content=body,
                headers={"X-Hub-Signature-256": sign(body), "Content-Type": "application/json"})
check(f"signed payload -> 200 (got {r.status_code})", r.status_code == 200)

r = client.post("/webhook/whatsapp", content=body,
                headers={"X-Hub-Signature-256": "sha256=deadbeef", "Content-Type": "application/json"})
check(f"bad signature -> 403 (got {r.status_code})", r.status_code == 403)

r = client.post("/webhook/whatsapp", content=body, headers={"Content-Type": "application/json"})
check(f"missing signature -> 403 (got {r.status_code})", r.status_code == 403)

print("\n[3] Parser")
from safety_rider.whatsapp.parser import iter_inbound_messages
msgs = list(iter_inbound_messages(LOCATION_PAYLOAD))
check(f"location message parsed (n={len(msgs)})", len(msgs) == 1)
m = msgs[0]
check(f"sender={m.from_number}", m.from_number == "14155551234")
check(f"profile_name={m.profile_name}", m.profile_name == "Asha")
check(f"lat/lon={m.location.latitude},{m.location.longitude}",
      m.location is not None and abs(m.location.latitude - 37.3318) < 1e-9)
check(f"geojson order (lon first) = {m.location.geojson_coordinates}",
      m.location.geojson_coordinates[0] == -121.8899)
check(f"phone_number_id={m.phone_number_id}", m.phone_number_id == "106540352242922")

TEXT_PAYLOAD = json.loads(json.dumps(LOCATION_PAYLOAD))
TEXT_PAYLOAD["entry"][0]["changes"][0]["value"]["messages"] = [
    {"from": "14155551234", "id": "wamid.TXT1", "timestamp": "1740000001",
     "type": "text", "text": {"body": "how hot is it?"}}]
tm = list(iter_inbound_messages(TEXT_PAYLOAD))
check(f"text parsed: {tm[0].text!r}", len(tm) == 1 and tm[0].text == "how hot is it?")
check("text has no location", tm[0].location is None)

STATUS_PAYLOAD = {"object": "whatsapp_business_account", "entry": [{"id": "1", "changes": [
    {"field": "messages", "value": {"messaging_product": "whatsapp",
     "metadata": {"phone_number_id": "1"},
     "statuses": [{"id": "wamid.X", "status": "delivered", "timestamp": "1740000002",
                   "recipient_id": "14155551234"}]}}]}]}
check("delivery receipt yields 0 messages", len(list(iter_inbound_messages(STATUS_PAYLOAD))) == 0)
check("empty dict yields 0 messages", len(list(iter_inbound_messages({}))) == 0)
check("junk payload yields 0 messages", len(list(iter_inbound_messages({"entry": [None, "x"]}))) == 0)

BAD_COORDS = json.loads(json.dumps(LOCATION_PAYLOAD))
BAD_COORDS["entry"][0]["changes"][0]["value"]["messages"][0]["location"] = {
    "latitude": 999, "longitude": -121.8}
check("out-of-range coords dropped",
      list(iter_inbound_messages(BAD_COORDS))[0].location is None)

print("\n[4] Deduplication")
from safety_rider.whatsapp.webhook import _SEEN_MESSAGE_IDS
check(f"wamid.LOC1 recorded as seen ({len(_SEEN_MESSAGE_IDS)} tracked)",
      "wamid.LOC1" in _SEEN_MESSAGE_IDS)

print("\n[5] Heat risk scaffold")
from safety_rider.heat_risk import (check_rider_heat_risk, checkRiderHeatRisk,
                                    classify, RiskLevel)
from safety_rider.whatsapp.models import RiderLocation
risk = check_rider_heat_risk(RiderLocation(37.3318, -121.8899))
check("alias checkRiderHeatRisk is the same callable",
      checkRiderHeatRisk is check_rider_heat_risk)
check(f"returns HeatRisk (level={risk.level.value}, is_live={risk.is_live})",
      risk.level == RiskLevel.CAUTION and risk.is_live is False)
check("renders a WhatsApp body", "*" in risk.to_whatsapp_text())
check("classify(20) -> low", classify(20.0) == RiskLevel.LOW)
check("classify(28) -> caution", classify(28.0) == RiskLevel.CAUTION)
check("classify(33) -> high", classify(33.0) == RiskLevel.HIGH)
check("classify(40) -> extreme", classify(40.0) == RiskLevel.EXTREME)
check("classify(28, 5h) escalates caution -> high", classify(28.0, 5.0) == RiskLevel.HIGH)
check("classify(40, 9h) stays extreme (no overflow)", classify(40.0, 9.0) == RiskLevel.EXTREME)

print("\n[6] Health endpoint")
h = client.get("/health").json()
check(f"health ok, configured={h['configured']}", h["status"] == "ok"
      and h["configured"]["verify_token"] and not h["configured"]["access_token"])
check("outbound stayed unconfigured -> no live Graph calls",
      not h["configured"]["access_token"] and not h["configured"]["phone_number_id"])

print("\n--- sample reply body ---")
print(risk.to_whatsapp_text())
print("\n" + ("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
raise SystemExit(0 if ok else 1)
