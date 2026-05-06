import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import LibraryContextPanel from "../components/LibraryContextPanel";

test("searches library and inserts citation", async () => {
  const onSearch = vi.fn().mockResolvedValue(undefined);
  const onInsertCitation = vi.fn();

  render(
    <LibraryContextPanel
      items={[
        {
          book_id: "uipath-cli",
          chapter_id: "agent",
          section_id: "deploy",
          score: 5,
          snippet: "Deploy guidance",
        },
      ]}
      onSearch={onSearch}
      onInsertCitation={onInsertCitation}
    />,
  );

  fireEvent.change(screen.getByRole("textbox", { name: "Library query" }), {
    target: { value: "deploy" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Search library" }));
  await waitFor(() => expect(onSearch).toHaveBeenCalledWith("deploy"));

  fireEvent.click(screen.getByRole("button", { name: "Insert citation" }));
  expect(onInsertCitation).toHaveBeenCalledTimes(1);
});
