"use client";

import { Check, Search } from "lucide-react";
import { type KeyboardEvent, type ReactNode, useMemo, useState } from "react";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import { cn } from "@/lib/utils";
import { FIELD_OPTION_SEARCH_THRESHOLD } from "./shared";

export interface FieldEditOptionItem {
  id: string;
  label: string;
  selected?: boolean;
  content: ReactNode;
  onSelect: () => void;
}

export function FieldEditOptionList({
  items,
  searchPlaceholder = "Search options",
  emptyText = "No options",
  autoFocusSearch = true,
  variant = "popover",
  onKeyDown,
}: {
  items: FieldEditOptionItem[];
  searchPlaceholder?: string;
  emptyText?: string;
  autoFocusSearch?: boolean;
  variant?: "popover" | "sheet";
  onKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
}) {
  const [query, setQuery] = useState("");
  const searchable = items.length > FIELD_OPTION_SEARCH_THRESHOLD;
  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return items;
    return items.filter((item) => item.label.toLowerCase().includes(normalizedQuery));
  }, [items, query]);

  return (
    <div
      data-slot="combobox-content"
      className={cn(
        "group/combobox-content relative overflow-hidden",
        variant === "popover" &&
          "max-h-96 min-w-56 rounded-md border border-border bg-popover text-popover-foreground shadow-md *:data-[slot=input-group]:m-1.5 *:data-[slot=input-group]:mb-1 *:data-[slot=input-group]:h-9 *:data-[slot=input-group]:border-input *:data-[slot=input-group]:bg-transparent *:data-[slot=input-group]:shadow-xs *:data-[slot=input-group]:has-[[data-slot=input-group-control]:focus-visible]:border-input *:data-[slot=input-group]:has-[[data-slot=input-group-control]:focus-visible]:ring-0",
        variant === "sheet" &&
          "max-h-none min-w-0 rounded-none bg-transparent text-foreground shadow-none ring-0",
      )}
      onKeyDown={onKeyDown}
    >
      {searchable ? (
        <InputGroup
          className={cn(
            variant === "sheet" &&
              "mb-3 h-10 border-input bg-transparent shadow-none ring-0 dark:bg-transparent has-[[data-slot=input-group-control]:focus-visible]:border-ring/30 has-[[data-slot=input-group-control]:focus-visible]:!ring-0",
          )}
        >
          <InputGroupAddon align="inline-start" className="pointer-events-none pl-2">
            <Search className="icon-14 shrink-0" />
          </InputGroupAddon>
          <InputGroupInput
            autoFocus={autoFocusSearch}
            name="field-option-search"
            value={query}
            placeholder={searchPlaceholder}
            className={cn(variant === "sheet" ? "h-9 text-base" : "h-8 text-sm")}
            onChange={(event) => setQuery(event.target.value)}
          />
        </InputGroup>
      ) : null}
      <div
        data-slot="combobox-list"
        className={cn(
          "scroll-py-1 overflow-y-auto",
          variant === "popover" && "max-h-72 p-1",
          variant === "sheet" && "max-h-[min(420px,calc(var(--visual-viewport-height)-13rem))] px-0 py-1",
        )}
      >
        {filteredItems.length > 0 ? (
          filteredItems.map((item) => (
            <button
              type="button"
              key={item.id}
              data-slot="combobox-item"
              className={cn(
                "relative flex w-full cursor-default items-center gap-2 rounded-md pr-8 text-left outline-hidden select-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:bg-accent focus-visible:text-accent-foreground",
                variant === "popover" && "py-1.5 pl-2 text-sm",
                variant === "sheet" && "min-h-11 py-2.5 pl-1 text-base",
              )}
              onClick={item.onSelect}
            >
              <span className="min-w-0">{item.content}</span>
              {item.selected ? (
                <span className="pointer-events-none absolute right-2 flex size-4 items-center justify-center">
                  <Check className="icon-14 shrink-0 text-muted-foreground" />
                </span>
              ) : null}
            </button>
          ))
        ) : (
          <div data-slot="combobox-empty" className="py-6 text-center text-sm text-muted-foreground">
            {emptyText}
          </div>
        )}
      </div>
    </div>
  );
}
