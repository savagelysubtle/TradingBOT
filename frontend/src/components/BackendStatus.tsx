import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { apiClient } from "@/lib/api";

export function BackendStatus() {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        await apiClient.getStatus();
        setIsOnline(true);
      } catch (error) {
        setIsOnline(false);
      } finally {
        setChecking(false);
      }
    };

    checkBackend();
    // Check every 5 seconds
    const interval = setInterval(checkBackend, 5000);
    return () => clearInterval(interval);
  }, []);

  if (checking) {
    return null;
  }

  if (!isOnline) {
    return (
      <Alert variant="destructive" className="mb-4">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Backend API Not Available</AlertTitle>
        <AlertDescription>
          The backend API server is not running. Please start it with:
          <br />
          <code className="mt-2 block bg-muted p-2 rounded">
            scripts\start_api.bat
          </code>
          <br />
          Or use the VS Code task: <strong>Run API Server</strong>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert className="mb-4 border-green-500 bg-green-50 dark:bg-green-950">
      <CheckCircle2 className="h-4 w-4 text-green-600" />
      <AlertTitle className="text-green-800 dark:text-green-200">
        Backend Connected
      </AlertTitle>
      <AlertDescription className="text-green-700 dark:text-green-300">
        API server is running and ready
      </AlertDescription>
    </Alert>
  );
}

