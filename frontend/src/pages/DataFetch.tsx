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
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.fetchData(symbol, timeframe, limit);
      setData(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch data");
    } finally {
      setLoading(false);
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

