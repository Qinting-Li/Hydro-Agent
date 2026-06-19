export function polyline(
  values: number[],
  width: number,
  height: number,
  low: number,
  high: number,
  padX = 45,
  padY = 15,
): string {
  const span = Math.max(high - low, 1e-12);
  return values
    .map((value, index) => {
      const x = padX + (index * (width - padX - 20)) / Math.max(values.length - 1, 1);
      const y = padY + ((high - value) * (height - padY - 25)) / span;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function seriesRange(series: number[][]): [number, number] {
  const flat = series.flat();
  if (!flat.length) return [0, 1];
  const low = Math.min(...flat);
  const high = Math.max(...flat);
  const margin = (high - low) * 0.08 || 0.02;
  return [Math.max(0, low - margin), high + margin];
}

export function formatMethod(name: string): string {
  return name
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
