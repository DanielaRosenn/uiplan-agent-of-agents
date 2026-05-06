import React from "react";
import { render, screen } from "@testing-library/react";
import { expect, test, describe } from "vitest";

import CodeSnippetViewer from "../components/CodeSnippetViewer";

describe("CodeSnippetViewer", () => {
  test("renders code snippet with syntax highlighting", () => {
    const code = 'function hello() { return "world"; }';
    const { container } = render(<CodeSnippetViewer code={code} language="typescript" />);
    // Check that the code snippet container exists
    const codeSnippet = container.querySelector('.code-snippet');
    expect(codeSnippet).toBeInTheDocument();
    // Check that syntax highlighter rendered the code (look for individual tokens)
    expect(screen.getByText("function")).toBeInTheDocument();
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  test("displays line range in header", () => {
    const code = 'const x = 42;';
    render(<CodeSnippetViewer code={code} language="typescript" lines="10-15" />);
    expect(screen.getByText("10-15")).toBeInTheDocument();
  });

  test("renders without line range", () => {
    const code = 'console.log("test");';
    const { container } = render(<CodeSnippetViewer code={code} language="typescript" />);
    // Should render without crashing
    const codeSnippet = container.querySelector('.code-snippet');
    expect(codeSnippet).toBeInTheDocument();
    // Check for individual tokens
    expect(screen.getByText("console")).toBeInTheDocument();
    expect(screen.getByText("log")).toBeInTheDocument();
  });
});
