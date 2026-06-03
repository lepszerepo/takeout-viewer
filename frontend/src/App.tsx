import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import DatasetsPage from "./pages/DatasetsPage";
import EntitiesPage from "./pages/EntitiesPage";
import EventsPage from "./pages/EventsPage";
import GraphPage from "./pages/GraphPage";
import MailPage from "./pages/MailPage";
import PeoplePage from "./pages/PeoplePage";
import PersonPage from "./pages/PersonPage";
import SearchPage from "./pages/SearchPage";
import SourcesPage from "./pages/SourcesPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="/datasets" element={<DatasetsPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/mail" element={<MailPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/people" element={<PeoplePage />} />
        <Route path="/person/:email" element={<PersonPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/entities" element={<EntitiesPage />} />
        <Route path="/sources" element={<SourcesPage />} />
      </Route>
    </Routes>
  );
}
