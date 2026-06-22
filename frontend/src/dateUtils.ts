export function todayIso() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function addDays(dateText: string, days: number) {
  const next = new Date(`${dateText}T12:00:00`);
  next.setDate(next.getDate() + days);
  const year = next.getFullYear();
  const month = String(next.getMonth() + 1).padStart(2, "0");
  const correctedDay = String(next.getDate()).padStart(2, "0");
  return `${year}-${month}-${correctedDay}`;
}

export function formatBriefingDate(dateText: string) {
  return new Date(`${dateText}T12:00:00`).toLocaleDateString([], {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric"
  });
}
