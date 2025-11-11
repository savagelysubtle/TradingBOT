import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Backtest from "./pages/Backtest";
import Strategies from "./pages/Strategies";
import DataFetch from "./pages/DataFetch";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/strategies" element={<Strategies />} />
        <Route path="/data" element={<DataFetch />} />
      </Routes>
    </Layout>
  );
}

export default App;

