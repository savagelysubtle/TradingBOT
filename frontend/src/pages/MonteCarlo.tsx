import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BackendStatus } from "@/components/BackendStatus";
import { apiClient, Strategy, MonteCarloRequest } from "@/lib/api";

interface ParameterSchema {
  type: "integer" | "float" | "boolean";
  default: number | boolean;
  min?: number;
  max?: number;
  description?: string;
}

export default function MonteCarlo() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({});
  const [paramSchema, setParamSchema] = useState<Record<string, ParameterSchema>>({});
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1d");
  const [limit, setLimit] = useState(365);
  const [method, setMethod] = useState("bootstrap");
  const [nSimulations, setNSimulations] = useState(1000);
  const [initialCapital, setInitialCapital] = useState(10000);
  const [commission, setCommission] = useState(0.001);
  const [slippage, setSlippage] = useState(0.0005);
  const [randomSeed, setRandomSeed] = useState<number | undefined>(undefined);
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [cancelling, setCancelling] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const progressIntervalRef = useRef<number | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<string>("disconnected");
  const [lastHeartbeat, setLastHeartbeat] = useState<Date | null>(null);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const [reconnectTimeout, setReconnectTimeout] = useState<NodeJS.Timeout | null>(null);
  const [lastMessageTime, setLastMessageTime] = useState<Date | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const connectionTimeoutMs = 60000; // 60 seconds without any message

  // Monitor connection timeout
  useEffect(() => {
    if (!eventSourceRef.current || connectionStatus !== "connected") return;

    const timeoutCheck = setInterval(() => {
      if (lastMessageTime) {
        const timeSinceLastMessage = Date.now() - lastMessageTime.getTime();
        if (timeSinceLastMessage > connectionTimeoutMs) {
          console.warn(`[MonteCarlo] ⚠️ Connection timeout: No messages for ${timeSinceLastMessage}ms. Checking job status...`);

          // First check if the job might have completed
          if (jobId) {
            apiClient.getMonteCarloJobStatus(jobId).then((status) => {
              if (status.status === "completed") {
                console.log(`[MonteCarlo] ✅ Job ${jobId} completed despite connection timeout. Fetching results...`);
                return apiClient.getMonteCarloJobResults(jobId);
              } else if (status.status === "failed") {
                throw new Error(status.error || "Job failed");
              } else {
                throw new Error("Connection timeout - job still running");
              }
            }).then((results) => {
              // Job completed successfully
              setResults(results);
              setLoading(false);
              setProgress(100);
            }).catch((error) => {
              console.error(`[MonteCarlo] ❌ Job status check failed: ${error.message}`);
              // Only trigger reconnection if job is still running
              if (eventSourceRef.current) {
                eventSourceRef.current.close();
                eventSourceRef.current = null;
              }
              setConnectionStatus("disconnected");
            });
          } else {
            // No job ID, just trigger reconnection
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
            setConnectionStatus("disconnected");
          }
        }
      }
    }, 5000); // Check every 5 seconds

    return () => clearInterval(timeoutCheck);
  }, [lastMessageTime, connectionStatus]);

  useEffect(() => {
    const fetchStrategies = async () => {
      console.log("[MonteCarlo] 📋 Starting strategy list fetch for Monte Carlo...");
      const fetchStartTime = Date.now();

      try {
        console.log("[MonteCarlo] 🔄 Calling apiClient.getStrategies()...");
        const data = await apiClient.getStrategies();
        const fetchDuration = Date.now() - fetchStartTime;

        console.log(`[MonteCarlo] ✅ Strategy list fetched successfully (${fetchDuration}ms)`);
        console.log(`[MonteCarlo] 📊 Total strategies received: ${data.length}`);

        const available = data.filter((s) => s.available);
        const unavailable = data.filter((s) => !s.available);

        console.log(`[MonteCarlo] ✅ Available strategies: ${available.length}`);
        available.forEach(strategy => {
          console.log(`  - ${strategy.name} (${strategy.display_name})`);
        });

        if (unavailable.length > 0) {
          console.log(`[MonteCarlo] ⚠️  Unavailable strategies: ${unavailable.length}`);
          unavailable.forEach(strategy => {
            console.log(`  - ${strategy.name} (${strategy.display_name}) - NOT AVAILABLE`);
          });
        }

        setStrategies(available);

        if (available.length > 0) {
          const defaultStrategy = available[0];
          console.log(`[MonteCarlo] 🎯 Auto-selecting default strategy: ${defaultStrategy.name}`);
          setSelectedStrategy(defaultStrategy.name);
        } else {
          console.warn("[MonteCarlo] ⚠️  No available strategies found for Monte Carlo!");
        }
      } catch (err: any) {
        const fetchDuration = Date.now() - fetchStartTime;
        console.error(`[MonteCarlo] ❌ Failed to fetch strategies (${fetchDuration}ms)`);

        // Detailed error analysis
        console.error("[MonteCarlo] 🔍 Error analysis:");
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

        console.error("[MonteCarlo] 📋 Full error details:", {
          message: err?.message,
          code: err?.code,
          stack: err?.stack,
          response: err?.response?.data
        });
      }
    };
    fetchStrategies();
  }, []);

  // Cleanup effect: abort any ongoing requests when component unmounts
  useEffect(() => {
    return () => {
      if (abortController) {
        abortController.abort();
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        setReconnectTimeout(null);
      }
    };
  }, [abortController, reconnectTimeout]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        console.log("[MonteCarlo] 🧹 Closing EventSource on unmount");
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeout) {
        console.log("[MonteCarlo] 🧹 Clearing reconnect timeout on unmount");
        clearTimeout(reconnectTimeout);
        setReconnectTimeout(null);
      }
    };
  }, [reconnectTimeout]);

  useEffect(() => {
    const fetchStrategyParams = async () => {
      if (!selectedStrategy) {
        console.log("[MonteCarlo] ⏭️  No strategy selected, skipping parameter fetch");
        return;
      }

      console.log(`[MonteCarlo] 📋 Fetching parameters for Monte Carlo strategy: ${selectedStrategy}`);
      const paramFetchStartTime = Date.now();

      try {
        console.log(`[MonteCarlo] 🔄 Calling apiClient.getStrategyInfo(${selectedStrategy})...`);
        const info = await apiClient.getStrategyInfo(selectedStrategy);
        const paramFetchDuration = Date.now() - paramFetchStartTime;

        console.log(`[MonteCarlo] ✅ Strategy info fetched successfully (${paramFetchDuration}ms)`);

        const params = info.parameters || {};
        console.log(`[MonteCarlo] 📊 Strategy parameters found: ${Object.keys(params).length}`);

        if (Object.keys(params).length > 0) {
          console.log("[MonteCarlo] 🔧 Monte Carlo parameter schema:");
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
          console.log("[MonteCarlo] ℹ️  Strategy has no configurable parameters for Monte Carlo");
        }

        setParamSchema(params);

        // Initialize params with defaults
        const defaults: Record<string, any> = {};
        Object.entries(params).forEach(([key, schema]: [string, any]) => {
          defaults[key] = schema.default;
          console.log(`[MonteCarlo] 🎛️  Setting default value for ${key}: ${schema.default}`);
        });

        setStrategyParams(defaults);
        console.log(`[MonteCarlo] ✅ Strategy parameters initialized with defaults for Monte Carlo`);
      } catch (err: any) {
        const paramFetchDuration = Date.now() - paramFetchStartTime;
        console.error(`[MonteCarlo] ❌ Failed to fetch strategy parameters for ${selectedStrategy} (${paramFetchDuration}ms)`);

        // Detailed error analysis
        console.error("[MonteCarlo] 🔍 Parameter fetch error analysis:");
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

        console.error("[MonteCarlo] 📋 Full parameter fetch error details:", {
          strategy: selectedStrategy,
          context: "Monte Carlo simulation setup",
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

  const handleCancel = () => {
    console.log("[MonteCarlo] 🛑 User requested simulation cancellation");

    if (abortController && !cancelling) {
      console.log("[MonteCarlo] 🔧 Aborting active Monte Carlo simulation...");
      setCancelling(true);

      // Clear progress interval
      if (progressIntervalRef.current) {
        console.log("[MonteCarlo] 🧹 Clearing progress simulation interval");
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }

      // Close EventSource connection
      if (eventSourceRef.current) {
        console.log("[MonteCarlo] 🧹 Closing EventSource connection");
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // Clear reconnect timeout
      if (reconnectTimeout) {
        console.log("[MonteCarlo] 🧹 Clearing reconnect timeout");
        clearTimeout(reconnectTimeout);
        setReconnectTimeout(null);
      }

      // Clear job state
      setJobId(null);
      setJobStatus(null);

      // Abort the request
      console.log("[MonteCarlo] 📡 Sending abort signal to API request");
      abortController.abort();

      console.log("[MonteCarlo] ✅ Cancellation request sent - waiting for cleanup");
    } else if (cancelling) {
      console.log("[MonteCarlo] ⏳ Cancellation already in progress");
    } else {
      console.log("[MonteCarlo] ⚠️  No active simulation to cancel");
    }
  };

  const handleRunMonteCarlo = async () => {
    console.log(`[MonteCarlo] 🎯 handleRunMonteCarlo called with selectedStrategy: ${selectedStrategy}`);

    if (!selectedStrategy) {
      const errorMsg = "Please select a strategy for Monte Carlo simulation";
      console.error(`[MonteCarlo] ❌ ${errorMsg}`);
      console.log(`[MonteCarlo] 📋 Available strategies:`, strategies.map(s => s.name));
      setError(errorMsg);
      return;
    }

    console.log(`[MonteCarlo] ✅ Strategy validation passed: ${selectedStrategy}`);

    console.log(`[MonteCarlo] 🎲 Starting Monte Carlo simulation for ${selectedStrategy}`);
    const simulationStartTime = Date.now();

    // Log Monte Carlo configuration
    console.log("[MonteCarlo] 📋 Monte Carlo simulation configuration:");
    console.log(`  - Strategy: ${selectedStrategy}`);
    console.log(`  - Symbol: ${symbol}`);
    console.log(`  - Timeframe: ${timeframe}`);
    console.log(`  - Data limit: ${limit} candles`);
    console.log(`  - Method: ${method}`);
    console.log(`  - Number of simulations: ${nSimulations}`);
    console.log(`  - Initial capital: $${initialCapital}`);
    console.log(`  - Commission: ${commission * 100}%`);
    console.log(`  - Slippage: ${slippage * 100}%`);
    console.log(`  - Random seed: ${randomSeed || 'random'}`);
    console.log(`  - Strategy parameters:`, strategyParams);

    // Create new AbortController for this request
    const controller = new AbortController();
    setAbortController(controller);
    console.log("[MonteCarlo] 🔧 Created AbortController for cancellation support");

    setLoading(true);
    setCancelling(false);
    setError(null);
    setProgress(0);
    setResults(null);

    try {
      const request: MonteCarloRequest = {
        strategy_name: selectedStrategy,
        symbol,
        timeframe,
        limit,
        method,
        n_simulations: nSimulations,
        initial_capital: initialCapital,
        commission,
        slippage,
        random_seed: randomSeed,
        strategy_params: strategyParams,
      };

      console.log("[MonteCarlo] 📊 Starting progress simulation (client-side)...");
      // Simulate progress (since we don't have real-time updates from API)
      const interval = setInterval(() => {
        setProgress((prev) => {
          const newProgress = prev + Math.random() * 5 + 2; // Random progress between 2-7%
          if (newProgress >= 90) {
            console.log("[MonteCarlo] ⏳ Progress simulation: reached 90%, waiting for completion...");
            if (progressIntervalRef.current) {
              clearInterval(progressIntervalRef.current);
              progressIntervalRef.current = null;
            }
            return 90;
          }
          return Math.min(newProgress, 90);
        });
      }, 500);
      progressIntervalRef.current = interval;

      console.log("[MonteCarlo] 🚀 Submitting Monte Carlo job to API...");
      console.log("[MonteCarlo] 📋 Request payload:", request);
      const apiCallStartTime = Date.now();

      try {
        const jobResponse = await apiClient.runMonteCarlo(request, controller.signal);
        const apiCallDuration = Date.now() - apiCallStartTime;

        console.log(`[MonteCarlo] ✅ Job submitted successfully (${apiCallDuration}ms API call)`);
        console.log("[MonteCarlo] 📊 Job submission response:", jobResponse);

      // Set job info and start streaming
      setJobId(jobResponse.job_id);
      setJobStatus("pending");
      setConnectionStatus("connecting");
      setLastHeartbeat(null);
      startJobStatusStreaming(jobResponse.job_id);

      } catch (apiError: any) {
        console.error("[MonteCarlo] ❌ API call failed:", apiError);
        console.error("[MonteCarlo] 📋 Error details:", {
          message: apiError.message,
          code: apiError.code,
          response: apiError.response?.data,
          status: apiError.response?.status
        });

        setError(`API Error: ${apiError.message}`);
        setLoading(false);
        return;
      }
    } catch (err: any) {
      const simulationDuration = Date.now() - simulationStartTime;

      // Clear interval on error
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }

      // Handle cancellation vs actual errors
      if (err.name === 'AbortError' || err.message?.includes('canceled') || err.code === 'ERR_CANCELED') {
        console.log(`[MonteCarlo] 🛑 Monte Carlo simulation cancelled by user (${simulationDuration}ms elapsed)`);
        setError("Simulation cancelled by user");
        setProgress(0);
        return;
      }

      console.error(`[MonteCarlo] ❌ Monte Carlo simulation failed after ${simulationDuration}ms`);

      // Detailed error analysis for Monte Carlo failures
      console.error("[MonteCarlo] 🔍 Monte Carlo error analysis:");
      let errorMessage = "Failed to run Monte Carlo simulation";

      if (err?.code === 'ECONNABORTED') {
        errorMessage = "Simulation timed out - may be too many simulations or server overloaded";
        console.error("  - Timeout: Simulation took too long to complete");
        console.error("  - Possible solutions:");
        console.error("    * Reduce number of simulations");
        console.error("    * Check server resources and GPU availability");
        console.error("    * Try different simulation method");
      } else if (err?.code === 'ERR_NETWORK') {
        errorMessage = "Network error - lost connection during simulation";
        console.error("  - Network interruption during execution");
        console.error("  - Check internet connection and server status");
      } else if (err?.response) {
        console.error(`  - Server error: ${err.response.status} ${err.response.statusText}`);
        console.error("  - Response data:", err.response.data);

        if (err.response.status === 400) {
          errorMessage = "Invalid simulation parameters - check settings";
          console.error("  - Bad request: Invalid parameters provided");
          console.error("  - Check simulation settings and parameter ranges");
        } else if (err.response.status === 404) {
          errorMessage = "Strategy or data not found for simulation";
          console.error("  - Strategy may not be available or data unavailable");
        } else if (err.response.status === 500) {
          errorMessage = "Server error during Monte Carlo execution";
          console.error("  - Internal server error");
          console.error("  - Check server logs for GPU/memory issues");
        } else if (err.response.status === 503) {
          errorMessage = "Server temporarily unavailable for simulations";
          console.error("  - Service unavailable, try again later");
          console.error("  - May be due to high server load or GPU issues");
        }
      } else {
        console.error("  - Unknown error during Monte Carlo execution");
      }

      console.error("[MonteCarlo] 📋 Full Monte Carlo error details:", {
        strategy: selectedStrategy,
        symbol: symbol,
        method: method,
        n_simulations: nSimulations,
        parameters: strategyParams,
        message: err?.message,
        code: err?.code,
        stack: err?.stack,
        response: err?.response?.data,
        simulation_duration_ms: simulationDuration
      });

      setError(err.response?.data?.detail || errorMessage);
      setProgress(0);
    } finally {
      setLoading(false);
      setCancelling(false);
      setAbortController(null);
      // Ensure intervals are cleared
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      if (statusPollingRef.current) {
        clearInterval(statusPollingRef.current);
        statusPollingRef.current = null;
      }

      // Clear job state
      setJobId(null);
      setJobStatus(null);

      const totalDuration = Date.now() - simulationStartTime;
      console.log(`[MonteCarlo] ⏱️  Monte Carlo operation completed (${totalDuration}ms total)`);
    }
  };

  const startJobStatusStreaming = (jobId: string, isReconnect = false) => {
    const attempt = reconnectAttemptsRef.current + 1;

    if (isReconnect) {
      console.log(`[MonteCarlo] 🔄 Attempting to reconnect EventSource for job ${jobId} (attempt ${attempt}/${maxReconnectAttempts})`);
      setConnectionAttempts(attempt);
    } else {
      console.log(`[MonteCarlo] 🔄 Starting status streaming for job ${jobId}`);
      reconnectAttemptsRef.current = 0;
      setConnectionAttempts(0);
    }

    // Close any existing EventSource
    if (eventSourceRef.current) {
      console.log("[MonteCarlo] 🧹 Closing existing EventSource");
      eventSourceRef.current.close();
    }

    // Clear any existing reconnect timeout
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      setReconnectTimeout(null);
    }

    // Create EventSource for Server-Sent Events
    const eventSource = new EventSource(`${import.meta.env.VITE_API_URL || '/api'}/monte-carlo/stream/${jobId}`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log(`[MonteCarlo] 📡 EventSource connected for job ${jobId}`);
      setConnectionStatus("connected");
      setLastHeartbeat(new Date());
      setLastMessageTime(new Date());
    };

    // Handle connection close (normal termination)
    eventSource.addEventListener('close', () => {
      console.log(`[MonteCarlo] 🔌 EventSource connection closed normally for job ${jobId}`);
      setConnectionStatus("disconnected");
      eventSourceRef.current = null;
    });

    eventSource.onmessage = (event) => {
      try {
        setLastMessageTime(new Date()); // Update last message time
        const data = JSON.parse(event.data);

        // Store the last received data globally for UI access
        (window as any).lastMonteCarloData = data;

        console.log(`[MonteCarlo] 📊 Received ${event.type} event:`, data);

        // Handle heartbeat messages
        if (event.type === 'heartbeat') {
          console.log(`[MonteCarlo] 💓 Heartbeat received for job ${jobId} at ${new Date(data.timestamp * 1000).toLocaleTimeString()}`);
          setLastHeartbeat(new Date(data.timestamp * 1000));
          return;
        }

        setJobStatus(data.status);

        if (event.type === 'complete') {
          // Job completed with results
          console.log(`[MonteCarlo] ✅ Job ${jobId} completed with results`);

          eventSource.close();
          eventSourceRef.current = null;

          // Clear progress interval
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          setProgress(100);

          // Results are already in the event data
          setResults(data);
          setLoading(false);

        } else if (event.type === 'cancelled') {
          console.log(`[MonteCarlo] 🛑 Job ${jobId} streaming cancelled`);
          // Don't close connection here, just log

        } else if (data.status === "failed") {
          // Job failed
          console.error(`[MonteCarlo] ❌ Job ${jobId} failed: ${data.error}`);

          eventSource.close();
          eventSourceRef.current = null;

          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          setProgress(0);

          setError(data.error || "Monte Carlo simulation failed");
          setLoading(false);
          setJobId(null);
          setJobStatus(null);

        } else if (data.status === "running") {
          // Update progress based on actual simulation progress
          if (data.progress && data.progress.percentage !== undefined) {
            const actualProgress = Math.min(90, data.progress.percentage);
            setProgress(actualProgress);
            console.log(`[MonteCarlo] 📊 Progress: ${data.progress.completed_simulations}/${data.progress.total_simulations} (${actualProgress.toFixed(1)}%)`);
          } else {
            // Fallback to elapsed time estimation if no progress data
            const elapsed = data.elapsed_seconds || 0;
            const estimatedProgress = Math.min(90, elapsed * 2); // Rough estimate
            setProgress(estimatedProgress);
          }
        }

      } catch (err: any) {
        console.error(`[MonteCarlo] ❌ Error parsing streaming data: ${err.message}`, event.data);
      }
    };

    eventSource.onerror = (error) => {
      console.error(`[MonteCarlo] ❌ EventSource error for job ${jobId}:`, error);
      setConnectionStatus("disconnected");

      eventSource.close();
      eventSourceRef.current = null;

      // Try to reconnect if we haven't exceeded max attempts and job is still active
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current += 1;
        const reconnectDelay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000); // Exponential backoff, max 30s

        console.log(`[MonteCarlo] ⏳ Scheduling reconnection in ${reconnectDelay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);

        const timeout = setTimeout(() => {
          startJobStatusStreaming(jobId, true);
        }, reconnectDelay);

        setReconnectTimeout(timeout);
      } else {
        console.error(`[MonteCarlo] ❌ Max reconnection attempts reached (${maxReconnectAttempts}). Giving up.`);

        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
          progressIntervalRef.current = null;
        }
        setProgress(0);
        setError("Connection lost during Monte Carlo simulation (max reconnection attempts reached)");
        setLoading(false);
        setJobId(null);
        setJobStatus(null);
      }
    };
  };

  const formatValue = (key: string, value: any): string => {
    if (typeof value === "number") {
      if (key.includes("pct") || key.includes("percent") || key.includes("rate") || key.includes("return") || key.includes("drawdown")) {
        return `${(value * 100).toFixed(2)}%`;
      }
      if (key.includes("ratio") || key.includes("factor")) {
        return value.toFixed(4);
      }
      if (key.includes("value") || key.includes("capital")) {
        return `$${value.toFixed(2)}`;
      }
      return value.toFixed(2);
    }
    return String(value);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Monte Carlo Simulation</h1>
        <p className="text-muted-foreground">
          Run thousands of simulations to assess strategy robustness and risk
        </p>
      </div>

      <BackendStatus />

      <Card>
        <CardHeader>
          <CardTitle>Simulation Configuration</CardTitle>
          <CardDescription>Configure parameters for Monte Carlo simulation</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Tabs defaultValue="strategy" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="strategy">Strategy</TabsTrigger>
              <TabsTrigger value="data">Data</TabsTrigger>
              <TabsTrigger value="simulation">Simulation</TabsTrigger>
            </TabsList>

            <TabsContent value="strategy" className="space-y-4 mt-4">
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
            </TabsContent>

            <TabsContent value="data" className="space-y-4 mt-4">
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
                  <Label htmlFor="limit">Data Points</Label>
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
              </div>
            </TabsContent>

            <TabsContent value="simulation" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="method">Method</Label>
                  <Select value={method} onValueChange={setMethod}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="bootstrap">Bootstrap Resampling</SelectItem>
                      <SelectItem value="shuffle_trades">Shuffle Trades</SelectItem>
                      <SelectItem value="randomize_returns">Randomize Returns</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {method === "bootstrap" && "Randomly sample from historical data"}
                    {method === "shuffle_trades" && "Randomize the order of trades"}
                    {method === "randomize_returns" && "Add random noise to returns"}
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="n_simulations">Number of Simulations</Label>
                  <Input
                    id="n_simulations"
                    type="number"
                    value={nSimulations || ""}
                    onChange={(e) => {
                      const val = parseInt(e.target.value);
                      setNSimulations(isNaN(val) ? 1000 : val);
                    }}
                    min={1}
                    max={10000}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="initial_capital">Initial Capital</Label>
                  <Input
                    id="initial_capital"
                    type="number"
                    value={initialCapital || ""}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setInitialCapital(isNaN(val) ? 10000 : val);
                    }}
                    min={1}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="commission">Commission Rate</Label>
                  <Input
                    id="commission"
                    type="number"
                    step="0.0001"
                    value={commission || ""}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setCommission(isNaN(val) ? 0.001 : val);
                    }}
                    min={0}
                    max={0.01}
                  />
                  <p className="text-xs text-muted-foreground">e.g., 0.001 = 0.1%</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="slippage">Slippage Rate</Label>
                  <Input
                    id="slippage"
                    type="number"
                    step="0.0001"
                    value={slippage || ""}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setSlippage(isNaN(val) ? 0.0005 : val);
                    }}
                    min={0}
                    max={0.01}
                  />
                  <p className="text-xs text-muted-foreground">e.g., 0.0005 = 0.05%</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="random_seed">Random Seed (Optional)</Label>
                  <Input
                    id="random_seed"
                    type="number"
                    value={randomSeed || ""}
                    onChange={(e) => {
                      const val = parseInt(e.target.value);
                      setRandomSeed(e.target.value && !isNaN(val) ? val : undefined);
                    }}
                    placeholder="Leave empty for random"
                  />
                  <p className="text-xs text-muted-foreground">For reproducibility</p>
                </div>
              </div>
            </TabsContent>
          </Tabs>

          {loading && (
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>
                    {cancelling ? "Cancelling simulation..." :
                     jobStatus ? `Job ${jobStatus}...` : "Submitting job..."}
                  </span>
                  <span>{progress}%</span>
                </div>
                <Progress value={progress} />
                {jobId && (
                  <div className="text-xs text-muted-foreground space-y-1">
                    <div>Job ID: {jobId}</div>
                    {(() => {
                      // Get the latest progress data from the last message
                      const lastData = window.lastMonteCarloData;
                      const progressInfo = lastData?.progress;
                      return progressInfo ? (
                        <div>Progress: {progressInfo.completed_simulations}/{progressInfo.total_simulations} simulations ({progressInfo.percentage.toFixed(1)}%)</div>
                      ) : null;
                    })()}
                    <div className="flex items-center gap-2">
                      <span>Connection:</span>
                      <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full ${
                        connectionStatus === 'connected' ? 'bg-green-100 text-green-800' :
                        connectionStatus === 'connecting' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {connectionStatus === 'connected' ? '🟢' :
                         connectionStatus === 'connecting' ? '🟡' : '🔴'}
                        {connectionStatus === 'connected' ? 'Connected' :
                         connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
                      </span>
                      {connectionAttempts > 0 && (
                        <span className="text-xs text-orange-600">
                          (Reconnect attempt: {connectionAttempts})
                        </span>
                      )}
                      {lastHeartbeat && connectionStatus === 'connected' && (
                        <span className="text-xs">
                          (Last heartbeat: {lastHeartbeat.toLocaleTimeString()})
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  onClick={handleCancel}
                  disabled={cancelling || !abortController}
                  className="flex-1"
                >
                  {cancelling ? "Cancelling..." : "❌ Cancel Simulation"}
                </Button>
              </div>
            </div>
          )}

          {!loading && (
            <Button onClick={handleRunMonteCarlo} disabled={!selectedStrategy}>
              Run Monte Carlo Simulation
            </Button>
          )}
          {error && <div className="text-red-500">{error}</div>}
        </CardContent>
      </Card>

      {results && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Simulation Results</CardTitle>
              <CardDescription>
                Results for {results.strategy} on {results.symbol} ({results.n_simulations}{" "}
                simulations, {results.method})
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <Tabs defaultValue="overview" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="returns">Returns</TabsTrigger>
                    <TabsTrigger value="risk">Risk Metrics</TabsTrigger>
                    <TabsTrigger value="performance">Performance</TabsTrigger>
                  </TabsList>

                  <TabsContent value="overview" className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="space-y-1">
                        <div className="text-sm font-medium text-muted-foreground">
                          Probability of Profit
                        </div>
                        <div className="text-2xl font-bold">
                          {results?.results?.probability_of_profit !== undefined ? formatValue("probability_of_profit", results.results.probability_of_profit) : "N/A"}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <div className="text-sm font-medium text-muted-foreground">Mean Return</div>
                        <div className="text-2xl font-bold">
                          {results?.results?.mean_return !== undefined ? formatValue("mean_return", results.results.mean_return) : "N/A"}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <div className="text-sm font-medium text-muted-foreground">Sharpe Ratio</div>
                        <div className="text-2xl font-bold">
                          {results?.results?.sharpe_ratio !== undefined ? formatValue("sharpe_ratio", results.results.sharpe_ratio) : "N/A"}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <div className="text-sm font-medium text-muted-foreground">
                          Worst Drawdown
                        </div>
                        <div className="text-2xl font-bold text-red-600">
                          {results?.results?.worst_drawdown !== undefined ? formatValue("worst_drawdown", results.results.worst_drawdown) : "N/A"}
                        </div>
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Execution time: {results?.execution_time_seconds ? `${results.execution_time_seconds}s` : "N/A"} | GPU Accelerated:{" "}
                      {results?.results?.gpu_accelerated ? "Yes" : "No"}
                    </div>
                  </TabsContent>

                  <TabsContent value="returns" className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {[
                        "mean_return",
                        "median_return",
                        "std_return",
                        "min_return",
                        "max_return",
                        "percentile_5",
                        "percentile_25",
                        "percentile_75",
                        "percentile_95",
                      ].map((key) => (
                        <div key={key} className="space-y-1">
                          <div className="text-sm font-medium capitalize text-muted-foreground">
                            {key.replace(/_/g, " ")}
                          </div>
                          <div className="text-xl font-bold">
                            {results.results[key] !== undefined
                              ? formatValue(key, results.results[key])
                              : "N/A"}
                          </div>
                        </div>
                      ))}
                    </div>
                  </TabsContent>

                  <TabsContent value="risk" className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {[
                        "mean_max_drawdown",
                        "median_max_drawdown",
                        "worst_drawdown",
                        "best_drawdown",
                        "var_95",
                        "cvar_95",
                        "sharpe_ratio",
                      ].map((key) => (
                        <div key={key} className="space-y-1">
                          <div className="text-sm font-medium capitalize text-muted-foreground">
                            {key.replace(/_/g, " ")}
                          </div>
                          <div className="text-xl font-bold">
                            {results.results[key] !== undefined
                              ? formatValue(key, results.results[key])
                              : "N/A"}
                          </div>
                        </div>
                      ))}
                    </div>
                  </TabsContent>

                  <TabsContent value="performance" className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {[
                        "mean_final_value",
                        "median_final_value",
                        "min_final_value",
                        "max_final_value",
                        "mean_win_rate",
                        "median_win_rate",
                        "mean_profit_factor",
                        "median_profit_factor",
                      ].map((key) => (
                        <div key={key} className="space-y-1">
                          <div className="text-sm font-medium capitalize text-muted-foreground">
                            {key.replace(/_/g, " ")}
                          </div>
                          <div className="text-xl font-bold">
                            {results.results[key] !== undefined
                              ? formatValue(key, results.results[key])
                              : "N/A"}
                          </div>
                        </div>
                      ))}
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

