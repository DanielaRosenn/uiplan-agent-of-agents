import React from "react";
import { ChevronRight, ChevronDown } from "lucide-react";

import NodeIcon from "./NodeIcon";
import type { DiagramNode, DiagramNodeKind } from "../types";

export interface TreeNode {
  id: string;
  title: string;
  kind: DiagramNodeKind | "file" | "folder";
  isFolder: boolean;
  children: TreeNode[];
  originalNode?: DiagramNode;
}

interface FileTreeNodeProps {
  node: TreeNode;
  level: number;
  selectedNodeId: string | null;
  onSelectNodeId: (nodeId: string) => void;
  isExpanded: boolean;
  onToggleExpanded: (nodeId: string, isExpanded: boolean) => void;
  expandedNodes: Set<string>;
}

const FileTreeNode = React.memo(function FileTreeNode({
  node,
  level,
  selectedNodeId,
  onSelectNodeId,
  isExpanded,
  onToggleExpanded,
  expandedNodes,
}: FileTreeNodeProps) {
  const isSelected = node.originalNode?.id === selectedNodeId;

  const handleClick = () => {
    if (node.isFolder) {
      onToggleExpanded(node.id, !isExpanded);
    }
    if (node.originalNode) {
      onSelectNodeId(node.originalNode.id);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    } else if (e.key === "ArrowRight" && node.isFolder && !isExpanded) {
      e.preventDefault();
      onToggleExpanded(node.id, true);
    } else if (e.key === "ArrowLeft" && node.isFolder && isExpanded) {
      e.preventDefault();
      onToggleExpanded(node.id, false);
    }
  };

  return (
    <>
      <div
        className={`graph-explorer-file-tree-node ${isSelected ? "selected" : ""}`}
        style={{ paddingLeft: `${level * 20 + 8}px` }}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        role="treeitem"
        aria-expanded={node.isFolder ? isExpanded : undefined}
        aria-selected={isSelected}
        tabIndex={0}
      >
        {node.isFolder && (
          <span style={{ display: "inline-flex", width: "16px" }}>
            {isExpanded ? (
              <ChevronDown size={16} strokeWidth={2} />
            ) : (
              <ChevronRight size={16} strokeWidth={2} />
            )}
          </span>
        )}
        {!node.isFolder && <span style={{ width: "16px", display: "inline-block" }} />}
        <NodeIcon kind={node.kind} size={16} />
        <span>{node.title}</span>
      </div>
      {node.isFolder && isExpanded && node.children.length > 0 && (
        <div className="graph-explorer-file-tree-children" role="group">
          {node.children.map((child) => (
            <FileTreeNode
              key={child.id}
              node={child}
              level={level + 1}
              selectedNodeId={selectedNodeId}
              onSelectNodeId={onSelectNodeId}
              isExpanded={expandedNodes.has(child.id)}
              onToggleExpanded={onToggleExpanded}
              expandedNodes={expandedNodes}
            />
          ))}
        </div>
      )}
    </>
  );
});

export default FileTreeNode;
