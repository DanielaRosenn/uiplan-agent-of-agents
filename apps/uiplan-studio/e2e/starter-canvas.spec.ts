import { expect, test } from "@playwright/test";

import {
  createStarterProjectGraphTemplate,
  starterProjectGraphTemplateMetadata,
} from "../src/projectGraph/templates";

test("loads starter ProjectGraph canvas and selects the planning agent", async ({ page }) => {
  let starterTemplateRequests = 0;

  await page.route("**/bundle/load**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      }),
    });
  });

  await page.route("**/agent/context-sources", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ categories: [] }),
    });
  });

  await page.route("**/diagram/load**", async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "No saved diagram" }),
    });
  });

  await page.route("**/project-graph/templates/starter", async (route) => {
    starterTemplateRequests += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        metadata: starterProjectGraphTemplateMetadata,
        graph: createStarterProjectGraphTemplate(),
      }),
    });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "UiPlan Studio" })).toBeVisible();

  await page.getByRole("button", { name: "Load starter ProjectGraph" }).click();
  await expect.poll(() => starterTemplateRequests).toBe(1);

  const canvas = page.getByLabel("UiPath diagram builder");
  await expect(canvas.getByRole("heading", { name: "ProjectGraph canvas" })).toBeVisible();
  await expect(canvas.getByRole("button", { name: /Workflow Plan/i })).toBeVisible();
  await expect(canvas.getByRole("button", { name: /Ready\?/i })).toBeVisible();
  await expect(canvas.locator(".diagram-edge-success")).toHaveCount(1);
  await expect(canvas.locator(".diagram-edge-fallback")).toHaveCount(1);

  await canvas.getByRole("button", { name: /Workflow Plan/i }).click();

  const drilldown = page.getByLabel("Selected node drilldown");
  await expect(drilldown.getByText("agent")).toBeVisible();
  await expect(drilldown.getByText("central_action")).toBeVisible();
  await expect(drilldown.getByText("draft")).toBeVisible();
  await expect(page.getByText("ProjectGraph node: planning_agent")).toBeVisible();
});
