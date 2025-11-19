import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BackendStatus } from "@/components/BackendStatus";
import { apiClient, Strategy } from "@/lib/api";
import { CheckCircle2, XCircle } from "lucide-react";

export default function Strategies() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStrategies = async () => {
      console.log("[Strategies] 📋 Starting strategy list fetch for display...");
      const fetchStartTime = Date.now();

      try {
        console.log("[Strategies] 🔄 Calling apiClient.getStrategies()...");
        const data = await apiClient.getStrategies();
        const fetchDuration = Date.now() - fetchStartTime;

        console.log(`[Strategies] ✅ Strategy list fetched successfully (${fetchDuration}ms)`);
        console.log(`[Strategies] 📊 Total strategies received: ${data.length}`);

        const available = data.filter((s) => s.available);
        const unavailable = data.filter((s) => !s.available);

        console.log(`[Strategies] ✅ Available strategies: ${available.length}`);
        available.forEach(strategy => {
          console.log(`  - ${strategy.name} (${strategy.display_name}) - ✅ AVAILABLE`);
        });

        if (unavailable.length > 0) {
          console.log(`[Strategies] ⚠️  Unavailable strategies: ${unavailable.length}`);
          unavailable.forEach(strategy => {
            console.log(`  - ${strategy.name} (${strategy.display_name}) - ❌ NOT AVAILABLE`);
          });

          // Provide helpful suggestions for unavailable strategies
          console.log("[Strategies] 💡 Suggestions for unavailable strategies:");
          console.log("  - Check if required dependencies are installed (TA-Lib, scikit-learn, etc.)");
          console.log("  - Review server logs for import errors");
          console.log("  - Some strategies may require specific Python packages or GPU support");
        }

        // Analyze strategy distribution
        console.log("[Strategies] 📈 Strategy analysis:");
        console.log(`  - Total strategies: ${data.length}`);
        console.log(`  - Available: ${available.length} (${((available.length / data.length) * 100).toFixed(1)}%)`);
        console.log(`  - Unavailable: ${unavailable.length} (${((unavailable.length / data.length) * 100).toFixed(1)}%)`);

        setStrategies(data);
      } catch (error: any) {
        const fetchDuration = Date.now() - fetchStartTime;
        console.error(`[Strategies] ❌ Failed to fetch strategies (${fetchDuration}ms)`);

        // Detailed error analysis for strategy loading
        console.error("[Strategies] 🔍 Strategy fetch error analysis:");
        if (error?.code === 'ECONNABORTED') {
          console.error("  - Connection timeout - API server may not be running");
          console.error("  - Strategies require server to be running to load");
        } else if (error?.code === 'ERR_NETWORK') {
          console.error("  - Network error - cannot reach API server");
          console.error("  - Check if backend is running on localhost:8000");
        } else if (error?.response) {
          console.error(`  - Server error: ${error.response.status} ${error.response.statusText}`);
          console.error("  - Response data:", error.response.data);

          if (error.response.status === 500) {
            console.error("  - Server error: Strategies may not be loading properly");
            console.error("  - Check server logs for strategy import failures");
            console.error("  - Common issues:");
            console.error("    * Missing TA-Lib installation");
            console.error("    * GPU/CUDA issues with ML strategies");
            console.error("    * Python import errors");
          }
        } else {
          console.error("  - Unknown error during strategy loading");
        }

        console.error("[Strategies] 📋 Full strategy fetch error details:", {
          message: error?.message,
          code: error?.code,
          stack: error?.stack,
          response: error?.response?.data,
          fetch_duration_ms: fetchDuration
        });

        // Set empty array so UI shows no strategies instead of loading forever
        setStrategies([]);
      } finally {
        setLoading(false);
        const totalDuration = Date.now() - fetchStartTime;
        console.log(`[Strategies] ⏱️  Strategy fetch operation completed (${totalDuration}ms total)`);
      }
    };
    fetchStrategies();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Strategies</h1>
        <p className="text-muted-foreground">Available trading strategies</p>
      </div>

      <BackendStatus />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {strategies.map((strategy) => (
          <Card key={strategy.name}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{strategy.display_name}</CardTitle>
                {strategy.available ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
              <CardDescription>{strategy.name}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2">
                <span
                  className={`text-sm ${
                    strategy.available ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {strategy.available ? "Available" : "Not Available"}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

