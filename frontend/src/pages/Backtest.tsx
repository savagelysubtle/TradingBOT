import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BackendStatus } from "@/components/BackendStatus";
import { apiClient, Strategy, BacktestRequest } from "@/lib/api";

interface ParameterSchema {
  type: "integer" | "float" | "boolean";
  default: number | boolean;
  min?: number;
  max?: number;
  description?: string;
}

export default function Backtest() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({});
  const [paramSchema, setParamSchema] = useState<Record<string, ParameterSchema>>({});
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1d");
  const [limit, setLimit] = useState(365);
  const [engine, setEngine] = useState("custom");
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const data = await apiClient.getStrategies();
        const available = data.filter((s) => s.available);
        setStrategies(available);
        if (available.length > 0) {
          setSelectedStrategy(available[0].name);
        }
      } catch (err) {
        console.error("Failed to fetch strategies:", err);
      }
    };
    fetchStrategies();
  }, []);

  useEffect(() => {
    const fetchStrategyParams = async () => {
      if (!selectedStrategy) return;
      try {
        const info = await apiClient.getStrategyInfo(selectedStrategy);
        const params = info.parameters || {};
        setParamSchema(params);
        // Initialize params with defaults
        const defaults: Record<string, any> = {};
        Object.entries(params).forEach(([key, schema]: [string, any]) => {
          defaults[key] = schema.default;
        });
        setStrategyParams(defaults);
      } catch (err) {
        console.error("Failed to fetch strategy parameters:", err);
      }
    };
    fetchStrategyParams();
  }, [selectedStrategy]);

  const handleParamChange = (key: string, value: any) => {
    setStrategyParams((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleRunBacktest = async () => {
    if (!selectedStrategy) {
      setError("Please select a strategy");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const request: BacktestRequest = {
        strategy_name: selectedStrategy,
        symbol,
        timeframe,
        limit,
        engine,
        strategy_params: strategyParams,
      };
      const result = await apiClient.runBacktest(request);
      setResults(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to run backtest");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Backtest</h1>
        <p className="text-muted-foreground">Run backtests on trading strategies</p>
      </div>

      <BackendStatus />

      <Card>
        <CardHeader>
          <CardTitle>Backtest Configuration</CardTitle>
          <CardDescription>Configure parameters for backtesting</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="strategy">Strategy</Label>
              <Select value={selectedStrategy} onValueChange={setSelectedStrategy}>
                <SelectTrigger>
                  <SelectValue placeholder="Select strategy" />
                </SelectTrigger>
                <SelectContent>
                  {strategies.map((strategy) => (
                    <SelectItem key={strategy.name} value={strategy.name}>
                      {strategy.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Input
                id="symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="BTC/USDT"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeframe">Timeframe</Label>
              <Select value={timeframe} onValueChange={setTimeframe}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1m">1 Minute</SelectItem>
                  <SelectItem value="5m">5 Minutes</SelectItem>
                  <SelectItem value="15m">15 Minutes</SelectItem>
                  <SelectItem value="1h">1 Hour</SelectItem>
                  <SelectItem value="4h">4 Hours</SelectItem>
                  <SelectItem value="1d">1 Day</SelectItem>
                  <SelectItem value="1w">1 Week</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="limit">Limit</Label>
              <Input
                id="limit"
                type="number"
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value))}
                min={1}
                max={1000}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="engine">Engine</Label>
              <Select value={engine} onValueChange={setEngine}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="custom">Custom</SelectItem>
                  <SelectItem value="backtrader">Backtrader</SelectItem>
                  <SelectItem value="vectorbt">VectorBT</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {Object.keys(paramSchema).length > 0 && (
            <div className="space-y-4 border-t pt-4">
              <h3 className="text-lg font-semibold">Strategy Parameters</h3>
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(paramSchema).map(([key, schema]) => (
                  <div key={key} className="space-y-2">
                    <Label htmlFor={key}>
                      {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                    </Label>
                    {schema.type === "boolean" ? (
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id={key}
                          checked={strategyParams[key] ?? schema.default}
                          onCheckedChange={(checked) => handleParamChange(key, checked)}
                        />
                        <Label htmlFor={key} className="text-sm text-muted-foreground">
                          {schema.description}
                        </Label>
                      </div>
                    ) : schema.type === "integer" ? (
                      <Input
                        id={key}
                        type="number"
                        value={strategyParams[key] ?? schema.default}
                        onChange={(e) =>
                          handleParamChange(key, parseInt(e.target.value) || schema.default)
                        }
                        min={schema.min}
                        max={schema.max}
                        placeholder={schema.description}
                      />
                    ) : (
                      <Input
                        id={key}
                        type="number"
                        step="0.1"
                        value={strategyParams[key] ?? schema.default}
                        onChange={(e) =>
                          handleParamChange(key, parseFloat(e.target.value) || schema.default)
                        }
                        min={schema.min}
                        max={schema.max}
                        placeholder={schema.description}
                      />
                    )}
                    {schema.description && schema.type !== "boolean" && (
                      <p className="text-xs text-muted-foreground">{schema.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <Button onClick={handleRunBacktest} disabled={loading || !selectedStrategy}>
            {loading ? "Running..." : "Run Backtest"}
          </Button>
          {error && <div className="text-red-500">{error}</div>}
        </CardContent>
      </Card>

      {results && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Backtest Results</CardTitle>
              <CardDescription>
                Results for {results.strategy} on {results.symbol}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {Object.entries(results.results)
                    .filter(([key]) => !["trades", "portfolio_history", "kelly_metrics"].includes(key))
                    .map(([key, value]) => (
                      <div key={key} className="space-y-1">
                        <div className="text-sm font-medium capitalize text-muted-foreground">
                          {key.replace(/_/g, " ")}
                        </div>
                        <div className="text-2xl font-bold">
                          {typeof value === "number"
                            ? key.includes("pct") || key.includes("percent") || key.includes("rate")
                              ? `${(value * 100).toFixed(2)}%`
                              : value.toFixed(2)
                            : String(value)}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {results.results.trades && Array.isArray(results.results.trades) && results.results.trades.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Trades</CardTitle>
                <CardDescription>{results.results.trades.length} trades executed</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2">Date</th>
                        <th className="text-right p-2">Type</th>
                        <th className="text-right p-2">Price</th>
                        <th className="text-right p-2">Quantity</th>
                        <th className="text-right p-2">Value</th>
                        <th className="text-right p-2">PnL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.results.trades.slice(0, 50).map((trade: any, idx: number) => (
                        <tr key={idx} className="border-b">
                          <td className="p-2">{trade.date || trade.timestamp || trade.time || "-"}</td>
                          <td className={`text-right p-2 font-medium ${trade.type === "buy" || trade.side === "buy" ? "text-green-600" : "text-red-600"}`}>
                            {trade.type || trade.side || "-"}
                          </td>
                          <td className="text-right p-2">{trade.price?.toFixed(2) || "-"}</td>
                          <td className="text-right p-2">{trade.quantity?.toFixed(4) || trade.size?.toFixed(4) || "-"}</td>
                          <td className="text-right p-2">{trade.value?.toFixed(2) || "-"}</td>
                          <td className={`text-right p-2 font-medium ${trade.pnl >= 0 ? "text-green-600" : "text-red-600"}`}>
                            {trade.pnl !== undefined ? trade.pnl.toFixed(2) : "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {results.results.trades.length > 50 && (
                    <p className="text-sm text-muted-foreground mt-2">
                      Showing first 50 of {results.results.trades.length} trades
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {results.results.portfolio_history && Array.isArray(results.results.portfolio_history) && results.results.portfolio_history.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Portfolio History</CardTitle>
                <CardDescription>Portfolio value over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2">Date</th>
                        <th className="text-right p-2">Value</th>
                        <th className="text-right p-2">Cash</th>
                        <th className="text-right p-2">Holdings</th>
                        <th className="text-right p-2">Return</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.results.portfolio_history.slice(0, 50).map((entry: any, idx: number) => (
                        <tr key={idx} className="border-b">
                          <td className="p-2">{entry.date || entry.timestamp || entry.time || "-"}</td>
                          <td className="text-right p-2 font-medium">{entry.value?.toFixed(2) || entry.portfolio_value?.toFixed(2) || "-"}</td>
                          <td className="text-right p-2">{entry.cash?.toFixed(2) || "-"}</td>
                          <td className="text-right p-2">{entry.holdings?.toFixed(4) || entry.position?.toFixed(4) || "-"}</td>
                          <td className={`text-right p-2 ${(entry.return || entry.total_return || 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                            {entry.return !== undefined
                              ? `${(entry.return * 100).toFixed(2)}%`
                              : entry.total_return !== undefined
                              ? `${(entry.total_return * 100).toFixed(2)}%`
                              : "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {results.results.portfolio_history.length > 50 && (
                    <p className="text-sm text-muted-foreground mt-2">
                      Showing first 50 of {results.results.portfolio_history.length} entries
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {results.results.kelly_metrics && typeof results.results.kelly_metrics === "object" && (
            <Card>
              <CardHeader>
                <CardTitle>Kelly Criterion Metrics</CardTitle>
                <CardDescription>Optimal position sizing metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {Object.entries(results.results.kelly_metrics).map(([key, value]) => (
                    <div key={key} className="space-y-1">
                      <div className="text-sm font-medium capitalize text-muted-foreground">
                        {key.replace(/_/g, " ")}
                      </div>
                      <div className="text-xl font-bold">
                        {typeof value === "number"
                          ? key.includes("pct") || key.includes("percent") || key.includes("ratio")
                            ? value.toFixed(4)
                            : value.toFixed(2)
                          : String(value)}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

