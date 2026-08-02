export interface Point {
  x: number
  y: number
}

const ISO = { originX: 575, originY: 160, tileX: 40, tileY: 21 }

export function isoPoint(x: number, y: number, z = 0): Point {
  return {
    x: ISO.originX + (x - y) * ISO.tileX,
    y: ISO.originY + (x + y) * ISO.tileY - z,
  }
}

export function pointsString(points: Point[]): string {
  return points.map((p) => `${p.x},${p.y}`).join(' ')
}

export function floorPolygon(x: number, y: number, w: number, d: number): Point[] {
  return [isoPoint(x, y), isoPoint(x + w, y), isoPoint(x + w, y + d), isoPoint(x, y + d)]
}

export interface BoxPolygons {
  top: Point[]
  left: Point[]
  right: Point[]
  back: Point[]
}

export function boxPolygons(x: number, y: number, w: number, d: number, height: number): BoxPolygons {
  const a = isoPoint(x, y)
  const b = isoPoint(x + w, y)
  const c = isoPoint(x + w, y + d)
  const dPoint = isoPoint(x, y + d)

  const at = isoPoint(x, y, height)
  const bt = isoPoint(x + w, y, height)
  const ct = isoPoint(x + w, y + d, height)
  const dt = isoPoint(x, y + d, height)

  return {
    top: [at, bt, ct, dt],
    left: [dPoint, c, ct, dt],
    right: [b, c, ct, bt],
    back: [a, b, bt, at],
  }
}

export function zoneCenter(zone: { x: number; y: number; w: number; d: number }, z = 0): Point {
  return isoPoint(zone.x + zone.w / 2, zone.y + zone.d / 2, z)
}
