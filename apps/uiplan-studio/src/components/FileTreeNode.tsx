import React, { useState } from "react";
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
}

export default function FileTreeNode({
  node,
  level,
  selectedNodeId,
  onSelectNodeId,
}: FileTreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const isSelected = node.originalNode?.id === selectedNodeId;

  const handleClick = () => {
    if (node.isFolder) {
      setIsExpanded(!isExpanded);
    }
    if (node.originalNode) {
      onSelectNodeId(node.originalNode.id);
    }
  };

  return (
    <>
      <div
        className={`file-tree-node ${isSelected ? "selected" : ""}`}
        style={{ paddingLeft: `${level * 20 + 8}px` }}
        onClick={handleClick}
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
        <div className="file-tree-children">
          {node.children.map((child) => (
            <FileTreeNode
              key={child.id}
              node={child}
              level={level + 1}
              selectedNodeId={selectedNodeId}
              onSelectNodeId={onSelectNodeId}
            />
          ))}
        </div>
      )}
    </>
  );
}
