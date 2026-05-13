type TelemetryPayload = Record<string, string | number | boolean | null | undefined>;

interface TelemetryEvent {
  name: string;
  count: number;
  lastAt: string;
  payload?: TelemetryPayload;
}

const STORAGE_KEY = "uiplan:ux-telemetry";

function readTelemetry(): Record<string, TelemetryEvent> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Record<string, TelemetryEvent>;
  } catch {
    return {};
  }
}

function writeTelemetry(data: Record<string, TelemetryEvent>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore storage failures to keep UX non-blocking
  }
}

export function trackUxEvent(name: string, payload?: TelemetryPayload) {
  if (typeof window === "undefined") return;
  const data = readTelemetry();
  const existing = data[name];
  data[name] = {
    name,
    count: existing ? existing.count + 1 : 1,
    lastAt: new Date().toISOString(),
    payload,
  };
  writeTelemetry(data);
}

export function loadUxTelemetry(): Record<string, TelemetryEvent> {
  if (typeof window === "undefined") return {};
  return readTelemetry();
}

