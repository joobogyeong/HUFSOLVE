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
