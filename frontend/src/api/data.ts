import http from './http'
import type { DataQuery, DataQueryResponse } from '@/types'

export const dataApi = {
  query: (q: DataQuery) => http.post<DataQueryResponse>('/data/query', q),
}
