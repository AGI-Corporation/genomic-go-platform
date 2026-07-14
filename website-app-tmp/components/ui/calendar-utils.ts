export interface CalendarDay {
  key: string;
  date: number;
  isCurrentMonth: boolean;
}

export function buildCalendarDays(year: number, month: number): CalendarDay[] {
  const lastDay = new Date(year, month + 1, 0);

  let startDow = new Date(year, month, 1).getDay() - 1;
  if (startDow < 0) startDow = 6;

  const days: CalendarDay[] = [];

  for (let i = startDow - 1; i >= 0; i--) {
    const date = new Date(year, month, -i);
    days.push({ key: formatDateKey(date), date: date.getDate(), isCurrentMonth: false });
  }

  for (let day = 1; day <= lastDay.getDate(); day += 1) {
    const date = new Date(year, month, day);
    days.push({ key: formatDateKey(date), date: day, isCurrentMonth: true });
  }

  const target = days.length <= 35 ? 35 : 42;
  let nextDay = 1;
  while (days.length < target) {
    const date = new Date(year, month + 1, nextDay);
    days.push({ key: formatDateKey(date), date: nextDay, isCurrentMonth: false });
    nextDay += 1;
  }

  return days;
}

export function formatDateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function dateValueToDateKey(value: unknown, opts: { includeTime?: boolean } = {}): string | null {
  if (value == null || value === "") return null;
  const raw = String(value).trim();
  const dateOnly = raw.match(/^(\d{4}-\d{2}-\d{2})$/);
  if (dateOnly) return dateOnly[1] ?? null;

  const utcMidnightDateOnly = raw.match(/^(\d{4}-\d{2}-\d{2})T00:00:00(?:\.000)?Z$/);
  if (opts.includeTime === false && utcMidnightDateOnly) return utcMidnightDateOnly[1] ?? null;

  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return null;
  return formatDateKey(parsed);
}
