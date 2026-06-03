import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { httpGet } from "../api";
import { DatasetOut } from "../types";
import { TopCorrespondent } from "../types_mail";

export default function PeoplePage() {
  const [datasets, setDatasets] = useState<DatasetOut[]>([]);
  const [datasetId, setDatasetId] = useState<number | undefined>();
  const [people, setPeople] = useState<TopCorrespondent[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    httpGet<DatasetOut[]>(`/api/datasets`).then(setDatasets).catch(() => setDatasets([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    const qs = datasetId ? `?dataset_id=${datasetId}&limit=200` : `?limit=200`;
    httpGet<TopCorrespondent[]>(`/api/mail/people/top${qs}`)
      .then(setPeople)
      .finally(() => setLoading(false));
  }, [datasetId]);

  const max = people[0]?.count || 1;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Najczęstsi korespondenci</h2>
      <div className="text-sm flex gap-2 items-center">
        <span className="text-slate-600">Zrzut:</span>
        <select
          value={datasetId ?? ""}
          onChange={(e) => setDatasetId(e.target.value ? Number(e.target.value) : undefined)}
          className="border border-slate-300 rounded px-2 py-1"
        >
          <option value="">— wszystkie —</option>
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>
      {loading && <div className="text-slate-500 text-sm">Ładowanie...</div>}
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="text-left px-3 py-2">E-mail</th>
              <th className="text-right px-3 py-2 w-32">Liczba</th>
              <th className="text-left px-3 py-2 w-64">Udział</th>
            </tr>
          </thead>
          <tbody>
            {people.map((p) => (
              <tr key={p.email} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2 font-mono text-xs">
                  <Link to={`/person/${encodeURIComponent(p.email)}`} className="text-indigo-700 hover:underline">
                    {p.email}
                  </Link>
                </td>
                <td className="px-3 py-2 text-right">{p.count.toLocaleString("pl-PL")}</td>
                <td className="px-3 py-2">
                  <div
                    className="h-3 bg-indigo-500 rounded"
                    style={{ width: `${Math.max(2, (p.count / max) * 100)}%` }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
