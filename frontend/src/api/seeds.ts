import http from './http'
import type { SeedListResponse } from '@/types'

export const seedsApi = {
  list: () => http.get<SeedListResponse>('/seeds/'),
  importSeeds: (data: Record<string, any>) =>
    http.post('/seeds/import', data),
}
