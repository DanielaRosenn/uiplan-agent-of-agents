import { expect, test } from "@playwright/test";

test.describe("Studio Web live UI verification", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:5176/");
    await expect(page.getByText("TO-BE WORKFLOW BUILDER", { exact: true })).toBeVisible({
      timeout: 15000,
    });
  });

  test("captures TO-BE main view with workflow drill-down", async ({ page }) => {
    await page.getByLabel("UiPlan view mode").getByRole("button", { name: "TO-BE" }).click();

    await expect(page.getByText("TO-BE WORKFLOW BUILDER", { exact: true })).toBeVisible();
    await expect(
      page.getByText("Workflow drill-down by player", { exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /Sales Rep approval workflow Sub-workflow/i })).toBeVisible();

    await page.screenshot({
      path: "test-results/live-ui-to-be-main-view.png",
      fullPage: true,
    });
  });

  test("captures TO-BE player-level drill-down with breadcrumb and level", async ({ page }) => {
    await page.getByLabel("UiPlan view mode").getByRole("button", { name: "TO-BE" }).click();
    await page.getByRole("button", { name: /Sales Rep approval workflow Sub-workflow/i }).click();

    await expect(page.getByText(/L0 SOLUTION > L1 Sales Rep approval workflow/i)).toBeVisible();
    await expect(page.getByText("L2 UIPATH DESIGN CONTRACT", { exact: true })).toBeVisible();
    await expect(page.getByText("L2 sub-workflow canvas", { exact: true })).toBeVisible();

    await page.screenshot({
      path: "test-results/live-ui-player-drill-down-view.png",
      fullPage: true,
    });
  });

  test("captures compare view with explicit delta summary", async ({ page }) => {
    await page.getByRole("button", { name: /COMPARE/i }).click();

    await expect(page.getByText("AS-IS PLAYERS", { exact: true })).toBeVisible();
    await expect(page.getByText("TO-BE COMPONENTS", { exact: true })).toBeVisible();
    await expect(
      page.getByText(/Delta summary: manual handoffs \d+ -> automated assets \d+\./i),
    ).toBeVisible();

    await page.screenshot({
      path: "test-results/live-ui-compare-as-is-to-be-view.png",
      fullPage: true,
    });
  });
});
