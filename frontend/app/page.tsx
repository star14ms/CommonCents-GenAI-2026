"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const [symbol, setSymbol] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = symbol.trim().toUpperCase();
    if (!clean) return;
    router.push(`/search/${encodeURIComponent(clean)}`);
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        background: "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%)",
      }}
    >
      <div
        style={{
          textAlign: "center",
          maxWidth: "32rem",
          width: "100%",
        }}
      >
        <h1
          style={{
            fontSize: "2.5rem",
            fontWeight: 700,
            marginBottom: "0.5rem",
            color: "#0f172a",
            letterSpacing: "-0.025em",
          }}
        >
          Stock Search
        </h1>
        <p
          style={{
            fontSize: "1rem",
            color: "#64748b",
            marginBottom: "2.5rem",
          }}
        >
          Search for any stock by symbol (e.g. AAPL, MSFT, GOOGL)
        </p>

        <form onSubmit={handleSearch} style={{ width: "100%" }}>
          <div
            style={{
              display: "flex",
              gap: "0.75rem",
              maxWidth: "28rem",
              margin: "0 auto",
              flexDirection: "column",
              alignItems: "stretch",
            }}
          >
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="Enter stock symbol..."
              autoFocus
              style={{
                width: "100%",
                padding: "1rem 1.25rem",
                fontSize: "1.125rem",
                border: "2px solid #e2e8f0",
                borderRadius: "12px",
                outline: "none",
                transition: "border-color 0.2s, box-shadow 0.2s",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = "#2563eb";
                e.target.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.15)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "#e2e8f0";
                e.target.style.boxShadow = "none";
              }}
            />
            <button
              type="submit"
              disabled={!symbol.trim()}
              style={{
                padding: "1rem 1.5rem",
                fontSize: "1rem",
                fontWeight: 600,
                borderRadius: "12px",
                border: "none",
                background: symbol.trim() ? "#2563eb" : "#94a3b8",
                color: "white",
                cursor: symbol.trim() ? "pointer" : "not-allowed",
                transition: "background 0.2s",
              }}
            >
              Search
            </button>
          </div>
        </form>

        <p
          style={{
            marginTop: "2rem",
            fontSize: "0.875rem",
            color: "#94a3b8",
          }}
        >
          <a href="/test" style={{ color: "#64748b", textDecoration: "none" }}>
            Developer test page →
          </a>
        </p>
      </div>
    </main>
  );
}
