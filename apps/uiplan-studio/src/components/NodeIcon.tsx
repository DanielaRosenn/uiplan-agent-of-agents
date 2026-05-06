import React from "react";
import {
  FileCode,
  Folder,
  Workflow,
  Bot,
  Zap,
  FileText,
  Book,
  AlertCircle,
} from "lucide-react";

import type { DiagramNodeKind } from "../types";

interface NodeIconProps {
  kind: DiagramNodeKind | "file" | "folder";
  size?: number;
}

export default function NodeIcon({ kind, size = 16 }: NodeIconProps) {
  const iconProps = { size, strokeWidth: 2 };

  switch (kind) {
    case "file":
      return <FileCode {...iconProps} />;
    case "folder":
      return <Folder {...iconProps} />;
    case "document":
      return <FileText {...iconProps} />;
    case "workflow":
      return <Workflow {...iconProps} />;
    case "skill":
      return <Zap {...iconProps} />;
    case "library":
      return <Book {...iconProps} />;
    case "review":
      return <AlertCircle {...iconProps} />;
    default:
      return <FileCode {...iconProps} />;
  }
}
