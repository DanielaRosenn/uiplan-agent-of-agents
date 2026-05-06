import { expect, test } from "vitest";

import { resolveApiBaseUrl } from "../config";

test("defaults API host to the current localhost hostname", () => {
  const baseUrl = resolveApiBaseUrl(undefined, new URL("http://127.0.0.1:5173/"));

  expect(baseUrl).toBe("http://127.0.0.1:8000");
});

test("honors an explicit API URL", () => {
  const baseUrl = resolveApiBaseUrl(
    "http://localhost:9000",
    new URL("http://127.0.0.1:5173/"),
  );

  expect(baseUrl).toBe("http://localhost:9000");
});
