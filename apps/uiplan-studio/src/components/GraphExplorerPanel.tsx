import React, { useMemo, useState } from "react";

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
  const seenPaths = new Set<string>();

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
            if (seenPaths.has(currentPath)) {
              console.warn(`Duplicate path detected: ${currentPath}`);
            }
            existingNode.originalNode = node;
            existingNode.kind = node.kind as DiagramNodeKind;
          }
        }
        if (isLast) {
          seenPaths.add(currentPath);
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
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  
  const treeNodes = useMemo(() => buildTreeFromFlatNodes(nodes), [nodes]);

  const handleToggleExpanded = (nodeId: string, isExpanded: boolean) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (isExpanded) {
        next.add(nodeId);
      } else {
        next.delete(nodeId);
      }
      return next;
    });
  };

  const handleExpandAll = () => {
    const allNodeIds = new Set<string>();
    const collectNodeIds = (node: TreeNode) => {
      if (node.isFolder) {
        allNodeIds.add(node.id);
      }
      node.children.forEach(collectNodeIds);
    };
    treeNodes.forEach(collectNodeIds);
    setExpandedNodes(allNodeIds);
  };

  const handleCollapseAll = () => {
    setExpandedNodes(new Set());
  };

  return (
    <section aria-label="Graph Explorer">
      <div className="panel-heading">
        <h2>Graph Explorer</h2>
        {nodes.length > 0 && (
          <div className="studio-actions">
            <button onClick={handleExpandAll}>Expand All</button>
            <button onClick={handleCollapseAll}>Collapse All</button>
          </div>
        )}
      </div>
      {nodes.length === 0 ? (
        <p className="muted">No graph nodes available.</p>
      ) : (
        <div className="graph-explorer file-tree" role="tree">
          {treeNodes.map((treeNode) => (
            <FileTreeNode
              key={treeNode.id}
              node={treeNode}
              level={0}
              selectedNodeId={selectedNodeId}
              onSelectNodeId={onSelectNodeId}
              isExpanded={expandedNodes.has(treeNode.id)}
              onToggleExpanded={handleToggleExpanded}
              expandedNodes={expandedNodes}
            />
          ))}
        </div>
      )}
    </section>
  );
}
