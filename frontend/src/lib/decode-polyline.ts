/**
 * Decodes Google's encoded polyline format (the same algorithm Google Maps
 * and Google Routes both use) into [lat, lon] pairs.
 * https://developers.google.com/maps/documentation/utilities/polylinealgorithm
 */
export function decodePolyline(encoded: string): [number, number][] {
  const points: [number, number][] = []
  let index = 0
  let lat = 0
  let lon = 0

  while (index < encoded.length) {
    lat += decodeNextValue()
    lon += decodeNextValue()
    points.push([lat / 1e5, lon / 1e5])
  }

  return points

  function decodeNextValue(): number {
    let result = 0
    let shift = 0
    let byte: number

    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)

    return result & 1 ? ~(result >> 1) : result >> 1
  }
}
