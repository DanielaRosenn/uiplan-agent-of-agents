import { test, expect } from '@playwright/test';

test.describe('AS-IS and TO-BE Views', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5176/');
    await expect(page.getByText('TO-BE WORKFLOW BUILDER', { exact: true })).toBeVisible({ timeout: 15000 });
  });

  test('should open with a clean UiPlan overview and drill-down tabs', async ({ page }) => {
    await page.getByLabel('UiPlan view mode').getByRole('button', { name: 'OVERVIEW' }).click();
    await expect(page.getByText('PLAN SOURCES')).toBeVisible();
    await expect(page.getByText('IMPLEMENTATION HEALTH')).toBeVisible();
    await expect(page.getByText(/51\/61 done/i)).toBeVisible();

    const asIsTab = page.getByRole('button', { name: /AS-IS/i });
    await expect(asIsTab).toBeVisible({ timeout: 5000 });
    const toBeTab = page.getByRole('button', { name: /TO-BE/i });
    await expect(toBeTab).toBeVisible();

    await page.screenshot({ path: 'test-results/uiplan-overview.png' });
  });

  test('should show AS-IS and TO-BE as planning nodes in the project map', async ({ page }) => {
    await page.getByRole('button', { name: /PROJECT MAP/i }).click();

    await expect(page.getByText('AS-IS (Manual Process)').first()).toBeVisible();
    await expect(page.getByText('TO-BE (Automated Solution)').first()).toBeVisible();
    await expect(page.getByText('ApprovalFlow.xaml')).toHaveCount(0);

    await page.screenshot({ path: 'test-results/project-map-planning-nodes.png', fullPage: true });
  });

  test('should render AS-IS canvas with swim lanes', async ({ page }) => {
    await page.getByRole('button', { name: /AS-IS/i }).click();

    await expect(page.getByText('AS-IS MANUAL PROCESS')).toBeVisible();
    await expect(page.getByText(/BUSINESS FRICTION/i)).toBeVisible();
    await expect(page.getByText('ACTOR 1')).toBeVisible();
    await expect(page.getByRole('button', { name: /Sales Rep.*Manager/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Finance.*CRO/i })).toBeVisible();
    await expect(page.getByText('Renewal pricing request')).toBeVisible();

    await page.screenshot({ path: 'test-results/as-is-canvas.png', fullPage: true });
  });

  test('navigate to player-level drill-down and backtrack with context', async ({ page }) => {
    await page.getByRole('button', { name: /AS-IS/i }).click();
    await page.getByRole('button', { name: /ACTOR 1 Sales Rep/i }).click();
    await expect(page.getByText(/DRILL LEVEL: L1/i)).toBeVisible();

    await page.getByRole('button', { name: /Sales Rep.*Manager/i }).click();
    await expect(page.getByText(/DRILL LEVEL: L2/i)).toBeVisible();
    await expect(page.getByText(/L2 Sales Rep -> Manager/i)).toBeVisible();

    await page.getByRole('button', { name: /DRILL BACK/i }).click();
    await expect(page.getByText(/DRILL LEVEL: L1/i)).toBeVisible();
  });

  test('should render TO-BE canvas with architecture buckets', async ({ page }) => {
    await page.getByLabel('UiPlan view mode').getByRole('button', { name: 'TO-BE' }).click();

    await expect(page.getByText('TO-BE WORKFLOW BUILDER', { exact: true })).toBeVisible();
    await expect(page.getByText(/L0 solution flow, L1 stage drill-down, L2 design contract/i)).toBeVisible();
    await expect(page.getByText('Trigger', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Ingress', { exact: true })).toBeVisible();
    await expect(page.getByText('Reason', { exact: true })).toBeVisible();
    await expect(page.getByText('Act', { exact: true })).toBeVisible();
    await expect(page.getByText('Observe', { exact: true })).toBeVisible();
    await expect(page.getByText('End', { exact: true })).toBeVisible();
    await expect(page.getByText('Slack request received', { exact: true })).toBeVisible();
    await expect(page.getByText('Normalize renewal request', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Route approval policy', { exact: true })).toBeVisible();
    await expect(page.getByText('Create approval task', { exact: true })).toBeVisible();
    await expect(page.getByText('Update Salesforce quote', { exact: true })).toBeVisible();
    await expect(page.getByText('Write audit evidence', { exact: true })).toBeVisible();
    await expect(page.getByText('Reply in Slack', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Webhook to Main-Queue', { exact: true })).toHaveCount(0);
    await expect(page.getByText(/\.xaml/i)).toHaveCount(0);
    await expect(page.getByText(/OPEN CODE/i)).toHaveCount(0);
    await expect(page.getByText('Approval request', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Audit event', { exact: true }).first()).toBeVisible();

    await page.getByRole('button', { name: /Normalize renewal request Robot workflow/i }).click();
    await expect(page.getByText(/L0 SOLUTION > L1 Normalize renewal request/i)).toBeVisible();
    await expect(page.getByText('L2 sub-workflow canvas', { exact: true })).toBeVisible();

    await page.screenshot({ path: 'test-results/to-be-canvas.png', fullPage: true });
  });

  test('should expand workflow to show internal steps', async ({ page }) => {
    await page.getByLabel('UiPlan view mode').getByRole('button', { name: 'TO-BE' }).click();
    await expect(page.getByText('Workflow drill-down by player', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: /Sales Rep approval workflow Sub-workflow/i }).click();
    await expect(page.getByText(/L0 SOLUTION > L1 Sales Rep approval workflow/i)).toBeVisible();
    await expect(page.getByText('L2 UIPATH DESIGN CONTRACT', { exact: true })).toBeVisible();
    await expect(page.getByText('get credentials', { exact: true })).toBeVisible();

    await page.screenshot({ path: 'test-results/workflow-expanded.png', fullPage: true });
  });

  test('TO-BE controls remain responsive on small viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1180, height: 760 });
    await page.getByLabel('UiPlan view mode').getByRole('button', { name: 'TO-BE' }).click();
    await page.getByRole('button', { name: /Create approval task HITL/i }).click();
    await expect(page.getByText('TO-BE WORKFLOW BUILDER', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create approval task HITL' })).toBeVisible();
  });

  test('compare as-is versus to-be deltas', async ({ page }) => {
    await page.getByRole('button', { name: /COMPARE/i }).click();
    await expect(page.getByText('AS-IS PLAYERS')).toBeVisible();
    await expect(page.getByText('TO-BE COMPONENTS')).toBeVisible();
    await expect(page.getByText(/Delta summary: manual handoffs/i)).toBeVisible();
  });

  test('project map should expose planning contracts and skill coverage controls', async ({ page }) => {
    await page.getByRole('button', { name: /PROJECT MAP/i }).click();

    await expect(page.getByText('PROJECT MAP EXPLAINER')).toBeVisible();
    await expect(page.getByText('Plan contracts')).toBeVisible();
    await expect(page.getByText('Contract links')).toBeVisible();
    await expect(page.getByText('Intake and routing workflow', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Salesforce', { exact: true }).first()).toBeVisible();

    await page.getByRole('button', { name: /SHOW SKILL COVERAGE LINKS/i }).click();
    await expect(page.getByRole('button', { name: /HIDE SKILL COVERAGE LINKS/i })).toBeVisible();

    await page.getByText('uipath-rpa').first().click();
    await expect(page.getByText('WHAT THIS SKILL DOES')).toBeVisible();
  });
});
