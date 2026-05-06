import React from "react";

import type { ContextSourceCategory, ContextSource } from "../types";

interface ContextSourcesPanelProps {
  categories: ContextSourceCategory[];
  onAddSource: (source: ContextSource) => void;
}

export default function ContextSourcesPanel({
  categories,
  onAddSource,
}: ContextSourcesPanelProps) {
  return (
    <section aria-label="Context Sources">
      <h2>Context Sources</h2>
      {categories.length === 0 ? (
        <p>No context sources loaded</p>
      ) : (
        <div className="source-category-list">
          {categories.map((category) => (
            <section key={category.id} className="source-category">
              <h3>{category.title}</h3>
              <p className="muted">{category.description}</p>
              <ul className="source-card-list">
                {category.sources.map((source) => {
                  const isUnavailable = source.available === false;
                  return (
                    <li
                      key={`${category.id}-${source.id}`}
                      className={`source-card${isUnavailable ? " source-card-unavailable" : ""}`}
                    >
                      <div>
                        <span className="node-kind">{source.kind}</span>
                        {isUnavailable ? <span className="source-status">Unavailable</span> : null}
                        <strong>{source.title}</strong>
                        <p>{source.description}</p>
                        <p className="muted">{source.source}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => onAddSource(source)}
                        disabled={isUnavailable}
                        aria-label={
                          isUnavailable
                            ? `Unavailable: ${source.title} source`
                            : `Add ${source.title} source`
                        }
                      >
                        {isUnavailable ? "Unavailable" : `Add ${source.title} source`}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
      )}
    </section>
  );
}
