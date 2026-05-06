import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

vi.mock("@copilotkit/react-core", async () => {
  const React = await import("react");
  const useCopilotReadable = vi.fn();
  const useCopilotAdditionalInstructions = vi.fn();
  const useCopilotAction = vi.fn();
  return {
    CopilotKit: ({
      children,
      runtimeUrl,
    }: {
      children: React.ReactNode;
      runtimeUrl?: string;
    }) =>
      React.createElement(
        "div",
        { "data-testid": "copilot-provider", "data-runtime-url": runtimeUrl },
        children,
      ),
    useCopilotAdditionalInstructions,
    useCopilotAction,
    useCopilotReadable,
  };
});

vi.mock("@copilotkit/react-ui", async () => {
  const React = await import("react");
  return {
    CopilotChat: () => React.createElement("div", { "data-testid": "copilot-chat" }, "Copilot"),
  };
});

if (!window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}
