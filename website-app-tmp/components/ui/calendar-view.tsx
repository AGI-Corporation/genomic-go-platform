"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useMemo, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { buildCalendarDays, dateValueToDateKey, formatDateKey } from "./calendar-utils";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;
const MAX_VISIBLE_EVENTS = 3;

export interface CalendarEvent<TData = unknown> {
  id: string;
  title: string;
  date: string | Date | null | undefined;
  data?: TData;
}

export interface CalendarViewProps<TData = unknown> {
  events: CalendarEvent<TData>[];
  label?: string;
  headerStart?: ReactNode;
  headerEnd?: ReactNode;
  selectedEventId?: string | null;
  onEventClick?: (event: CalendarEvent<TData>) => void;
}

function firstUsableDate(events: CalendarEvent[]): Date {
  for (const event of events) {
    const key = dateValueToDateKey(event.date, { includeTime: false });
    if (key) return new Date(`${key}T00:00:00`);
  }
  return new Date();
}

export function CalendarView<TData = unknown>({
  events,
  label = "Calendar",
  headerStart,
  headerEnd,
  selectedEventId,
  onEventClick,
}: CalendarViewProps<TData>) {
  const [currentDate, setCurrentDate] = useState(() => {
    const initial = firstUsableDate(events);
    return { year: initial.getFullYear(), month: initial.getMonth() };
  });

  const eventsByDate = useMemo(() => {
    const map = new Map<string, CalendarEvent<TData>[]>();
    for (const event of events) {
      const key = dateValueToDateKey(event.date, { includeTime: false });
      if (!key) continue;
      const list = map.get(key);
      if (list) list.push(event);
      else map.set(key, [event]);
    }
    return map;
  }, [events]);

  const calendarDays = useMemo(
    () => buildCalendarDays(currentDate.year, currentDate.month),
    [currentDate],
  );

  const handlePrevMonth = useCallback(() => {
    setCurrentDate((prev) => {
      const month = prev.month - 1;
      return month < 0 ? { year: prev.year - 1, month: 11 } : { year: prev.year, month };
    });
  }, []);

  const handleNextMonth = useCallback(() => {
    setCurrentDate((prev) => {
      const month = prev.month + 1;
      return month > 11 ? { year: prev.year + 1, month: 0 } : { year: prev.year, month };
    });
  }, []);

  const handleToday = useCallback(() => {
    const now = new Date();
    setCurrentDate({ year: now.getFullYear(), month: now.getMonth() });
  }, []);

  const monthLabel = new Date(currentDate.year, currentDate.month).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });
  const todayKey = formatDateKey(new Date());

  return (
    <section aria-label={label} className="flex min-h-0 flex-1 flex-col">
      <CalendarHeader
        label={monthLabel}
        headerStart={headerStart}
        headerEnd={headerEnd}
        onPrev={handlePrevMonth}
        onNext={handleNextMonth}
        onToday={handleToday}
      />
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4 lg:px-6">
        {events.length === 0 ? (
          <CalendarEmptyState message="There are no scheduled events yet." />
        ) : (
          <div className="grid grid-cols-7 overflow-hidden rounded-lg border border-border bg-background">
            {WEEKDAYS.map((day) => (
              <div
                key={day}
                className="border-r border-border/70 bg-muted px-2 py-1.5 text-center text-xs font-medium text-muted-foreground last:border-r-0"
              >
                {day}
              </div>
            ))}
            {calendarDays.map((day) => (
              <CalendarDayCell
                key={day.key}
                date={day.date}
                dateKey={day.key}
                isCurrentMonth={day.isCurrentMonth}
                isToday={day.key === todayKey}
                events={eventsByDate.get(day.key) ?? []}
                selectedEventId={selectedEventId}
                onEventClick={onEventClick}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function CalendarHeader({
  label,
  headerStart,
  headerEnd,
  onPrev,
  onNext,
  onToday,
}: {
  label: string;
  headerStart?: ReactNode;
  headerEnd?: ReactNode;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
}) {
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 px-4 py-4 lg:px-6">
      {headerStart ? <div className="flex shrink-0 items-center">{headerStart}</div> : null}
      <div className="flex shrink-0 items-center gap-0.5">
        <Button size="icon-sm" variant="ghost" onClick={onPrev} aria-label="Previous month">
          <ChevronLeft className="icon-16" />
        </Button>
        <Button size="sm" variant="ghost" onClick={onToday} className="px-2 text-xs">
          Today
        </Button>
        <Button size="icon-sm" variant="ghost" onClick={onNext} aria-label="Next month">
          <ChevronRight className="icon-16" />
        </Button>
      </div>
      <h2 className="min-w-40 text-label-lg">{label}</h2>
      {headerEnd ? <div className="ml-auto flex shrink-0 items-center">{headerEnd}</div> : null}
    </div>
  );
}

function CalendarDayCell<TData>({
  date,
  dateKey,
  isCurrentMonth,
  isToday,
  events,
  selectedEventId,
  onEventClick,
}: {
  date: number;
  dateKey: string;
  isCurrentMonth: boolean;
  isToday: boolean;
  events: CalendarEvent<TData>[];
  selectedEventId?: string | null;
  onEventClick?: (event: CalendarEvent<TData>) => void;
}) {
  const visible = events.slice(0, MAX_VISIBLE_EVENTS);
  const overflow = events.length - MAX_VISIBLE_EVENTS;

  return (
    <div
      data-date={dateKey}
      className={cn(
        "flex min-h-[6.25rem] flex-col gap-0.5 border-t border-r border-border/70 bg-background p-1.5 [&:nth-child(7n+7)]:border-r-0",
        !isCurrentMonth && "bg-muted/50",
      )}
    >
      <span
        className={cn(
          "mb-0.5 inline-flex size-6 items-center justify-center rounded-full text-xs",
          isToday && "bg-primary font-medium text-primary-foreground",
          !isCurrentMonth && !isToday && "text-muted-foreground/50",
        )}
      >
        {date}
      </span>
      {visible.map((event) => (
        <button
          key={event.id}
          type="button"
          onClick={() => onEventClick?.(event)}
          className={cn(
            "w-full truncate rounded px-1.5 py-0.5 text-left text-[11px] leading-tight transition-colors",
            "bg-primary/10 text-foreground hover:bg-primary/20",
            event.id === selectedEventId && "bg-primary/20 ring-1 ring-primary",
          )}
          title={event.title}
        >
          {event.title}
        </button>
      ))}
      {overflow > 0 ? (
        <span className="px-1.5 text-[10px] text-muted-foreground">+{overflow} more</span>
      ) : null}
    </div>
  );
}

function CalendarEmptyState({ message }: { message: string }) {
  return (
    <div className="flex min-h-[320px] items-center justify-center rounded-lg border border-border bg-background px-6">
      <p className="max-w-sm text-center text-body-sm text-muted-foreground">{message}</p>
    </div>
  );
}
