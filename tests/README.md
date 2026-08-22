# Tests

    ../venv/bin/python tests/test_whatsapp_webhook.py
    ../venv/bin/python tests/test_heat_risk_live.py
    ../venv/bin/python tests/test_rider_status.py

All three run standalone — no pytest required — and exit non-zero on any failure.

| File | Covers |
|---|---|
| `test_whatsapp_webhook.py` | GET verification handshake, `X-Hub-Signature-256` enforcement, payload parsing (location / text / delivery receipts / malformed input), wamid deduplication, risk banding, `/health` |
| `test_heat_risk_live.py` | U.S. coverage gate, AOI geometry and cache-grid snapping, tile lookup, cached-layer reuse, duration-based escalation, `env_params` hot-hour selection |
| `test_rider_status.py` | `getHyperlocalTemperature` (determinism, provenance, non-finite input), `evaluateRiderSafetyStatus` band edges at 34.9/35.0/39.9/40.0, a 0–60 °C sweep proving the bands leave no gap, the Danger rest-protocol flags, typed-coordinate parsing, and the unified controller from signed POST through to reply text |

## All three suites are offline by design

None makes a network call, and that is enforced rather than assumed:

* `test_whatsapp_webhook.py` sets `SAFETY_RIDER_LIVE_HEAT=0` **before importing
  the app**. Without it the suite picks up `FORTYGUARD_API_KEY` from `.env`,
  makes real billable calls, and hangs on the polling loop.
* `test_rider_status.py` sets both `SAFETY_RIDER_LIVE_HEAT=0` and
  `SAFETY_RIDER_MOCK_TEMPERATURE=1` before importing the app, and swaps
  `graph_client.send_text` for a capture function so the controller's replies
  are asserted on rather than delivered. It restores the real function after.
* `test_heat_risk_live.py` points `FORTYGUARD_BASE_URL` at an unroutable address
  and injects a `FakeClient` that raises if the code tries to bill a heatmap it
  should have served from cache. It seeds and then removes its own cache files.

If you add a test that touches `check_rider_heat_risk` or
`get_hyperlocal_temperature`, keep the same guards.

## Demoing a specific band

`SAFETY_RIDER_MOCK_TEMP_C` pins the simulated temperature to an exact value, so
you can show the Danger branch on a mild afternoon:

    SAFETY_RIDER_MOCK_TEMPERATURE=1 SAFETY_RIDER_MOCK_TEMP_C=41.5 \
        ../venv/bin/uvicorn safety_rider.app:app --port 8000

Without the override the value is derived by hashing the grid cell and date —
deterministic, so the same pin always gives the same answer, but which band a
given pin lands in is arbitrary.
