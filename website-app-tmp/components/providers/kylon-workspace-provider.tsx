"use client";

import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useMemo, type ReactNode } from "react";
import type { KylonWorkspaceContext } from "@/lib/kylon/bridge";
import {
  normalizeWorkspaceMemberProfiles,
  type WorkspaceMemberProfile,
  type WorkspaceMemberProfileMap,
} from "@/lib/kylon/workspace-member-profiles";
import { queryKeys } from "@/lib/query-keys";

const EMPTY_MEMBER_MAP: WorkspaceMemberProfileMap = new Map();
const KylonWorkspaceContextValue = createContext<KylonWorkspaceContext | null>(null);
const WorkspaceMemberProfilesContext =
  createContext<WorkspaceMemberProfileMap>(EMPTY_MEMBER_MAP);

async function fetchWorkspaceMembers(): Promise<WorkspaceMemberProfile[]> {
  const response = await fetch("/api/kylon/workspace-members", {
    headers: { accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to load workspace members: ${response.status}`);
  }
  return normalizeWorkspaceMemberProfiles(await response.json());
}

export function useWorkspaceMembers() {
  return useQuery({
    queryKey: queryKeys.workspaceMembers(),
    queryFn: fetchWorkspaceMembers,
    staleTime: 10 * 60_000,
    gcTime: 30 * 60_000,
  });
}

export function KylonWorkspaceProvider({
  value,
  children,
}: {
  value: KylonWorkspaceContext | null;
  children: ReactNode;
}) {
  const { data = [] } = useWorkspaceMembers();
  const membersById = useMemo<WorkspaceMemberProfileMap>(() => {
    if (data.length === 0) return EMPTY_MEMBER_MAP;
    return new Map(data.map((member) => [member.userId, member]));
  }, [data]);

  return (
    <KylonWorkspaceContextValue.Provider value={value}>
      <WorkspaceMemberProfilesContext.Provider value={membersById}>
        {children}
      </WorkspaceMemberProfilesContext.Provider>
    </KylonWorkspaceContextValue.Provider>
  );
}

export function useKylonWorkspaceContext() {
  return useContext(KylonWorkspaceContextValue);
}

export function useWorkspaceMemberProfiles() {
  return useContext(WorkspaceMemberProfilesContext);
}
