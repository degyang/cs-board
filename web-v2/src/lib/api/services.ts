/* ==========================================================================
   Mountain Services API
   Dynamic service management — extensible capability/adapter.
   ========================================================================== */

import { get, post, patch, del } from './http'
import type { ServiceDefinition, ServiceListResponse, ServiceSecret } from './types'

// ---------------------------------------------------------------------------
// Services CRUD
// ---------------------------------------------------------------------------

export interface ServiceListParams {
  capability?: string
  enabled?: boolean
  q?: string
  cursor?: string
  limit?: number
}

export function fetchServices(params: ServiceListParams = {}): Promise<ServiceListResponse> {
  const qs = new URLSearchParams()
  if (params.capability) qs.set('capability', params.capability)
  if (params.enabled !== undefined) qs.set('enabled', String(params.enabled))
  if (params.q) qs.set('q', params.q)
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.limit) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return get(`/services${query ? `?${query}` : ''}`)
}

export function fetchService(serviceId: string): Promise<ServiceDefinition> {
  return get(`/services/${encodeURIComponent(serviceId)}`)
}

export function createService(body: {
  display_name: string
  capability: string
  adapter_type: string
  endpoint?: string
  model?: string
  priority?: number
  enabled?: boolean
  config?: Record<string, unknown>
}): Promise<ServiceDefinition> {
  return post('/services', body)
}

export function updateService(
  serviceId: string,
  body: {
    display_name?: string
    capability?: string
    adapter_type?: string
    endpoint?: string
    model?: string
    priority?: number
    enabled?: boolean
    config?: Record<string, unknown>
  },
): Promise<ServiceDefinition> {
  return patch(`/services/${encodeURIComponent(serviceId)}`, body)
}

export function deleteService(serviceId: string): Promise<void> {
  return del(`/services/${encodeURIComponent(serviceId)}`)
}

// ---------------------------------------------------------------------------
// Service Actions
// ---------------------------------------------------------------------------

export function activateService(serviceId: string): Promise<ServiceDefinition> {
  return post(`/services/${encodeURIComponent(serviceId)}/activate`)
}

export function deactivateService(serviceId: string): Promise<ServiceDefinition> {
  return post(`/services/${encodeURIComponent(serviceId)}/deactivate`)
}

export function probeService(serviceId: string): Promise<ServiceDefinition> {
  return post(`/services/${encodeURIComponent(serviceId)}/probe`)
}

export function setDefaultService(serviceId: string): Promise<ServiceDefinition> {
  return post(`/services/${encodeURIComponent(serviceId)}/default`)
}

// ---------------------------------------------------------------------------
// Service Secrets
// ---------------------------------------------------------------------------

export function fetchServiceSecrets(serviceId: string): Promise<ServiceSecret[]> {
  return get(`/services/${encodeURIComponent(serviceId)}/secrets`)
}

export function setServiceSecret(
  serviceId: string,
  body: { key: string; value: string },
): Promise<void> {
  return post(`/services/${encodeURIComponent(serviceId)}/secrets`, body)
}

export function deleteServiceSecret(serviceId: string, secretKey: string): Promise<void> {
  return del(
    `/services/${encodeURIComponent(serviceId)}/secrets/${encodeURIComponent(secretKey)}`,
  )
}
