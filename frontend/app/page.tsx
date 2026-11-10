"use client";
import { WorkspaceProvider } from "./workspace/context";
import { Shell } from "./workspace/shell";
export default function Home() {
  return (
    <WorkspaceProvider>
      <Shell />
    </WorkspaceProvider>
  );
}
