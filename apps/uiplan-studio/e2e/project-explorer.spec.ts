import { expect, test } from "@playwright/test";

test.describe("Project Explorer", () => {
  test.beforeEach(async ({ page }) => {
    // Mock the API responses
    await page.route("**/graph/index**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          version: "2.0",
          nodes: [
            {
              id: "src/App.tsx",
              type: "source_file",
              title: "src/App.tsx",
              summary: "Main application component",
              code: {
                path: "src/App.tsx",
                lines: "1-5",
                snippet: "import React from 'react';\n\nfunction App() {\n  return <div>Hello</div>;\n}",
                language: "typescript",
              },
            },
            {
              id: "src/components/Button.tsx",
              type: "source_file",
              title: "src/components/Button.tsx",
              summary: "Button component",
              code: {
                path: "src/components/Button.tsx",
                lines: "1-3",
                snippet: "export const Button = () => {\n  return <button>Click</button>;\n};",
                language: "typescript",
              },
            },
            {
              id: "src/utils/helpers.ts",
              type: "source_file",
              title: "src/utils/helpers.ts",
              summary: "Helper utilities",
              code: {
                path: "src/utils/helpers.ts",
                lines: "1-3",
                snippet: "export function formatDate(date: Date) {\n  return date.toISOString();\n}",
                language: "typescript",
              },
            },
          ],
          edges: [],
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
  });

  test("loads project and displays file tree", async ({ page }) => {
    await page.goto("/");
    
    // Wait for the Graph Explorer to be visible
    await expect(page.getByRole("heading", { name: "Graph Explorer" })).toBeVisible();
    
    // Verify that the root folder is visible
    const fileTree = page.locator('[role="tree"]');
    const srcFolder = fileTree.locator('[role="treeitem"]').filter({ hasText: /^src$/ });
    await expect(srcFolder).toBeVisible();
    
    // Use Expand All to see all files
    await page.getByRole("button", { name: "Expand All" }).click();
    
    // Verify that all file nodes are visible in the tree
    await expect(fileTree.getByText("App.tsx", { exact: true })).toBeVisible();
    await expect(fileTree.getByText("Button.tsx", { exact: true })).toBeVisible();
    await expect(fileTree.getByText("helpers.ts", { exact: true })).toBeVisible();
  });

  test("shows code snippet when file selected", async ({ page }) => {
    await page.goto("/");
    
    // Wait for the tree to load
    await expect(page.getByRole("heading", { name: "Graph Explorer" })).toBeVisible();
    
    // Expand the src folder first
    const srcFolder = page.locator('[role="treeitem"]').filter({ hasText: /^src$/ });
    await srcFolder.click();
    
    // Click on App.tsx
    const appFile = page.locator('[role="treeitem"]').filter({ hasText: /^App\.tsx$/ });
    await appFile.click();
    
    // Verify that the inspector shows the code snippet
    await expect(page.locator(".code-snippet")).toBeVisible();
    await expect(page.getByText(/import React/)).toBeVisible();
    await expect(page.getByText(/function App/)).toBeVisible();
  });

  test("navigates tree with expand/collapse and updates inspector", async ({ page }) => {
    await page.goto("/");
    
    // Wait for the tree to load
    await expect(page.getByRole("heading", { name: "Graph Explorer" })).toBeVisible();
    
    // Verify initial state - src folder should be expandable
    const fileTree = page.locator('[role="tree"]');
    const srcFolder = fileTree.locator('[role="treeitem"]').filter({ hasText: /^src$/ }).first();
    await expect(srcFolder).toHaveAttribute("aria-expanded", "false");
    
    // Expand the src folder
    await srcFolder.click();
    await expect(srcFolder).toHaveAttribute("aria-expanded", "true");
    
    // Verify that immediate children are now visible
    await expect(fileTree.getByText("App.tsx", { exact: true })).toBeVisible();
    await expect(fileTree.getByText("components", { exact: true })).toBeVisible();
    
    // Expand the components folder to see Button.tsx
    const componentsFolder = fileTree.locator('[role="treeitem"]').filter({ hasText: /^components$/ });
    await componentsFolder.click();
    await expect(fileTree.getByText("Button.tsx", { exact: true })).toBeVisible();
    
    // Select a file and verify inspector updates
    const appFile = fileTree.locator('[role="treeitem"]').filter({ hasText: /^App\.tsx$/ });
    await appFile.click();
    await expect(appFile).toHaveAttribute("aria-selected", "true");
    
    // Verify inspector shows the selected file's details
    await expect(page.getByRole("heading", { name: "src/App.tsx" })).toBeVisible();
    await expect(page.locator(".code-snippet")).toBeVisible();
    
    // Select a different file and verify inspector updates
    const buttonFile = fileTree.locator('[role="treeitem"]').filter({ hasText: /^Button\.tsx$/ });
    await buttonFile.click();
    await expect(buttonFile).toHaveAttribute("aria-selected", "true");
    
    // Verify inspector now shows the Button component
    await expect(page.getByRole("heading", { name: "src/components/Button.tsx" })).toBeVisible();
    await expect(page.getByText(/export const Button/)).toBeVisible();
    
    // Collapse the components folder
    await componentsFolder.click();
    await expect(componentsFolder).toHaveAttribute("aria-expanded", "false");
    
    // Collapse the src folder
    await srcFolder.click();
    await expect(srcFolder).toHaveAttribute("aria-expanded", "false");
  });

  test("expand all and collapse all buttons work", async ({ page }) => {
    await page.goto("/");
    
    // Wait for the tree to load
    await expect(page.getByRole("heading", { name: "Graph Explorer" })).toBeVisible();
    
    // Click "Expand All" button
    await page.getByRole("button", { name: "Expand All" }).click();
    
    // Verify all folders are expanded
    const fileTree = page.locator('[role="tree"]');
    const srcFolder = fileTree.locator('[role="treeitem"]').filter({ hasText: /^src$/ }).first();
    await expect(srcFolder).toHaveAttribute("aria-expanded", "true");
    
    // Verify all children are visible
    await expect(fileTree.getByText("App.tsx", { exact: true })).toBeVisible();
    await expect(fileTree.getByText("Button.tsx", { exact: true })).toBeVisible();
    await expect(fileTree.getByText("helpers.ts", { exact: true })).toBeVisible();
    
    // Click "Collapse All" button
    await page.getByRole("button", { name: "Collapse All" }).click();
    
    // Verify folders are collapsed
    await expect(srcFolder).toHaveAttribute("aria-expanded", "false");
  });
});
