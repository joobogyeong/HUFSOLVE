export function formatTime(milliseconds: number) {
  const seconds = Math.max(0, Math.ceil(milliseconds / 1000));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  const two = (value: number) => value.toString().padStart(2, "0");
  return hours > 0
    ? `${two(hours)}:${two(minutes)}:${two(rest)}`
    : `${two(minutes)}:${two(rest)}`;
}

export function formatDateTime(value: string | number) {
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatDuration(seconds: number) {
  const totalMinutes = Math.floor(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return [hours > 0 ? `${hours}시간` : "", minutes > 0 ? `${minutes}분` : ""]
    .filter(Boolean)
    .join(" ");
}
