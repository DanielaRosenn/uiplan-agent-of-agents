const DEFAULT_API_PORT = "8000";
const DEFAULT_API_HOST = "localhost";

interface LocationLike {
  protocol: string;
  hostname: string;
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

export function resolveApiBaseUrl(
  explicitUrl?: string,
  locationLike: LocationLike | undefined = typeof window !== "undefined"
    ? window.location
    : undefined,
): string {
  if (explicitUrl?.trim()) {
    return trimTrailingSlash(explicitUrl.trim());
  }

  const hostname =
    locationLike?.hostname === "127.0.0.1" || locationLike?.hostname === "localhost"
      ? locationLike.hostname
      : DEFAULT_API_HOST;
  const protocol = locationLike?.protocol === "https:" ? "https:" : "http:";

  return `${protocol}//${hostname}:${DEFAULT_API_PORT}`;
}
