"""Exercise the live heat path using a fake client + cached layers. No network."""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
# A fake key: FakeClient stands in for the network, and the coverage gate
# plus pre-seeded caches mean no request is ever attempted.
os.environ["FORTYGUARD_API_KEY"] = "test-key"
os.environ["FORTYGUARD_BASE_URL"] = "http://127.0.0.1:9"  # unroutable, fails fast
os.environ["SAFETY_RIDER_LIVE_HEAT"] = "1"

from safety_rider import heat_layer
from safety_rider.heat_risk import check_rider_heat_risk, classify, RiskLevel
from safety_rider.whatsapp.models import RiderLocation

ok = True
def check(label, cond):
    global ok; ok = ok and cond
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")

SJ = RiderLocation(37.3318, -121.8899, name="Diridon Station")

print("\n[1] Coverage gate")
check("San Jose in coverage", heat_layer.is_in_coverage(37.3318, -121.8899))
check("Anchorage in coverage", heat_layer.is_in_coverage(61.2, -149.9))
check("Honolulu in coverage", heat_layer.is_in_coverage(21.3, -157.85))
check("London NOT in coverage", not heat_layer.is_in_coverage(51.5, -0.12))
check("Karachi NOT in coverage", not heat_layer.is_in_coverage(24.86, 67.0))
r = check_rider_heat_risk(RiderLocation(51.5, -0.12))
check(f"out-of-coverage -> UNKNOWN, no API call ({r.level.value})",
      r.level == RiskLevel.UNKNOWN and not r.is_live)

print("\n[2] Geometry")
aoi = heat_layer.build_aoi(37.3318, -121.8899, 5000)
ring = aoi["features"][0]["geometry"]["coordinates"][0]
check(f"AOI is a closed 5-point ring ({len(ring)} pts)", len(ring) == 5 and ring[0] == ring[-1])
check(f"GeoJSON lon-first (x={ring[0][0]:.4f})", ring[0][0] < -100)
from shapely.geometry import shape as _shape
poly = _shape(aoi["features"][0]["geometry"])
w_km = (poly.bounds[2]-poly.bounds[0]) * 111.32 * __import__('math').cos(__import__('math').radians(37.33))
h_km = (poly.bounds[3]-poly.bounds[1]) * 111.32
check(f"AOI ~10x10 km (got {w_km:.1f} x {h_km:.1f} km)", 9.5 < w_km < 10.5 and 9.5 < h_km < 10.5)
k1 = heat_layer.grid_key(37.3318, -121.8899)
k2 = heat_layer.grid_key(37.3350, -121.8850)   # ~500 m away
k3 = heat_layer.grid_key(37.5000, -121.8899)   # ~19 km away
check(f"nearby riders share a cell {k1}", k1 == k2)
check(f"distant rider gets a different cell {k3}", k1 != k3)

print("\n[3] Live evaluation against synthetic cached layers")
CACHE = heat_layer.cache_dir()
cell_lat, cell_lon = k1
slug = f"rider_{cell_lat:.5f}_{cell_lon:.5f}_TESTDATE"

def tile(lon, lat, props, d=0.001):
    return {"type": "Feature", "properties": props, "geometry": {"type": "Polygon",
            "coordinates": [[[lon-d,lat-d],[lon+d,lat-d],[lon+d,lat+d],[lon-d,lat+d],[lon-d,lat-d]]]}}

tcm = {"map_data": {"features": [tile(-121.8899, 37.3318,
        {"tile_id": 0, "average_temperature": 30.1, "max_temperature": 36.4, "min_temperature": 18.2})]},
       "stats_data": {"n_cells": 1}}
exc = {"map_data": {"features": [tile(-121.8899, 37.3318, {"tile_id": 0, "value": 7.0})]},
       "stats_data": {"analytic_type": "exceedance", "units": "hour"}}

written = []
for name, blob in ((f"heatmap_{slug}_tcm.json", tcm),
                   (f"heatmap_{slug}_exceedance_32.2.json", exc)):
    p = CACHE / name; p.write_text(json.dumps(blob)); written.append(p)

layer = heat_layer.HeatLayer.from_response(tcm)
hit = layer.lookup(37.3318, -121.8899)
check(f"tile lookup hits (peak={hit.get('max_temperature')})", hit and hit["max_temperature"] == 36.4)
check("lookup far outside AOI returns None", layer.lookup(40.0, -100.0) is None)

class FakeClient:
    """Fails loudly if the code tries to bill an API call it should have cached."""
    calls = []
    def create_heatmap(self, **kw):
        FakeClient.calls.append(("heatmap", kw)); raise AssertionError("should have used cache")
    def environmental_parameters(self, **kw):
        FakeClient.calls.append(("env", kw))
        # The REAL envelope, verified against data/env_params/*.json: series are
        # nested under locations[0].parameters, not at the top level.
        ap = [15+10*__import__('math').sin(i/24*3.14159) for i in range(24)]
        hi = [40 - i for i in range(24)]
        return {"result": {"metadata": {"timezone": "GMT-8"},
                           "locations": [{"lat": 37.33, "lon": -121.89,
                                          "temperature": 36.4,
                                          "parameters": {
                                              "apparent_temperature_celsius": ap,
                                              "heat_index_celsius": hi}}]}}

tcm_l, exc_l = heat_layer.fetch_layers(FakeClient(), 37.3318, -121.8899,
                                       study_date="TESTDATE", threshold_c=32.2)
check("both layers loaded from cache, zero heatmap calls",
      tcm_l is not None and exc_l is not None and not FakeClient.calls)
et = exc_l.lookup(37.3318, -121.8899)
check(f"exceedance reads properties.value (={et.get('value')})", et["value"] == 7.0)

print("\n[4] Banding with duration")
check("36.4C alone -> HIGH", classify(36.4) == RiskLevel.HIGH)
check("36.4C + 7h -> EXTREME (duration escalates)", classify(36.4, 7.0) == RiskLevel.EXTREME)

print("\n[5] env_params hot-hour selection")
from safety_rider.heat_risk import _hot_hour_heat_index, _series
hi = _hot_hour_heat_index(FakeClient(), SJ, 36.4, "TESTDATE")
# apparent peaks near midday (i=12); heat_index there = 40-12 = 28
check(f"reads heat index at the APPARENT-temp peak, not the overnight max (got {hi})", hi == 28.0)
check("_series reads the real nested envelope",
      _series({"locations": [{"parameters": {"x": [1,2,3]}}]}, "x") == [1.0,2.0,3.0])
check("_series rejects a top-level series (the old wrong shape)",
      _series({"x": [1,2,3]}, "x") == [])
check("_series rejects an all-None series", 
      _series({"locations": [{"parameters": {"x": [None]*24}}]}, "x") == [])
check("_series tolerates junk", _series({"locations": "nope"}, "x") == [])

# ── Regression against a REAL live API response ─────────────────────────────
# Captured 2026-08-20 from one deliberate env_params call over San Jose and
# committed as a fixture (4 KB). This is the shape that broke the first parser:
# series nested under locations[0].parameters, not at the top level.
print("\n[6] Real live env_params response (fixture)")
fixture = pathlib.Path(__file__).parent / "fixtures" / "env_params_live_san_jose_2026-08-19.json"
live = json.loads(fixture.read_text())
ap_l = _series(live, "apparent_temperature_celsius")
hi_l = _series(live, "heat_index_celsius")
check(f"apparent series parsed from live response (n={len(ap_l)})", len(ap_l) == 24)
check(f"heat_index series parsed from live response (n={len(hi_l)})", len(hi_l) == 24)
hot_l = max(range(len(ap_l)), key=lambda i: ap_l[i])
check(f"hot hour is afternoon, not overnight (got {hot_l:02d}:00)", 11 <= hot_l <= 18)
naive_l = max(hi_l)
check(f"reported {hi_l[hot_l]:.1f}C beats naive max {naive_l:.1f}C at {hi_l.index(naive_l):02d}:00 "
      f"(avoids +{naive_l - hi_l[hot_l]:.1f}C artifact)", naive_l - hi_l[hot_l] > 20)
check("naive max would be physically absurd (>60C)", naive_l > 60)

for p in written: p.unlink(missing_ok=True)
for p in pathlib.Path('data/env_params').glob('env_params_rider_*TESTDATE*'):
    p.unlink(missing_ok=True)
print("\n" + ("ALL LIVE-PATH CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
raise SystemExit(0 if ok else 1)
