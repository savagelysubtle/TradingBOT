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
      try {
        const data = await apiClient.getStrategies();
        setStrategies(data);
      } catch (error) {
        console.error("Failed to fetch strategies:", error);
      } finally {
        setLoading(false);
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

