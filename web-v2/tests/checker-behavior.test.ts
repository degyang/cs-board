/**
 * Contract checker behavior tests (§3E)
 *
 * Tests the production verification logic by directly importing
 * contract-checker-core.mjs — no source string assertions, no copied algorithms.
 */

import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  extractInterfaceFields,
  tsTypeToJsonTypes,
  validateJsonType,
  verifyFieldsBidirectional,
  verifyResponse,
  verifyNested,
  checkFixtures,
} from '../scripts/contract-checker-core.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')
const TYPES_FILE = path.join(ROOT, 'src/lib/api/types.ts')
const FIXTURES_DIR = path.join(ROOT, 'tests/fixtures/contracts')

const tsContent = fs.readFileSync(TYPES_FILE, 'utf-8')

// ── extractInterfaceFields ────────────────────────────────────────────────

describe('extractInterfaceFields', () => {
  it('extracts required and optional fields for ServiceDefinition', () => {
    const fields = extractInterfaceFields(tsContent, 'ServiceDefinition')
    expect(fields).not.toBeNull()
    expect(fields!.required.has('service_id')).toBe(true)
    expect(fields!.required.has('display_name')).toBe(true)
    expect(fields!.required.has('enabled')).toBe(true)
    expect(fields!.required.has('config_status')).toBe(true)
    expect(fields!.optional.size).toBe(0)
  })

  it('extracts optional fields for ApiError', () => {
    const fields = extractInterfaceFields(tsContent, 'ApiError')
    expect(fields).not.toBeNull()
    expect(fields!.required.has('code')).toBe(true)
    expect(fields!.required.has('message')).toBe(true)
    expect(fields!.optional.has('retryable')).toBe(true)
    expect(fields!.optional.has('details')).toBe(true)
  })

  it('extracts optional fields for VoiceDefinition', () => {
    const fields = extractInterfaceFields(tsContent, 'VoiceDefinition')
    expect(fields).not.toBeNull()
    expect(fields!.required.has('voice_id')).toBe(true)
    expect(fields!.optional.has('description')).toBe(true)
    expect(fields!.optional.has('content_url')).toBe(true)
  })

  it('returns null for nonexistent interface', () => {
    expect(extractInterfaceFields(tsContent, 'NonexistentInterface')).toBeNull()
  })

  it('extracts ServiceAvailability fields', () => {
    const fields = extractInterfaceFields(tsContent, 'ServiceAvailability')
    expect(fields).not.toBeNull()
    expect(fields!.required.has('available')).toBe(true)
    expect(fields!.required.has('latency_ms')).toBe(true)
    expect(fields!.required.has('component')).toBe(true)
  })
})

// ── verifyFieldsBidirectional ─────────────────────────────────────────────

describe('verifyFieldsBidirectional', () => {
  it('detects undeclared backend fields', () => {
    const fields = extractInterfaceFields(tsContent, 'ServiceAvailability')!
    const result = verifyFieldsBidirectional(
      ['available', 'checked_at', 'latency_ms', 'component', 'error_code', 'suggestion', 'extra_field'],
      fields
    )
    expect(result.backendExtra).toEqual(['extra_field'])
    expect(result.missingRequired).toEqual([])
  })

  it('detects missing required fields', () => {
    const fields = extractInterfaceFields(tsContent, 'ServiceAvailability')!
    const result = verifyFieldsBidirectional(['available', 'checked_at'], fields)
    expect(result.backendExtra).toEqual([])
    expect(result.missingRequired).toContain('latency_ms')
    expect(result.missingRequired).toContain('component')
  })

  it('allows missing optional fields', () => {
    const fields = extractInterfaceFields(tsContent, 'ApiError')!
    const result = verifyFieldsBidirectional(['code', 'message'], fields)
    expect(result.backendExtra).toEqual([])
    expect(result.missingRequired).toEqual([])
    expect(result.missingOptional).toContain('retryable')
    expect(result.missingOptional).toContain('details')
  })

  it('passes when all fields match', () => {
    const fields = extractInterfaceFields(tsContent, 'ServiceAvailability')!
    const result = verifyFieldsBidirectional(
      ['available', 'checked_at', 'latency_ms', 'component', 'error_code', 'suggestion'],
      fields
    )
    expect(result.backendExtra).toEqual([])
    expect(result.missingRequired).toEqual([])
  })
})

// ── validateJsonType ──────────────────────────────────────────────────────

describe('validateJsonType', () => {
  it('validates string type', () => {
    expect(validateJsonType('hello', 'string', 'test')).toBeNull()
    expect(validateJsonType(123, 'string', 'test')).toContain('expected string')
  })

  it('validates number type', () => {
    expect(validateJsonType(42, 'number', 'test')).toBeNull()
    expect(validateJsonType('42', 'number', 'test')).toContain('expected number')
  })

  it('validates boolean type', () => {
    expect(validateJsonType(true, 'boolean', 'test')).toBeNull()
    expect(validateJsonType('true', 'boolean', 'test')).toContain('expected boolean')
  })

  it('validates string | null', () => {
    expect(validateJsonType('hello', 'string | null', 'test')).toBeNull()
    expect(validateJsonType(null, 'string | null', 'test')).toBeNull()
    expect(validateJsonType(123, 'string | null', 'test')).toContain('expected string | null')
  })

  it('validates number | null', () => {
    expect(validateJsonType(42, 'number | null', 'test')).toBeNull()
    expect(validateJsonType(null, 'number | null', 'test')).toBeNull()
    expect(validateJsonType('42', 'number | null', 'test')).toContain('expected number | null')
  })

  it('validates array element types', () => {
    expect(validateJsonType(['a', 'b'], 'string[]', 'test')).toBeNull()
    expect(validateJsonType(['a', 123], 'string[]', 'test')).toContain('expected string')
  })

  it('rejects null for non-nullable types', () => {
    expect(validateJsonType(null, 'string', 'test')).toContain('expected string, got null')
    expect(validateJsonType(null, 'number', 'test')).toContain('expected number, got null')
  })

  it('accepts any type for unknown', () => {
    expect(validateJsonType('hello', 'unknown', 'test')).toBeNull()
    expect(validateJsonType(123, 'unknown', 'test')).toBeNull()
  })

  it('validates Record<string, unknown>', () => {
    expect(validateJsonType({}, 'Record<string, unknown>', 'test')).toBeNull()
    expect(validateJsonType('not-object', 'Record<string, unknown>', 'test')).toContain('expected Record')
  })

  it('distinguishes array from plain object', () => {
    // Array is valid for array types
    expect(validateJsonType([], 'string[]', 'test')).toBeNull()
    // Object is NOT valid for array of primitives
    expect(validateJsonType({}, 'string[]', 'test')).toContain('expected string[]')
    // Array is NOT valid for Record
    expect(validateJsonType([], 'Record<string, unknown>', 'test')).not.toBeNull()
  })
})

// ── verifyResponse ────────────────────────────────────────────────────────

describe('verifyResponse', () => {
  it('passes for valid ServiceAvailability response', () => {
    const data = { available: true, checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null }
    const violations: string[] = []
    verifyResponse(tsContent, data, 'ServiceAvailability', 'test', violations)
    expect(violations).toEqual([])
  })

  it('fails for unknown fields', () => {
    const data = { available: true, checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null, extra: 'bad' }
    const violations: string[] = []
    verifyResponse(tsContent, data, 'ServiceAvailability', 'test', violations)
    expect(violations.some(v => v.includes('extra'))).toBe(true)
  })

  it('fails for missing required fields', () => {
    const data = { available: true }
    const violations: string[] = []
    verifyResponse(tsContent, data, 'ServiceAvailability', 'test', violations)
    expect(violations.some(v => v.includes('required'))).toBe(true)
  })

  it('allows missing optional fields in ApiError', () => {
    const data = { code: 'TEST', message: 'test msg' }
    const violations: string[] = []
    verifyResponse(tsContent, data, 'ApiError', 'test', violations)
    expect(violations).toEqual([])
  })

  it('fails for wrong type in field', () => {
    const data = { available: 'not-boolean', checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null }
    const violations: string[] = []
    verifyResponse(tsContent, data, 'ServiceAvailability', 'test', violations)
    expect(violations.some(v => v.includes('expected boolean'))).toBe(true)
  })

  it('fails for nested type error', () => {
    const data = {
      schema_version: 1, revision: 1, service_id: 'test', display_name: 'Test',
      capability: 'text_generation', adapter_type: 'openai_compatible',
      endpoint: null, model: null, enabled: true, priority: 0, is_default: false,
      config: {}, required_secrets: [], optional_secrets: [],
      config_status: { configured: 'not-boolean', missing_fields: [], missing_secrets: [] },
      availability: { available: true, checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null },
      secret_status: { configured: true, required: [], missing: [] },
      created_at: '', updated_at: '',
    }
    const violations: string[] = []
    verifyResponse(tsContent, data, 'ServiceDefinition', 'test', violations)
    expect(violations.some(v => v.includes('config_status.configured'))).toBe(true)
  })

  it('fails for array element type error', () => {
    const data = {
      items: [
        { secret_key: 'key', configured: true, masked_value: null, updated_at: null },
        { secret_key: 123, configured: true, masked_value: null, updated_at: null }, // wrong type
      ],
      total: 2,
    }
    const violations: string[] = []
    verifyResponse(tsContent, data, 'ServiceSecretListResponse', 'test', violations)
    expect(violations.some(v => v.includes('items[1]'))).toBe(true)
  })

  it('validates ErrorResponse with nested ApiError', () => {
    const data = { error: { code: 'NOT_FOUND', message: 'not found' } }
    const violations: string[] = []
    verifyResponse(tsContent, data, 'ErrorResponse', 'test', violations)
    expect(violations).toEqual([])
  })

  it('fails when ErrorResponse.error missing required code', () => {
    const data = { error: { message: 'not found' } }
    const violations: string[] = []
    verifyResponse(tsContent, data, 'ErrorResponse', 'test', violations)
    expect(violations.some(v => v.includes('error.code') && v.includes('required'))).toBe(true)
  })
})

// ── Fixture alignment ─────────────────────────────────────────────────────

describe('fixture alignment (via checkFixtures)', () => {
  it('all fixtures pass through checkFixtures with zero violations', () => {
    const violations = checkFixtures(tsContent, FIXTURES_DIR, { fs, path })
    expect(violations).toEqual([])
  })
})
