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
import { BASE_CURRENCIES, QUOTE_CURRENCIES, combinePair } from "@/lib/cryptoPairs";

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
  const [baseCurrency, setBaseCurrency] = useState("BTC");
  const [quoteCurrency, setQuoteCurrency] = useState("USDT");
  const [timeframe, setTimeframe] = useState("1d");
  const [limit, setLimit] = useState(365);
  const [engine, setEngine] = useState("custom");
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Combine base and quote into symbol format
  const symbol = combinePair(baseCurrency, quoteCurrency);

  useEffect(() => {
    const fetchStrategies = async () => {
      console.log("[Backtest] 📋 Starting strategy list fetch...");
      const fetchStartTime = Date.now();

      try {
        console.log("[Backtest] 🔄 Calling apiClient.getStrategies()...");
        const data = await apiClient.getStrategies();
        const fetchDuration = Date.now() - fetchStartTime;

        console.log(`[Backtest] ✅ Strategy list fetched successfully (${fetchDuration}ms)`);
        console.log(`[Backtest] 📊 Total strategies received: ${data.length}`);

        const available = data.filter((s) => s.available);
        const unavailable = data.filter((s) => !s.available);

        console.log(`[Backtest] ✅ Available strategies: ${available.length}`);
        available.forEach(strategy => {
          console.log(`  - ${strategy.name} (${strategy.display_name})`);
        });

        if (unavailable.length > 0) {
          console.log(`[Backtest] ⚠️  Unavailable strategies: ${unavailable.length}`);
          unavailable.forEach(strategy => {
            console.log(`  - ${strategy.name} (${strategy.display_name}) - NOT AVAILABLE`);
          });
        }

        setStrategies(available);

        if (available.length > 0) {
          const defaultStrategy = available[0];
          console.log(`[Backtest] 🎯 Auto-selecting default strategy: ${defaultStrategy.name}`);
          setSelectedStrategy(defaultStrategy.name);
        } else {
          console.warn("[Backtest] ⚠️  No available strategies found!");
        }
      } catch (err: any) {
        const fetchDuration = Date.now() - fetchStartTime;
        console.error(`[Backtest] ❌ Failed to fetch strategies (${fetchDuration}ms)`);

        // Detailed error analysis
        console.error("[Backtest] 🔍 Error analysis:");
        if (err?.code === 'ECONNABORTED') {
          console.error("  - Connection timeout - API server may not be running");
        } else if (err?.code === 'ERR_NETWORK') {
          console.error("  - Network error - cannot reach API server");
        } else if (err?.response) {
          console.error(`  - Server error: ${err.response.status} ${err.response.statusText}`);
          console.error("  - Response data:", err.response.data);
        } else {
          console.error("  - Unknown error:", err.message);
        }

        console.error("[Backtest] 📋 Full error details:", {
          message: err?.message,
          code: err?.code,
          stack: err?.stack,
          response: err?.response?.data
        });
      }
    };
    fetchStrategies();
  }, []);

  useEffect(() => {
    const fetchStrategyParams = async () => {
      if (!selectedStrategy) {
        console.log("[Backtest] ⏭️  No strategy selected, skipping parameter fetch");
        return;
      }

      console.log(`[Backtest] 📋 Fetching parameters for strategy: ${selectedStrategy}`);
      const paramFetchStartTime = Date.now();

      try {
        console.log(`[Backtest] 🔄 Calling apiClient.getStrategyInfo(${selectedStrategy})...`);
        const info = await apiClient.getStrategyInfo(selectedStrategy);
        const paramFetchDuration = Date.now() - paramFetchStartTime;

        console.log(`[Backtest] ✅ Strategy info fetched successfully (${paramFetchDuration}ms)`);

        const params = info.parameters || {};
        console.log(`[Backtest] 📊 Strategy parameters found: ${Object.keys(params).length}`);

        if (Object.keys(params).length > 0) {
          console.log("[Backtest] 🔧 Parameter schema:");
          Object.entries(params).forEach(([key, schema]: [string, any]) => {
            console.log(`  - ${key}: ${schema.type} (default: ${schema.default})`);
            if (schema.description) {
              console.log(`    Description: ${schema.description}`);
            }
            if (schema.min !== undefined || schema.max !== undefined) {
              console.log(`    Range: ${schema.min || 'N/A'} to ${schema.max || 'N/A'}`);
            }
          });
        } else {
          console.log("[Backtest] ℹ️  Strategy has no configurable parameters");
        }

        setParamSchema(params);

        // Initialize params with defaults
        const defaults: Record<string, any> = {};
        Object.entries(params).forEach(([key, schema]: [string, any]) => {
          defaults[key] = schema.default;
          console.log(`[Backtest] 🎛️  Setting default value for ${key}: ${schema.default}`);
        });

        setStrategyParams(defaults);
        console.log(`[Backtest] ✅ Strategy parameters initialized with defaults`);
      } catch (err: any) {
        const paramFetchDuration = Date.now() - paramFetchStartTime;
        console.error(`[Backtest] ❌ Failed to fetch strategy parameters for ${selectedStrategy} (${paramFetchDuration}ms)`);

        // Detailed error analysis
        console.error("[Backtest] 🔍 Parameter fetch error analysis:");
        if (err?.code === 'ECONNABORTED') {
          console.error("  - Connection timeout - API server may be overloaded");
        } else if (err?.code === 'ERR_NETWORK') {
          console.error("  - Network error - cannot reach API server");
        } else if (err?.response) {
          console.error(`  - Server error: ${err.response.status} ${err.response.statusText}`);
          console.error("  - Response data:", err.response.data);
          if (err.response.status === 404) {
            console.error("  - Strategy not found - may be unavailable or misnamed");
          }
        } else {
          console.error("  - Unknown error:", err.message);
        }

        console.error("[Backtest] 📋 Full parameter fetch error details:", {
          strategy: selectedStrategy,
          message: err?.message,
          code: err?.code,
          stack: err?.stack,
          response: err?.response?.data
        });
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
      const errorMsg = "Please select a strategy";
      console.error(`[Backtest] ❌ ${errorMsg}`);
      setError(errorMsg);
      return;
    }

    console.log(`[Backtest] 🚀 Starting backtest execution for ${selectedStrategy}`);
    const backtestStartTime = Date.now();

    // Log backtest configuration
    console.log("[Backtest] 📋 Backtest configuration:");
    console.log(`  - Strategy: ${selectedStrategy}`);
    console.log(`  - Symbol: ${symbol} (${baseCurrency}/${quoteCurrency})`);
    console.log(`  - Timeframe: ${timeframe}`);
    console.log(`  - Data limit: ${limit} candles`);
    console.log(`  - Engine: ${engine}`);
    console.log(`  - Strategy parameters:`, strategyParams);

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

      console.log("[Backtest] 🔄 Sending backtest request to API...");
      const result = await apiClient.runBacktest(request);
      const backtestDuration = Date.now() - backtestStartTime;

      console.log(`[Backtest] ✅ Backtest completed successfully (${backtestDuration}ms)`);
      console.log("[Backtest] 📊 Backtest results summary:");
      console.log(`  - Status: ${result.status}`);
      console.log(`  - Strategy: ${result.strategy}`);
      console.log(`  - Symbol: ${result.symbol}`);

      if (result.results) {
        console.log("  - Key metrics:");
        Object.entries(result.results).forEach(([key, value]) => {
          if (typeof value === 'number' && !['trades', 'portfolio_history', 'kelly_metrics'].includes(key)) {
            console.log(`    * ${key}: ${value}`);
          }
        });

        if (result.results.trades && Array.isArray(result.results.trades)) {
          console.log(`  - Trades executed: ${result.results.trades.length}`);
        }
      }

      setResults(result);
    } catch (err: any) {
      const backtestDuration = Date.now() - backtestStartTime;
      console.error(`[Backtest] ❌ Backtest failed after ${backtestDuration}ms`);

      // Detailed error analysis for backtest failures
      console.error("[Backtest] 🔍 Backtest error analysis:");
      let errorMessage = "Failed to run backtest";

      if (err?.code === 'ECONNABORTED') {
        errorMessage = "Backtest timed out - server may be overloaded or backtest is too complex";
        console.error("  - Timeout: Backtest took too long to complete");
        console.error("  - Possible solutions:");
        console.error("    * Reduce data limit");
        console.error("    * Use VectorBT engine for faster execution");
        console.error("    * Check server resources");
      } else if (err?.code === 'ERR_NETWORK') {
        errorMessage = "Network error - lost connection during backtest";
        console.error("  - Network interruption during execution");
        console.error("  - Check internet connection and server status");
      } else if (err?.response) {
        console.error(`  - Server error: ${err.response.status} ${err.response.statusText}`);
        console.error("  - Response data:", err.response.data);

        if (err.response.status === 400) {
          errorMessage = "Invalid backtest parameters - check strategy settings";
          console.error("  - Bad request: Invalid parameters provided");
          console.error("  - Check parameter values and ranges");
        } else if (err.response.status === 404) {
          errorMessage = "Strategy or data not found";
          console.error("  - Strategy may not be available or data unavailable");
        } else if (err.response.status === 500) {
          errorMessage = "Server error during backtest execution";
          console.error("  - Internal server error");
          console.error("  - Check server logs for details");
        } else if (err.response.status === 503) {
          errorMessage = "Server temporarily unavailable";
          console.error("  - Service unavailable, try again later");
        }
      } else {
        console.error("  - Unknown error during backtest execution");
      }

      console.error("[Backtest] 📋 Full backtest error details:", {
        strategy: selectedStrategy,
        symbol: symbol,
        timeframe: timeframe,
        limit: limit,
        engine: engine,
        parameters: strategyParams,
        message: err?.message,
        code: err?.code,
        stack: err?.stack,
        response: err?.response?.data
      });

      setError(err.response?.data?.detail || errorMessage);
    } finally {
      setLoading(false);
      const totalDuration = Date.now() - backtestStartTime;
      console.log(`[Backtest] ⏱️  Backtest operation completed (${totalDuration}ms total)`);
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
              <Label htmlFor="base">Base Currency</Label>
              <Select value={baseCurrency} onValueChange={setBaseCurrency}>
                <SelectTrigger>
                  <SelectValue placeholder="Select base currency" />
                </SelectTrigger>
                <SelectContent>
                  {BASE_CURRENCIES.map((currency) => (
                    <SelectItem key={currency.symbol} value={currency.symbol}>
                      {currency.name} ({currency.symbol})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="quote">Quote Currency</Label>
              <Select value={quoteCurrency} onValueChange={setQuoteCurrency}>
                <SelectTrigger>
                  <SelectValue placeholder="Select quote currency" />
                </SelectTrigger>
                <SelectContent>
                  {QUOTE_CURRENCIES.map((currency) => (
                    <SelectItem key={currency.symbol} value={currency.symbol}>
                      {currency.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
                value={limit || ""}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  setLimit(isNaN(val) ? 365 : val);
                }}
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
                        value={strategyParams[key] ?? schema.default ?? ""}
                        onChange={(e) => {
                          const val = parseInt(e.target.value);
                          handleParamChange(key, isNaN(val) ? (schema.default ?? 0) : val);
                        }}
                        min={schema.min}
                        max={schema.max}
                        placeholder={schema.description}
                      />
                    ) : (
                      <Input
                        id={key}
                        type="number"
                        step="0.1"
                        value={strategyParams[key] ?? schema.default ?? ""}
                        onChange={(e) => {
                          const val = parseFloat(e.target.value);
                          handleParamChange(key, isNaN(val) ? (schema.default ?? 0) : val);
                        }}
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

