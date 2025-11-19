import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BackendStatus } from "@/components/BackendStatus";
import { apiClient } from "@/lib/api";
import { Activity, TrendingUp, Database } from "lucide-react";

export default function Dashboard() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      console.log("[Dashboard] Starting status fetch...");
      console.log("[Dashboard] API base URL:", "/api");
      console.log("[Dashboard] Full endpoint:", "/api/status");

      try {
        console.log("[Dashboard] Calling apiClient.getStatus()...");
        const data = await apiClient.getStatus();
        console.log("[Dashboard] ✅ Status fetched successfully:", data);
        setStatus(data);
      } catch (error: any) {
        // Log detailed error information to console
        console.error("=".repeat(60));
        console.error("[Dashboard] ❌ FAILED TO FETCH STATUS");
        console.error("=".repeat(60));
        console.error("[Dashboard] Error Type:", error?.constructor?.name || typeof error);
        console.error("[Dashboard] Error Code:", error?.code);
        console.error("[Dashboard] Error Message:", error?.message);
        console.error("[Dashboard] Error Response:", error?.response);
        console.error("[Dashboard] Error Request:", error?.request);
        console.error("[Dashboard] Error Config:", error?.config);

        if (error?.response) {
          console.error("[Dashboard] Response Status:", error.response.status);
          console.error("[Dashboard] Response Data:", error.response.data);
          console.error("[Dashboard] Response Headers:", error.response.headers);
        }

        if (error?.request) {
          console.error("[Dashboard] Request URL:", error.request.responseURL);
          console.error("[Dashboard] Request Status:", error.request.status);
        }

        // Check error type
        const isTimeout = error?.code === 'ECONNABORTED' || error?.message?.includes('timeout');
        const isConnectionError = error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error');
        const isCorsError = error?.message?.includes('CORS') || error?.message?.includes('cross-origin');

        console.error("[Dashboard] Error Classification:");
        console.error("  - Is Timeout:", isTimeout);
        console.error("  - Is Connection Error:", isConnectionError);
        console.error("  - Is CORS Error:", isCorsError);
        console.error("=".repeat(60));

        // Set a default status so the page doesn't stay on "Loading..."
        // But don't show error message in UI - only in console
        setStatus({
          status: isTimeout || isConnectionError ? "offline" : "error",
          exchange: "N/A",
          data_provider: "N/A",
          sandbox_mode: false,
        });
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Trading bot status and overview</p>
      </div>

      <BackendStatus />

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold capitalize ${
              status?.status === "offline" || status?.status === "error"
                ? "text-red-600 dark:text-red-400"
                : ""
            }`}>
              {status?.status || "Unknown"}
            </div>
            <p className="text-xs text-muted-foreground">
              {status?.sandbox_mode !== undefined
                ? (status.sandbox_mode ? "Sandbox Mode" : "Live Mode")
                : "N/A"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Exchange</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{status?.exchange || "N/A"}</div>
            <p className="text-xs text-muted-foreground">Data Provider: {status?.data_provider}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Data Provider</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{status?.data_provider || "N/A"}</div>
            <p className="text-xs text-muted-foreground">Market data source</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

