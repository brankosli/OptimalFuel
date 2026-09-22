/**
 * Decode a Google Encoded Polyline string into [lat, lng] pairs.
 * Spec: https://developers.google.com/maps/documentation/utilities/polylinealgorithm
 */
export function decodePolyline(encoded: string): [number, number][] {
  const coords: [number, number][] = []
  let index = 0
  let lat = 0
  let lng = 0

  while (index < encoded.length) {
    let shift = 0
    let result = 0
    let byte: number

    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)

    lat += result & 1 ? ~(result >> 1) : result >> 1

    shift = 0
    result = 0

    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)

    lng += result & 1 ? ~(result >> 1) : result >> 1

    coords.push([lat / 1e5, lng / 1e5])
  }

  return coords
}

/**
 * Convert [lat, lng] pairs to a normalized SVG path string
 * that fits within a viewBox of (0, 0, width, height).
 */
export function polylineToSvgPath(
  encoded: string,
  width: number,
  height: number,
  padding = 4,
): string | null {
  if (!encoded) return null
  const coords = decodePolyline(encoded)
  if (coords.length < 2) return null

  const lats = coords.map(c => c[0])
  const lngs = coords.map(c => c[1])

  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minLng = Math.min(...lngs)
  const maxLng = Math.max(...lngs)

  const latRange = maxLat - minLat || 1
  const lngRange = maxLng - minLng || 1

  const w = width - padding * 2
  const h = height - padding * 2

  // Preserve aspect ratio
  const scale = Math.min(w / lngRange, h / latRange)
  const offsetX = padding + (w - lngRange * scale) / 2
  const offsetY = padding + (h - latRange * scale) / 2

  const points = coords.map(([lat, lng]) => {
    const x = offsetX + (lng - minLng) * scale
    const y = offsetY + (maxLat - lat) * scale  // flip Y axis
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  return `M ${points.join(' L ')}`
}
