import React, { useState } from "react";

import type { LibraryContextItem } from "../types";

interface LibraryContextPanelProps {
  items: LibraryContextItem[];
  onSearch: (query: string) => Promise<void>;
  onInsertCitation: (item: LibraryContextItem) => void;
}

export default function LibraryContextPanel({
  items,
  onSearch,
  onInsertCitation,
}: LibraryContextPanelProps) {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) {
      return;
    }
    setIsLoading(true);
    try {
      await onSearch(query);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section aria-label="Library Context">
      <h2>Library Context</h2>
      <input
        aria-label="Library query"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search UiPath library..."
      />
      <button type="button" onClick={handleSearch} disabled={isLoading}>
        {isLoading ? "Searching..." : "Search library"}
      </button>
      {items.length === 0 ? (
        <p>No library results</p>
      ) : (
        <ul>
          {items.map((item) => {
            const citation = `${item.book_id}/${item.chapter_id}/${item.section_id}`;
            return (
              <li key={citation}>
                <p>{citation}</p>
                <p>{item.snippet}</p>
                <button type="button" onClick={() => onInsertCitation(item)}>
                  Insert citation
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
