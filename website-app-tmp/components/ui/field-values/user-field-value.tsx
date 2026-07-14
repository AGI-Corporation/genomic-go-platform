"use client";

import { Fragment } from "react";
import { useWorkspaceMemberProfiles } from "@/components/providers/kylon-workspace-provider";
import { type OverflowItem, OverflowList } from "@/components/ui/overflow-list";
import { resolveUserOption } from "@/lib/kylon/workspace-member-profiles";
import { cn } from "@/lib/utils";
import type { DataUserOption, DataValue } from "@/components/ui/data-types";
import { FieldEditOptionList } from "./edit-option-list";
import {
  CHIP_AVATAR_WIDTH,
  CHIP_FONT,
  CHIP_GAP,
  fieldAvailableWidth,
  measureTextWidth,
  toArray,
  UserChip,
  visibleItemCount,
  type FieldValueEditProps,
  type FieldValueViewProps,
} from "./shared";

function userOptions({ field }: Pick<FieldValueViewProps, "field">, workspaceMemberProfiles: ReturnType<typeof useWorkspaceMemberProfiles>): DataUserOption[] {
  if (field.config?.users?.length) return field.config.users;
  return [...workspaceMemberProfiles.values()].map((member) => ({
    id: member.userId,
    name: member.name,
    email: member.email,
    avatar_url: member.avatarUrl,
  }));
}

export function UserFieldView({ value, field }: FieldValueViewProps) {
  const workspaceMemberProfiles = useWorkspaceMemberProfiles();
  return <UserChip user={resolveUserOption(field, value, workspaceMemberProfiles)} />;
}

export function MultiUserFieldView({
  value,
  field,
  cellWidth,
  availableWidth,
  displayCount,
  wrapText = true,
  overflowBadgeTrigger = "button",
  className,
}: FieldValueViewProps) {
  const workspaceMemberProfiles = useWorkspaceMemberProfiles();
  const values = toArray(value);
  const users = values.map((item) => resolveUserOption(field, item, workspaceMemberProfiles));
  const resolvedAvailableWidth = fieldAvailableWidth(cellWidth, availableWidth);
  const items: OverflowItem[] = users.map((user, index) => ({
    key: `${user.id}-${index}`,
    element: <UserChip user={user} />,
  }));
  const visibleCount = visibleItemCount({
    itemWidths: users.map((user) => CHIP_AVATAR_WIDTH + measureTextWidth(user.name, CHIP_FONT)),
    availableWidth: resolvedAvailableWidth,
    gap: CHIP_GAP,
    displayCount: displayCount ?? (resolvedAvailableWidth == null ? field.config?.max_visible : undefined),
  });
  if (visibleCount >= items.length) {
    return (
      <span className={cn("flex min-w-0 items-center gap-x-2.5 overflow-hidden", wrapText ? "flex-wrap" : "flex-nowrap", className)}>
        {items.map((item) => (
          <Fragment key={item.key}>{item.element}</Fragment>
        ))}
      </span>
    );
  }
  return (
    <OverflowList
      items={items}
      visibleCount={visibleCount}
      gap={10}
      className={className}
      overflowBadgeTrigger={overflowBadgeTrigger}
      overflowBadgeClassName={overflowBadgeTrigger === "span" ? "cursor-pointer" : undefined}
      renderPopoverContent={(hidden) => (
        <div className="flex flex-col gap-2">
          {hidden.map((item) => (
            <span key={item.key} className="inline-flex items-center leading-none">
              {item.element}
            </span>
          ))}
        </div>
      )}
    />
  );
}

export function UserFieldEdit({ value, field, onChange, onCommit, autoFocus, presentation }: FieldValueEditProps) {
  const workspaceMemberProfiles = useWorkspaceMemberProfiles();
  const current = String(value ?? "");
  return (
    <FieldEditOptionList
      searchPlaceholder="Search people"
      autoFocusSearch={autoFocus}
      variant={presentation}
      items={userOptions({ field }, workspaceMemberProfiles).map((user) => {
        const selected = user.id === current || user.email === current || user.name === current;
        return {
          id: user.id,
          label: [user.name, user.email].filter(Boolean).join(" "),
          selected,
          content: <UserChip user={user} />,
          onSelect: () => {
            onChange(user.id);
            onCommit(user.id);
          },
        };
      })}
    />
  );
}

export function MultiUserFieldEdit({ value, field, onChange, onCommit, autoFocus, presentation }: FieldValueEditProps) {
  const workspaceMemberProfiles = useWorkspaceMemberProfiles();
  const selected = new Set(toArray(value).map((item) => String(item)));
  const options = userOptions({ field }, workspaceMemberProfiles);
  return (
    <FieldEditOptionList
      searchPlaceholder="Search people"
      autoFocusSearch={autoFocus}
      variant={presentation}
      onKeyDown={(event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          onCommit([...selected]);
        }
      }}
      items={options.map((user) => {
        const isSelected = selected.has(user.id) || (user.email ? selected.has(user.email) : false);
        return {
          id: user.id,
          label: [user.name, user.email].filter(Boolean).join(" "),
          selected: isSelected,
          content: <UserChip user={user} />,
          onSelect: () => {
            const next = new Set(selected);
            if (next.has(user.id)) next.delete(user.id);
            else next.add(user.id);
            onChange([...next] as DataValue);
          },
        };
      })}
    />
  );
}
