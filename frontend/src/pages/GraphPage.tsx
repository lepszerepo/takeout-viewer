import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { Link, useSearchParams } from "react-router-dom";
import { httpGet } from "../api";

interface Node {
  id: string;
  count: number;
  self?: boolean;
}

interface Edge {
  source: string | Node;
  target: string | Node;
  weight: number;
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
  stats?: any;
  center?: string;
}

export default function GraphPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [minWeight, setMinWeight] = useState(3);
  const [center, setCenter] = useState<string>(searchParams.get("person") || "");
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dim, setDim] = useState({ w: 1000, h: 600 });

  useEffect(() => {
    const obs = new ResizeObserver(() => {
      if (containerRef.current) {
        setDim({
          w: containerRef.current.clientWidth,
          h: Math.max(500, window.innerHeight - 280),
        });
      }
    });
    if (containerRef.current) obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    setLoading(true);
    const url = center
      ? `/api/graph/person/${encodeURIComponent(center)}?depth=1&min_weight=1`
      : `/api/graph/people?min_weight=${minWeight}&limit_edges=1500`;
    httpGet<GraphData>(url)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [minWeight, center]);

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.edges.map((e) => ({ ...e })),
    };
  }, [data]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-xl font-semibold">Graf relacji</h2>
        <div className="flex gap-2 items-center text-sm">
          {center ? (
            <>
              <span className="text-slate-600">Centrum:</span>
              <span className="font-mono bg-indigo-50 text-indigo-700 px-2 py-1 rounded">
                {center}
              </span>
              <button
                onClick={() => {
                  setCenter("");
                  setSearchParams({});
                }}
                className="text-slate-500 hover:text-slate-900 text-xs underline"
              >
                pokaż cały graf
              </button>
            </>
          ) : (
            <>
              <span className="text-slate-600">Minimalna waga krawędzi:</span>
              <input
                type="number"
                min={1}
                value={minWeight}
                onChange={(e) => setMinWeight(Math.max(1, Number(e.target.value) || 1))}
                className="w-20 border border-slate-300 rounded px-2 py-1"
              />
            </>
          )}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded p-2 text-xs text-slate-600">
        {loading
          ? "Obliczam graf..."
          : data
            ? `${data.nodes.length} węzłów · ${data.edges.length} krawędzi${data.stats ? ` (z ${data.stats.total_unique_edges} unikalnych)` : ""}`
            : "Brak danych"}
        {!center && <span className="ml-2 text-slate-400">Klik w węzeł → ego-graph tej osoby.</span>}
      </div>

      <div
        ref={containerRef}
        className="bg-white border border-slate-200 rounded overflow-hidden"
        style={{ height: dim.h }}
      >
        {data && (
          <ForceGraph2D
            graphData={graphData as any}
            width={dim.w}
            height={dim.h}
            nodeLabel={(n: any) => `${n.id} (${n.count})`}
            nodeRelSize={4}
            nodeColor={(n: any) => (n.self ? "#dc2626" : "#4f46e5")}
            nodeVal={(n: any) => Math.log2((n.count || 1) + 1)}
            linkColor={() => "rgba(100,116,139,0.4)"}
            linkWidth={(l: any) => Math.min(8, Math.log2((l.weight || 1) + 1))}
            linkLabel={(l: any) => `${l.weight}`}
            onNodeClick={(n: any) => {
              setCenter(n.id);
              setSearchParams({ person: n.id });
            }}
            cooldownTicks={120}
          />
        )}
      </div>

      {center && (
        <div className="text-sm">
          <Link
            to={`/mail?q=${encodeURIComponent(center)}`}
            className="text-indigo-600 underline"
          >
            Pokaż maile z udziałem {center} →
          </Link>
        </div>
      )}
    </div>
  );
}
