import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ThermoAgent-AI | San Jose FortyGuard Thermal Intelligence Platform',
  description: 'Multi-agent urban heat anomaly detector and parametric cool-roof mitigation optimizer for San Jose.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-emerald-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
