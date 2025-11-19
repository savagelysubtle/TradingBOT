import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "./ui/alert";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { apiClient } from "@/lib/api";

export function BackendStatus() {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const checkBackend = async () => {
      const checkStartTime = Date.now();
      console.log(`[BackendStatus] 🔍 Starting backend connectivity check (${new Date().toISOString()})`);

      try {
        console.log("[BackendStatus] 📡 Attempting to connect to API server...");
        const statusData = await apiClient.getStatus();
        const checkDuration = Date.now() - checkStartTime;

        console.log(`[BackendStatus] ✅ Backend connection successful (${checkDuration}ms)`);
        console.log("[BackendStatus] 📊 Status data received:", statusData);

        // Check if status changed from offline to online
        if (isOnline === false || isOnline === null) {
          console.log("[BackendStatus] 🎉 Backend status changed: OFFLINE → ONLINE");
        }

        setIsOnline(true);
      } catch (error: any) {
        const checkDuration = Date.now() - checkStartTime;
        console.error(`[BackendStatus] ❌ Backend connection failed (${checkDuration}ms)`);

        // Check if status changed from online to offline
        if (isOnline === true) {
          console.error("[BackendStatus] 💥 Backend status changed: ONLINE → OFFLINE");
        }

        setIsOnline(false);

        // Enhanced error logging with diagnostics
        console.error("[BackendStatus] 🔍 Error classification:");
        if (error?.code === 'ECONNABORTED') {
          console.error("  - Type: TIMEOUT (15s limit exceeded)");
          console.error("  - Likely cause: API server not running or overloaded");
          console.error("  - Action: Check if API server is started");
        } else if (error?.code === 'ERR_NETWORK') {
          console.error("  - Type: NETWORK ERROR");
          console.error("  - Likely causes:");
          console.error("    * API server not running");
          console.error("    * Wrong server URL/port");
          console.error("    * Firewall blocking localhost");
          console.error("    * Network connectivity issues");
          console.error("  - Action: Check http://localhost:8000/docs in browser");
        } else if (error?.response) {
          console.error(`  - Type: SERVER ERROR (${error.response.status})`);
          console.error("  - Server responded but with error status");
          console.error("  - Action: Check API server logs for details");
        } else if (error?.request) {
          console.error("  - Type: NO RESPONSE");
          console.error("  - Request sent but no response received");
          console.error("  - Action: Check network connectivity and server status");
        } else {
          console.error("  - Type: UNKNOWN ERROR");
          console.error("  - Unexpected error occurred");
        }

        // Log connection diagnostics
        console.log("[BackendStatus] 🔧 Connection diagnostics:");
        console.log(`  - Attempted URL: ${window.location.origin}/api/status`);
        console.log(`  - Timestamp: ${new Date().toISOString()}`);
        console.log(`  - User agent: ${navigator.userAgent}`);
        console.log(`  - Online status: ${navigator.onLine ? 'Online' : 'Offline'}`);

        // Log error details for debugging
        console.error("[BackendStatus] 📋 Full error details:", {
          message: error?.message,
          code: error?.code,
          stack: error?.stack,
          response: error?.response?.data,
          request: error?.request
        });
      } finally {
        setChecking(false);
        console.log(`[BackendStatus] ⏱️  Backend check completed (${Date.now() - checkStartTime}ms total)`);
      }
    };

    checkBackend();
    // Check every 5 seconds
    const interval = setInterval(checkBackend, 5000);
    return () => clearInterval(interval);
  }, [isOnline]);

  if (checking) {
    return null;
  }

  if (!isOnline) {
    return (
      <Alert variant="destructive" className="mb-4">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Backend API Not Available</AlertTitle>
        <AlertDescription>
          The backend API server is not running or not responding on port 8000.
          <br />
          <br />
          <strong>To start the API server:</strong>
          <br />
          <code className="mt-2 block bg-muted p-2 rounded text-xs">
            uv run --python .venv\Scripts\python.exe -m uvicorn trading_bot.api.main:app --host 0.0.0.0 --port 8000 --reload
          </code>
          <br />
          Or use the VS Code task: <strong>Run API Server</strong> or <strong>Run GUI (API + Frontend)</strong>
          <br />
          <br />
          <strong>Verify the server is running:</strong> Open <a href="http://localhost:8000/docs" target="_blank" className="underline">http://localhost:8000/docs</a> in your browser
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

