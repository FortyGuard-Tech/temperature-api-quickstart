import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const backendRes = await fetch('http://localhost:8000/api/v1/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (backendRes.ok) {
      const data = await backendRes.json();
      return NextResponse.json(data);
    }
  } catch (err) {
    console.warn('Proxy simulate request failed, computing fallback...', err);
  }

  // Local fallback calculation
  const { roof_area = 1200, target_albedo = 0.7, canopy_area = 250 } = await req.json();
  const cool_roof_drop = (roof_area / 1000.0) * 2.5 * (target_albedo - 0.2);
  const greenery_drop = (canopy_area / 1000.0) * 1.8;
  const total_drop = cool_roof_drop + greenery_drop;
  const annual_savings = roof_area * 4.5;
  const payback = (roof_area * 25.0) / annual_savings;

  return NextResponse.json({
    status: "success",
    simulation: {
      projected_temp_drop_f: Number(total_drop.toFixed(2)),
      annual_hvac_savings_usd: Number(annual_savings.toFixed(2)),
      payback_years: Number(payback.toFixed(1)),
      cool_roof_drop_f: Number(cool_roof_drop.toFixed(2)),
      greenery_drop_f: Number(greenery_drop.toFixed(2)),
      co2_reduction_tons: Number((roof_area * 0.015).toFixed(2)),
      estimated_retrofit_cost_usd: Number((roof_area * 25.0).toFixed(2))
    }
  });
}
