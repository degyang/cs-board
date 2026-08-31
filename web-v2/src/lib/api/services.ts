/* ==========================================================================
   Mountain Services API
   Dynamic service management — NOT fixed provider list.
   ========================================================================== */

import { get, patch, post, del } from './http'
import type {
  ServiceDetail,
  ServiceSecret,
  SetServiceSecretRequest,
  ServiceListResponse,
} from './types'

// ---------------------------------------------------------------------------
// Services (dynamic list)
// ---------------------------------------------------------------------------

export function fetchServices(): Promise<ServiceListResponse> {
  return get('/services')
}

export function fetchService(serviceId: string): Promise<ServiceDetail> {
  return get(`/services/${encodeURIComponent(serviceId)}`)
}

export function updateServiceConfig(
  serviceId: string,
  config: Record<string, unknown>,
): Promise<ServiceDetail> {
  return patch(`/services/${encodeURIComponent(serviceId)}/config`, config)
}

export function toggleService(serviceId: string, enabled: boolean): Promise<ServiceDetail> {
  return patch(`/services/${encodeURIComponent(serviceId)}/toggle`, { enabled })
}

export function setDefaultService(serviceId: string): Promise<ServiceDetail> {
  return post(`/services/${encodeURIComponent(serviceId)}/set-default`)
}

// ---------------------------------------------------------------------------
// Service Secrets (write-only)
// ---------------------------------------------------------------------------

export function fetchServiceSecrets(serviceId: string): Promise<ServiceSecret[]> {
  return get(`/services/${encodeURIComponent(serviceId)}/secrets`)
}

export function setServiceSecret(
  serviceId: string,
  req: SetServiceSecretRequest,
): Promise<void> {
  return post(`/services/${encodeURIComponent(serviceId)}/secrets`, req).then(() => undefined)
}

export function deleteServiceSecret(serviceId: string, key: string): Promise<void> {
  return del(`/services/${encodeURIComponent(serviceId)}/secrets/${encodeURIComponent(key)}`).then(
    () => undefined,
  )
}
