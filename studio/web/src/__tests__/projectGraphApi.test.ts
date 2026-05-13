import { describe, expect, test, vi } from "vitest";

import { loadRefreshState } from "../projectGraph/api";

describe("project graph API", () => {
  test("loads the plan refresh state for a worktree", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ worktree_id: "demo", stamp: "123.4", source_count: 2 }),
    } as Response);

    const result = await loadRefreshState("pricing-bot");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/explorer/refresh-state?worktree=pricing-bot",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(result).toEqual({
      data: { worktree_id: "demo", stamp: "123.4", source_count: 2 },
      source: "api",
    });
  });
});
