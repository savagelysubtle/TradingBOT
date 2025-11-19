import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BackendStatus } from "@/components/BackendStatus";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiClient } from "@/lib/api";

export default function DataFetch() {
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1d");
  const [limit, setLimit] = useState(100);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetch = async () => {
    console.log(`[DataFetch] 📊 Starting data fetch for ${symbol}`);
    const fetchStartTime = Date.now();

    // Log data fetch configuration
    console.log("[DataFetch] 📋 Data fetch configuration:");
    console.log(`  - Symbol: ${symbol}`);
    console.log(`  - Timeframe: ${timeframe}`);
    console.log(`  - Limit: ${limit} records`);

    setLoading(true);
    setError(null);

    try {
      console.log("[DataFetch] 🔄 Calling apiClient.fetchData()...");
      const result = await apiClient.fetchData(symbol, timeframe, limit);
      const fetchDuration = Date.now() - fetchStartTime;

      console.log(`[DataFetch] ✅ Data fetch completed successfully (${fetchDuration}ms)`);
      console.log("[DataFetch] 📊 Data fetch results:");
      console.log(`  - Symbol: ${result.symbol}`);
      console.log(`  - Records returned: ${result.rows}`);
      console.log(`  - Data size: ${result.data ? result.data.length : 0} entries`);

      if (result.data && result.data.length > 0) {
        const firstEntry = result.data[0];
        const lastEntry = result.data[result.data.length - 1];
        console.log("  - Date range:");
        console.log(`    * First: ${firstEntry.timestamp || firstEntry.date || 'N/A'}`);
        console.log(`    * Last: ${lastEntry.timestamp || lastEntry.date || 'N/A'}`);

        // Basic data validation
        console.log("[DataFetch] 🔍 Data validation:");
        const hasOHLC = firstEntry.open !== undefined && firstEntry.high !== undefined &&
                        firstEntry.low !== undefined && firstEntry.close !== undefined;
        const hasVolume = firstEntry.volume !== undefined;

        console.log(`  - OHLC data: ${hasOHLC ? '✅ Present' : '❌ Missing'}`);
        console.log(`  - Volume data: ${hasVolume ? '✅ Present' : '❌ Missing'}`);

        if (hasOHLC) {
          console.log(`  - Sample OHLC: O=${firstEntry.open}, H=${firstEntry.high}, L=${firstEntry.low}, C=${firstEntry.close}`);
        }
        if (hasVolume) {
          console.log(`  - Sample Volume: ${firstEntry.volume}`);
        }
      } else {
        console.warn("[DataFetch] ⚠️  No data returned from API");
      }

      setData(result);
    } catch (err: any) {
      const fetchDuration = Date.now() - fetchStartTime;
      console.error(`[DataFetch] ❌ Data fetch failed after ${fetchDuration}ms`);

      // Detailed error analysis for data fetching
      console.error("[DataFetch] 🔍 Data fetch error analysis:");
      let errorMessage = "Failed to fetch data";

      if (err?.code === 'ECONNABORTED') {
        errorMessage = "Data fetch timed out - server may be overloaded";
        console.error("  - Timeout: Request took too long to complete");
        console.error("  - Possible solutions:");
        console.error("    * Reduce data limit");
        console.error("    * Check server resources");
        console.error("    * Try different timeframe");
      } else if (err?.code === 'ERR_NETWORK') {
        errorMessage = "Network error - cannot reach data API";
        console.error("  - Network interruption during data fetch");
        console.error("  - Check internet connection and server status");
      } else if (err?.response) {
        console.error(`  - Server error: ${err.response.status} ${err.response.statusText}`);
        console.error("  - Response data:", err.response.data);

        if (err.response.status === 400) {
          errorMessage = "Invalid data request parameters";
          console.error("  - Bad request: Check symbol format and parameters");
          console.error("  - Valid symbol examples: BTC/USDT, AAPL");
          console.error("  - Valid timeframes: 1m, 5m, 1h, 1d, etc.");
        } else if (err.response.status === 404) {
          errorMessage = "Symbol or data not found";
          console.error("  - Symbol may not exist or be unavailable");
          console.error("  - Check symbol spelling and format");
          console.error("  - Try a different symbol or data source");
        } else if (err.response.status === 429) {
          errorMessage = "Rate limit exceeded - too many requests";
          console.error("  - API rate limit hit");
          console.error("  - Wait a moment before trying again");
        } else if (err.response.status === 500) {
          errorMessage = "Server error during data retrieval";
          console.error("  - Internal server error");
          console.error("  - Check server logs for data source issues");
        } else if (err.response.status === 503) {
          errorMessage = "Data service temporarily unavailable";
          console.error("  - Service unavailable");
          console.error("  - Data provider may be down or rate limited");
        }
      } else {
        console.error("  - Unknown error during data fetch");
      }

      console.error("[DataFetch] 📋 Full data fetch error details:", {
        symbol: symbol,
        timeframe: timeframe,
        limit: limit,
        message: err?.message,
        code: err?.code,
        stack: err?.stack,
        response: err?.response?.data,
        fetch_duration_ms: fetchDuration
      });

      setError(err.response?.data?.detail || errorMessage);
    } finally {
      setLoading(false);
      const totalDuration = Date.now() - fetchStartTime;
      console.log(`[DataFetch] ⏱️  Data fetch operation completed (${totalDuration}ms total)`);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Fetch Market Data</h1>
        <p className="text-muted-foreground">Fetch historical market data for analysis</p>
      </div>

      <BackendStatus />

      <Card>
        <CardHeader>
          <CardTitle>Data Fetch Configuration</CardTitle>
          <CardDescription>Configure parameters for data fetching</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
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
          </div>
          <Button onClick={handleFetch} disabled={loading}>
            {loading ? "Fetching..." : "Fetch Data"}
          </Button>
          {error && <div className="text-red-500">{error}</div>}
        </CardContent>
      </Card>

      {data && (
        <Card>
          <CardHeader>
            <CardTitle>Data Preview</CardTitle>
            <CardDescription>
              {data.rows} rows fetched for {data.symbol}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">Date</th>
                    <th className="text-right p-2">Open</th>
                    <th className="text-right p-2">High</th>
                    <th className="text-right p-2">Low</th>
                    <th className="text-right p-2">Close</th>
                    <th className="text-right p-2">Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.slice(0, 10).map((row: any, idx: number) => (
                    <tr key={idx} className="border-b">
                      <td className="p-2">{row.timestamp || row.date || "-"}</td>
                      <td className="text-right p-2">{row.open?.toFixed(2)}</td>
                      <td className="text-right p-2">{row.high?.toFixed(2)}</td>
                      <td className="text-right p-2">{row.low?.toFixed(2)}</td>
                      <td className="text-right p-2">{row.close?.toFixed(2)}</td>
                      <td className="text-right p-2">{row.volume?.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

