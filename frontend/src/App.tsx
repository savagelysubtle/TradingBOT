import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Backtest from "./pages/Backtest";
import Strategies from "./pages/Strategies";
import DataFetch from "./pages/DataFetch";
import MonteCarlo from "./pages/MonteCarlo";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/strategies" element={<Strategies />} />
        <Route path="/data" element={<DataFetch />} />
        <Route path="/monte-carlo" element={<MonteCarlo />} />
      </Routes>
    </Layout>
  );
}

export default App;

