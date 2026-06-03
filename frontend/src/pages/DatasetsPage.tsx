import ImportManager from "../components/ImportManager";

export default function DatasetsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Zarządzanie zrzutami Google Takeout</h2>
        <p className="text-sm text-slate-600 mt-1">
          Każdy podkatalog w <code>data/imports</code> to osobny zrzut. Rozpakuj kolejne archiwa do
          osobnych katalogów (np. <code>takeout_2024_01</code>, <code>takeout_2024_06</code>), a
          następnie odśwież listę.
        </p>
      </div>
      <ImportManager />
    </div>
  );
}
