"use client";

import { useMemo, useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

type HistoryPoint = {
  date: string;
  close: number | null;
};

const RANGES = [1, 3, 5, 10] as const;

interface AnalysisData {
  data?: Record<string, unknown>[];
  signal?: string;
  latest_price?: number;
}

interface QualitativeSummary {
  qualitative_summary?: string;
  headlines?: { title?: string; link?: string; published_at?: string }[];
}

interface QuantitativeSummary {
  quantitative_summary?: string;
  latest_metrics?: Record<string, unknown>;
}

export default function SearchPage() {
  const params = useParams();
  const symbol = (params?.symbol as string)?.toUpperCase() || "";
  const [years, setYears] = useState<(typeof RANGES)[number]>(1);
  const [points, setPoints] = useState<HistoryPoint[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [qualitative, setQualitative] = useState<QualitativeSummary | null>(null);
  const [quantitative, setQuantitative] = useState<QuantitativeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const base = API_URL.replace(/\/$/, "");

  useEffect(() => {
    if (!symbol || !base || base === "undefined") {
      setLoading(false);
      setError("Invalid symbol or API not configured");
      return;
    }

    setLoading(true);
    setError(null);

    const loadHistory = async () => {
      try {
        const res = await fetch(
          `${base}/api/stocks/history/${encodeURIComponent(symbol)}?years=${years}`
        );
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to load history");
        setPoints((data.points || []).filter((p: HistoryPoint) => p.close !== null));
      } catch (err) {
        setPoints([]);
        setError(err instanceof Error ? err.message : "Failed to load stock data");
      }
    };

    const loadAnalysis = async () => {
      try {
        const res = await fetch(`${base}/analysis/${encodeURIComponent(symbol)}?days=30`);
        if (res.ok) {
          const data = await res.json();
          setAnalysis(data);
        }
      } catch {
        setAnalysis(null);
      }
    };

    const loadQualitative = async () => {
      try {
        const res = await fetch(
          `${base}/api/stocks/qualitative-summary/${encodeURIComponent(symbol)}?news_limit=5`
        );
        if (res.ok) {
          const data = await res.json();
          setQualitative(data);
        }
      } catch {
        setQualitative(null);
      }
    };

    const loadQuantitative = async () => {
      try {
        const res = await fetch(
          `${base}/api/stocks/quantitative-summary/${encodeURIComponent(symbol)}?days=252`
        );
        if (res.ok) {
          const data = await res.json();
          setQuantitative(data);
        }
      } catch {
        setQuantitative(null);
      }
    };

    Promise.all([
      loadHistory(),
      loadAnalysis(),
      loadQualitative(),
      loadQuantitative(),
    ]).finally(() => setLoading(false));
  }, [symbol, years, base]);

  const chart = useMemo(() => {
    if (!points.length) return null;
    const width = 900;
    const height = 300;
    const values = points.map((p) => p.close ?? 0);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = Math.max(max - min, 1);
    const polyline = points
      .map((p, index) => {
        const x = (index / Math.max(points.length - 1, 1)) * width;
        const y = height - (((p.close ?? min) - min) / range) * height;
        return `${x},${y}`;
      })
      .join(" ");
    return { width, height, min, max, polyline };
  }, [points]);

  const handleRangeChange = (range: (typeof RANGES)[number]) => {
    setYears(range);
  };

  if (!symbol) {
    return (
      <main style={{ padding: "2rem", textAlign: "center" }}>
        <p>No symbol provided.</p>
        <Link href="/" style={{ color: "#2563eb", textDecoration: "none" }}>
          ← Back to search
        </Link>
      </main>
    );
  }

  return (
    <main
      style={{
        maxWidth: "64rem",
        margin: "0 auto",
        padding: "1.5rem",
        minHeight: "100vh",
      }}
    >
      <header style={{ marginBottom: "1.5rem" }}>
        <Link
          href="/"
          style={{
            fontSize: "0.875rem",
            color: "#64748b",
            textDecoration: "none",
            marginBottom: "0.5rem",
            display: "inline-block",
          }}
        >
          ← Back to search
        </Link>
        <h1 style={{ fontSize: "1.75rem", marginBottom: "0.25rem" }}>
          {symbol}
        </h1>
        {analysis?.latest_price != null && (
          <p style={{ fontSize: "1.25rem", color: "#334155", fontWeight: 600 }}>
            ${analysis.latest_price.toFixed(2)}
            {analysis.signal && (
              <span
                style={{
                  marginLeft: "0.75rem",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  color:
                    analysis.signal.includes("Oversold")
                      ? "#059669"
                      : analysis.signal.includes("Overbought")
                        ? "#dc2626"
                        : "#64748b",
                }}
              >
                ({analysis.signal})
              </span>
            )}
          </p>
        )}
      </header>

      {loading && (
        <p style={{ color: "#64748b", marginBottom: "1rem" }}>
          Loading stock data...
        </p>
      )}

      {error && (
        <div
          style={{
            background: "#fee2e2",
            color: "#991b1b",
            borderRadius: "8px",
            padding: "0.75rem",
            marginBottom: "1rem",
          }}
        >
          {error}
        </div>
      )}

      {!loading && chart && (
        <section style={{ marginBottom: "2rem" }}>
          <div
            style={{
              display: "flex",
              gap: "0.5rem",
              alignItems: "center",
              marginBottom: "1rem",
              flexWrap: "wrap",
            }}
          >
            <span style={{ fontSize: "0.875rem", color: "#64748b" }}>
              Price history:
            </span>
            {RANGES.map((range) => (
              <button
                key={range}
                onClick={() => handleRangeChange(range)}
                style={{
                  padding: "0.375rem 0.75rem",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  background: years === range ? "#2563eb" : "#fff",
                  color: years === range ? "#fff" : "#334155",
                  cursor: "pointer",
                  fontSize: "0.875rem",
                }}
              >
                {range}Y
              </button>
            ))}
          </div>
          <div
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: "12px",
              padding: "1rem",
              background: "#fff",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
            }}
          >
            <svg
              viewBox={`0 0 ${chart.width} ${chart.height}`}
              style={{ width: "100%", height: "20rem", display: "block" }}
              role="img"
              aria-label={`${symbol} historical price chart`}
            >
              <polyline
                fill="none"
                stroke="#2563eb"
                strokeWidth="2"
                points={chart.polyline}
              />
            </svg>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: "0.5rem",
                fontSize: "0.875rem",
                color: "#64748b",
              }}
            >
              <span>Min: ${chart.min.toFixed(2)}</span>
              <span>Max: ${chart.max.toFixed(2)}</span>
              <span>Last: ${(points[points.length - 1]?.close ?? 0).toFixed(2)}</span>
            </div>
          </div>
        </section>
      )}

      <section style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {qualitative?.qualitative_summary && (
          <div
            style={{
              padding: "1rem",
              background: "#f8fafc",
              borderRadius: "12px",
              border: "1px solid #e2e8f0",
            }}
          >
            <h2 style={{ fontSize: "1rem", marginBottom: "0.5rem", color: "#334155" }}>
              Qualitative Summary
            </h2>
            <p style={{ fontSize: "0.9375rem", lineHeight: 1.6, color: "#475569", whiteSpace: "pre-wrap" }}>
              {qualitative.qualitative_summary}
            </p>
            {qualitative.headlines && qualitative.headlines.length > 0 && (
              <div style={{ marginTop: "1rem" }}>
                <h3 style={{ fontSize: "0.875rem", marginBottom: "0.5rem", color: "#64748b" }}>
                  Recent news
                </h3>
                <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem" }}>
                  {qualitative.headlines.slice(0, 5).map((n, i) => (
                    <li key={i} style={{ marginBottom: "0.25rem" }}>
                      {n.link ? (
                        <a
                          href={n.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: "#2563eb", textDecoration: "none" }}
                        >
                          {n.title || "Article"}
                        </a>
                      ) : (
                        n.title || "Article"
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {quantitative?.quantitative_summary && (
          <div
            style={{
              padding: "1rem",
              background: "#f8fafc",
              borderRadius: "12px",
              border: "1px solid #e2e8f0",
            }}
          >
            <h2 style={{ fontSize: "1rem", marginBottom: "0.5rem", color: "#334155" }}>
              Quantitative Summary
            </h2>
            <p style={{ fontSize: "0.9375rem", lineHeight: 1.6, color: "#475569", whiteSpace: "pre-wrap" }}>
              {quantitative.quantitative_summary}
            </p>
          </div>
        )}

        {analysis?.data && analysis.data.length > 0 && (
          <div
            style={{
              padding: "1rem",
              background: "#f8fafc",
              borderRadius: "12px",
              border: "1px solid #e2e8f0",
            }}
          >
            <h2 style={{ fontSize: "1rem", marginBottom: "0.5rem", color: "#334155" }}>
              Technical Data (last 5 days)
            </h2>
            <div style={{ overflowX: "auto" }}>
              <pre
                style={{
                  fontSize: "0.8125rem",
                  color: "#475569",
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {JSON.stringify(analysis.data, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
