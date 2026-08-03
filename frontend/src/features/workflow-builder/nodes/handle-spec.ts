export interface HandleSpec {
  id: string
  topPct: number
}

export const singleTarget: HandleSpec[] = [{ id: 'in', topPct: 50 }]
export const singleSource: HandleSpec[] = [{ id: 'out', topPct: 50 }]
