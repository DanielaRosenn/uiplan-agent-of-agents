import React from "react";

import FileTreeNode, { type TreeNode } from "./FileTreeNode";
import type { DiagramNode, DiagramNodeKind } from "../types";

interface GraphExplorerPanelProps {
  nodes: DiagramNode[];
  selectedNodeId: string | null;
  onSelectNodeId: (nodeId: string) => void;
}

function buildTreeFromFlatNodes(nodes: DiagramNode[]): TreeNode[] {
  const treeMap = new Map<string, TreeNode>();
  const rootNodes: TreeNode[] = [];

  nodes.forEach((node) => {
    if (node.title.includes("/")) {
      const parts = node.title.split("/");
      let currentPath = "";

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        const isLast = i === parts.length - 1;
        currentPath = currentPath ? `${currentPath}/${part}` : part;

        if (!treeMap.has(currentPath)) {
          const treeNode: TreeNode = {
            id: currentPath,
            title: part,
            kind: isLast ? (node.kind as DiagramNodeKind) : "folder",
            isFolder: !isLast,
            children: [],
            originalNode: isLast ? node : undefined,
          };

          if (i === 0) {
            rootNodes.push(treeNode);
          } else {
            const parentPath = parts.slice(0, i).join("/");
            const parent = treeMap.get(parentPath);
            if (parent) {
              parent.children.push(treeNode);
            }
          }

          treeMap.set(currentPath, treeNode);
        } else if (isLast) {
          const existingNode = treeMap.get(currentPath);
          if (existingNode) {
            existingNode.originalNode = node;
            existingNode.kind = node.kind as DiagramNodeKind;
          }
        }
      }
    } else {
      const treeNode: TreeNode = {
        id: node.id,
        title: node.title,
        kind: node.kind,
        isFolder: false,
        children: [],
        originalNode: node,
      };
      rootNodes.push(treeNode);
    }
  });

  return rootNodes;
}

export default function GraphExplorerPanel({
  nodes,
  selectedNodeId,
  onSelectNodeId,
}: GraphExplorerPanelProps) {
  const treeNodes = buildTreeFromFlatNodes(nodes);

  return (
    <section aria-label="Graph Explorer">
      <h2>Graph Explorer</h2>
      {nodes.length === 0 ? (
        <p className="muted">No graph nodes available.</p>
      ) : (
        <div className="file-tree">
          {treeNodes.map((treeNode) => (
            <FileTreeNode
              key={treeNode.id}
              node={treeNode}
              level={0}
              selectedNodeId={selectedNodeId}
              onSelectNodeId={onSelectNodeId}
            />
          ))}
        </div>
      )}
    </section>
  );
}
