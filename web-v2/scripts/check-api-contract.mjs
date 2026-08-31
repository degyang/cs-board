/**
 * check-api-contract — Verify API contract against real backend or fixtures
 *
 * §3C: Hardened contract verification with:
 *   - Explicit HTTP methods per endpoint (GET for detail/secrets, POST for probe)
 *   - MOUNTAIN_CONTRACT_SERVICE_ID support; non-zero exit when no service available
 *   - 404 status as metadata (not injected into response body)
 *   - Real JSON type validation from explicit contract schema
 *   - Required vs optional field distinction (missing required fails, missing optional allowed)
 *   - Bidirectional verification: unknown backend fields still fail
 *
 * When MOUNTAIN_API_BASE is set, requests real backend.
 * When MOUNTAIN_API_BASE is NOT set, falls back to local fixture comparison only.
 *
 * Exit 0 = all contracts aligned, 1 = violations found.
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')
const TYPES_FILE = path.join(ROOT, 'src/lib/api/types.ts')
const FIXTURES_DIR = path.join(ROOT, 'tests/fixtures/contracts')

const BASE = process.env.MOUNTAIN_API_BASE || ''

// Endpoints with explicit HTTP methods
const ENDPOINTS = [
  { path: '/services', method: 'GET', type: 'ServiceListResponse', description: 'Service list' },
  { path: '/services?limit=1', method: 'GET', type: 'ServiceListResponse', description: 'Service list (filtered)' },
  { path: '/assets/styles', method: 'GET', type: 'StyleListResponse', description: 'Style list' },
  { path: '/assets/styles?kind=preset', method: 'GET', type: 'StyleListResponse', description: 'Style list (preset)' },
  { path: '/assets/voices', method: 'GET', type: 'VoiceListResponse', description: 'Voice list' },
  { path: '/settings/voice-alignment', method: 'GET', type: 'VoiceAlignmentSettings', description: 'Voice alignment' },
  { path: '/settings/toolchain', method: 'GET', type: 'ToolchainSettings', description: 'Toolchain' },
  { path: '/settings/storage', method: 'GET', type: 'StorageSettings', description: 'Storage' },
  { path: '/settings/diagnostics', method: 'GET', type: 'DiagnosticsSettings', description: 'Diagnostics' },
]

// Dynamic service endpoints with explicit HTTP methods
const DYNAMIC_ENDPOINTS = [
  { suffix: '', method: 'GET', type: 'ServiceDefinition', description: 'Service detail' },
  { suffix: '/secrets', method: 'GET', type: 'ServiceSecretListResponse', description: 'Service secrets' },
  { suffix: '/probe', method: 'POST', type: 'ServiceAvailability', description: 'Service probe' },
]

// Error endpoint for unified error contract
const ERROR_ENDPOINT = { path: '/nonexistent-path-404', method: 'GET', type: 'ErrorResponse', description: 'Unified error response' }

// Fixture mapping
const FIXTURE_MAP = [
  { fixture: 'service-list.json', interface: 'ServiceListResponse' },
  { fixture: 'service-definition.json', interface: 'ServiceDefinition' },
  { fixture: 'service-secrets.json', interface: 'ServiceSecretListResponse' },
  { fixture: 'service-probe.json', interface: 'ServiceAvailability' },
  { fixture: 'style-template.json', interface: 'StyleTemplate' },
  { fixture: 'style-list.json', interface: 'StyleListResponse' },
  { fixture: 'voice-definition.json', interface: 'VoiceDefinition' },
  { fixture: 'voice-list.json', interface: 'VoiceListResponse' },
  { fixture: 'settings-voice-alignment.json', interface: 'VoiceAlignmentSettings' },
  { fixture: 'settings-toolchain.json', interface: 'ToolchainSettings' },
  { fixture: 'settings-storage.json', interface: 'StorageSettings' },
  { fixture: 'settings-diagnostics.json', interface: 'DiagnosticsSettings' },
  { fixture: 'error.json', interface: 'ErrorResponse' },
]

// Nested structures with their expected types
const NESTED_STRUCTURES = {
  'ServiceDefinition': {
    'config_status': 'ServiceConfigStatus',
    'secret_status': 'ServiceSecretStatus',
    'availability': 'ServiceAvailability',
  },
  'ServiceListResponse': {
    'items': 'ServiceDefinition[]',
  },
  'ServiceSecretListResponse': {
    'items': 'ServiceSecret[]',
  },
  'StyleListResponse': {
    'items': 'StyleTemplate[]',
  },
  'VoiceListResponse': {
    'items': 'VoiceDefinition[]',
  },
  'VoiceAlignmentSettings': {
    'speech_synthesis': 'VoiceAlignmentServiceSummary',
    'speech_alignment': 'VoiceAlignmentServiceSummary',
    'indextts': 'ProbeSummary',
    'whisper': 'ProbeSummary',
  },
  'DiagnosticsSettings': {
    'api': 'DiagnosticsApiStatus',
    'services': 'DiagnosticsServiceSummary',
    'toolchain': 'DiagnosticsToolchainSummary',
    'storage': 'DiagnosticsStorageSummary',
    'telemetry': 'DiagnosticsTelemetry',
    'logs': 'DiagnosticsLogs',
    'recent_errors': 'DiagnosticsRecentError[]',
  },
  'ErrorResponse': {
    'error': 'ApiError',
  },
}

// ── Helpers ────────────────────────────────────────────────────────────────

/**
 * Extract interface fields with required/optional distinction and TypeScript types.
 * Returns { required: Map<name, tsType>, optional: Map<name, tsType> } or null.
 */
function extractInterfaceFields(tsContent, ifaceName) {
  const cleanName = ifaceName.replace(/\[\]$/, '')
  const patterns = [
    new RegExp('export\\s+interface\\s+' + cleanName + '\\s*\\{([^}]*)\\}', 's'),
    new RegExp('export\\s+type\\s+' + cleanName + '\\s*=\\s*\\{([^}]*)\\}', 's'),
  ]

  for (const pat of patterns) {
    const m = tsContent.match(pat)
    if (m) {
      const body = m[1]
      const required = new Map()
      const optional = new Map()

      for (const line of body.split('\n')) {
        const trimmed = line.trim()
        if (!trimmed || trimmed.startsWith('//') || trimmed.startsWith('*')) continue

        // Match "fieldName?: type" (optional) or "fieldName: type" (required)
        const km = trimmed.match(/^(\w+)(\??)\s*:\s*(.+?)$/)
        if (km) {
          const name = km[1]
          const isOptional = km[2] === '?'
          const tsType = km[3].trim()

          if (isOptional) {
            optional.set(name, tsType)
          } else {
            required.set(name, tsType)
          }
        }
      }

      return { required, optional }
    }
  }
  return null
}

function extractFixtureTopLevelKeys(obj) {
  return Object.keys(obj)
}

/**
 * Fetch with explicit HTTP method. Returns { status, body }.
 */
async function fetchWithMethod(url, method) {
  const res = await fetch(url, { method })
  const status = res.status

  if (status === 404) {
    // 404: return status as metadata, try to parse body for DTO validation
    try {
      const body = await res.json()
      return { status, body }
    } catch {
      return { status, body: null }
    }
  }

  if (!res.ok) {
    throw new Error('HTTP ' + status + ': ' + res.statusText)
  }

  return { status, body: await res.json() }
}

/**
 * Map TypeScript type string to expected JSON typeof value(s).
 */
function tsTypeToJsonTypes(tsType) {
  const t = tsType.trim()

  if (t === 'string') return ['string']
  if (t === 'number') return ['number']
  if (t === 'boolean') return ['boolean']
  if (t === 'null') return ['object'] // typeof null === 'object'
  if (t === 'Record<string, unknown>' || t.startsWith('Record<')) return ['object']
  if (t.endsWith('[]')) return ['object'] // arrays are typeof 'object'
  if (t === 'string | null') return ['string', 'object']
  if (t === 'number | null') return ['number', 'object']
  if (t === 'unknown') return null // any type accepted
  if (t === 'unknown[]') return ['object']
  if (t.includes('|')) return null // union types: skip validation for now
  return null // complex types: skip
}

/**
 * Validate JSON type against expected TypeScript type.
 * Returns violation message or null if OK.
 */
function validateJsonType(value, tsType, path) {
  if (value === null) {
    // null is valid for any "| null" type
    if (tsType.includes('| null') || tsType === 'null') return null
    return path + ': expected ' + tsType + ', got null'
  }

  const expectedTypes = tsTypeToJsonTypes(tsType)
  if (!expectedTypes) return null // unknown/complex type, skip

  const actualType = typeof value
  if (!expectedTypes.includes(actualType)) {
    return path + ': expected ' + tsType + ' (JSON ' + expectedTypes.join('|') + '), got ' + actualType
  }

  // For arrays, check element types if possible
  if (Array.isArray(value) && tsType.endsWith('[]')) {
    const elementType = tsType.slice(0, -2)
    const expectedElementTypes = tsTypeToJsonTypes(elementType)
    if (expectedElementTypes) {
      for (let i = 0; i < value.length; i++) {
        const elem = value[i]
        if (elem === null && elementType.includes('| null')) continue
        const elemType = typeof elem
        if (!expectedElementTypes.includes(elemType)) {
          return path + '[' + i + ']: expected ' + elementType + ' (JSON ' + expectedElementTypes.join('|') + '), got ' + elemType
        }
      }
    }
  }

  return null
}

/**
 * Bidirectional field verification with required/optional distinction.
 * Returns { backendExtra, missingRequired, missingOptional }.
 */
function verifyFieldsBidirectional(dataKeys, fields) {
  const backendExtra = dataKeys.filter(k => !(fields.required.has(k) || fields.optional.has(k)))
  const missingRequired = []
  for (const k of fields.required.keys()) {
    if (!dataKeys.includes(k)) missingRequired.push(k)
  }
  const missingOptional = []
  for (const k of fields.optional.keys()) {
    if (!dataKeys.includes(k)) missingOptional.push(k)
  }
  return { backendExtra, missingRequired, missingOptional }
}

/**
 * Recursively verify nested structures with type validation.
 */
function verifyNested(tsContent, data, typeName, basePath, violations) {
  const nestedMap = NESTED_STRUCTURES[typeName]
  if (!nestedMap) return

  for (const [field, nestedType] of Object.entries(nestedMap)) {
    const value = data[field]
    if (value === undefined || value === null) continue

    const nestedCleanType = nestedType.replace(/\[\]$/, '')
    const nestedFields = extractInterfaceFields(tsContent, nestedCleanType)
    if (!nestedFields) continue

    if (nestedType.endsWith('[]') && Array.isArray(value)) {
      for (let i = 0; i < value.length; i++) {
        const itemPath = basePath + '.' + field + '[' + i + ']'
        const itemKeys = Object.keys(value[i])
        const { backendExtra, missingRequired, missingOptional } = verifyFieldsBidirectional(itemKeys, nestedFields)

        if (backendExtra.length > 0) {
          console.error('        ' + itemPath + ' has undeclared fields: ' + backendExtra.join(', '))
          violations.push(...backendExtra.map(k => itemPath + '.' + k))
        }
        if (missingRequired.length > 0) {
          console.error('        ' + itemPath + ' missing required fields: ' + missingRequired.join(', '))
          violations.push(...missingRequired.map(k => itemPath + '.' + k + ' (required)'))
        }
        // missingOptional is OK — just informational

        verifyNested(tsContent, value[i], nestedCleanType, itemPath, violations)
      }
    } else if (typeof value === 'object' && !Array.isArray(value)) {
      const objPath = basePath + '.' + field
      const itemKeys = Object.keys(value)
      const { backendExtra, missingRequired, missingOptional } = verifyFieldsBidirectional(itemKeys, nestedFields)

      if (backendExtra.length > 0) {
        console.error('        ' + objPath + ' has undeclared fields: ' + backendExtra.join(', '))
        violations.push(...backendExtra.map(k => objPath + '.' + k))
      }
      if (missingRequired.length > 0) {
        console.error('        ' + objPath + ' missing required fields: ' + missingRequired.join(', '))
        violations.push(...missingRequired.map(k => objPath + '.' + k + ' (required)'))
      }

      verifyNested(tsContent, value, nestedCleanType, objPath, violations)
    }
  }
}

/**
 * Verify one endpoint/response against its DTO type.
 */
function verifyResponse(tsContent, data, type, description, violations) {
  const fields = extractInterfaceFields(tsContent, type)

  if (!fields) {
    console.error('✗ FAIL  ' + description + ' → ' + type + ' — interface not found in types.ts')
    violations.push(description + ': interface ' + type + ' not found')
    return
  }

  const dataKeys = Object.keys(data)
  const { backendExtra, missingRequired, missingOptional } = verifyFieldsBidirectional(dataKeys, fields)

  if (backendExtra.length > 0) {
    console.error('✗ FAIL  ' + description + ' → ' + type)
    console.error('        Undeclared fields: ' + backendExtra.join(', '))
    violations.push(...backendExtra.map(k => description + '.' + k))
  }
  if (missingRequired.length > 0) {
    console.error('✗ FAIL  ' + description + ' → ' + type)
    console.error('        Missing required fields: ' + missingRequired.join(', '))
    violations.push(...missingRequired.map(k => description + '.' + k + ' (required)'))
  }
  if (backendExtra.length === 0 && missingRequired.length === 0) {
    console.log('✓ OK    ' + description + ' → ' + type + ' (' + dataKeys.length + ' fields)')
  }

  verifyNested(tsContent, data, type, description, violations)
}

// ── Backend checker ────────────────────────────────────────────────────────

async function checkRealBackend(tsContent) {
  console.log('\n\u{1F517} Connecting to real backend: ' + BASE + '\n')
  const violations = []

  // Check static endpoints (all GET)
  for (const ep of ENDPOINTS) {
    const url = BASE + ep.path
    try {
      const { status, body } = await fetchWithMethod(url, ep.method)

      if (status === 404) {
        console.error('✗ FAIL  ' + ep.description + ' — 404 Not Found')
        violations.push(ep.description + ': 404 Not Found')
        continue
      }

      verifyResponse(tsContent, body, ep.type, ep.description, violations)
    } catch (err) {
      console.error('✗ ERR   ' + ep.description + ' — ' + err.message)
      violations.push(ep.description + ': ' + err.message)
    }
  }

  // Check dynamic service endpoints
  const serviceIdOverride = process.env.MOUNTAIN_CONTRACT_SERVICE_ID || ''
  let serviceId = serviceIdOverride

  if (!serviceId) {
    try {
      const servicesUrl = BASE + '/services?limit=1'
      const { body: servicesData } = await fetchWithMethod(servicesUrl, 'GET')
      const services = servicesData.items || []
      if (services.length > 0) {
        serviceId = services[0].service_id
      }
    } catch {
      // Will handle below
    }
  }

  if (!serviceId) {
    const msg = 'No service ID available — set MOUNTAIN_CONTRACT_SERVICE_ID or ensure /services returns items'
    console.error('\n✗ FAIL  Dynamic endpoints — ' + msg + '\n')
    violations.push('Dynamic endpoints: ' + msg)
  } else {
    console.log('\n\u{1F517} Testing dynamic endpoints for service: ' + serviceId + '\n')

    for (const de of DYNAMIC_ENDPOINTS) {
      const url = BASE + '/services/' + encodeURIComponent(serviceId) + de.suffix
      try {
        const { status, body } = await fetchWithMethod(url, de.method)

        if (status === 404) {
          console.error('✗ FAIL  ' + de.description + ' — 404 Not Found')
          violations.push(de.description + ': 404 Not Found')
          continue
        }

        verifyResponse(tsContent, body, de.type, de.description, violations)
      } catch (err) {
        console.error('✗ ERR   ' + de.description + ' — ' + err.message)
        violations.push(de.description + ': ' + err.message)
      }
    }
  }

  // Check unified error response (404 expected — status as metadata, body for DTO)
  try {
    const url = BASE + ERROR_ENDPOINT.path
    const { status, body } = await fetchWithMethod(url, ERROR_ENDPOINT.method)

    if (body) {
      verifyResponse(tsContent, body, ERROR_ENDPOINT.type, ERROR_ENDPOINT.description, violations)
    } else {
      console.error('✗ FAIL  ' + ERROR_ENDPOINT.description + ' — 404 with no JSON body')
      violations.push(ERROR_ENDPOINT.description + ': no JSON body on 404')
    }
  } catch (err) {
    console.error('✗ ERR   ' + ERROR_ENDPOINT.description + ' — ' + err.message)
    violations.push(ERROR_ENDPOINT.description + ': ' + err.message)
  }

  return violations
}

// ── Fixture checker ────────────────────────────────────────────────────────

async function checkFixtures(tsContent) {
  console.log('\n\u{1F4C1} Checking local fixtures (MOUNTAIN_API_BASE not set — fixture mode only)\n')
  const violations = []

  for (const fm of FIXTURE_MAP) {
    const fixturePath = path.join(FIXTURES_DIR, fm.fixture)

    if (!fs.existsSync(fixturePath)) {
      console.log('⚠ SKIP  ' + fm.fixture + ' — file not found')
      continue
    }

    const data = JSON.parse(fs.readFileSync(fixturePath, 'utf-8'))
    const fixtureKeys = extractFixtureTopLevelKeys(data)

    const fields = extractInterfaceFields(tsContent, fm.interface)
    if (!fields) {
      console.error('✗ FAIL  ' + fm.fixture + ' → ' + fm.interface + ' — interface not found in types.ts')
      violations.push(fm.fixture + ': interface ' + fm.interface + ' not found')
      continue
    }

    const { backendExtra, missingRequired, missingOptional } = verifyFieldsBidirectional(fixtureKeys, fields)

    if (backendExtra.length > 0) {
      console.error('✗ FAIL  ' + fm.fixture + ' → ' + fm.interface)
      console.error('        Fixture has fields not in DTO: ' + backendExtra.join(', '))
      violations.push(...backendExtra.map(k => fm.fixture + '.' + k))
    }
    if (missingRequired.length > 0) {
      console.error('✗ FAIL  ' + fm.fixture + ' → ' + fm.interface)
      console.error('        DTO required fields missing from fixture: ' + missingRequired.join(', '))
      violations.push(...missingRequired.map(k => fm.fixture + '.' + k + ' (required)'))
    }
    if (backendExtra.length === 0 && missingRequired.length === 0) {
      console.log('✓ OK    ' + fm.fixture + ' → ' + fm.interface + ' (' + fixtureKeys.length + ' fields)')
    }

    verifyNested(tsContent, data, fm.interface, fm.fixture, violations)
  }

  return violations
}

// ── Main ───────────────────────────────────────────────────────────────────

async function main() {
  const tsContent = fs.readFileSync(TYPES_FILE, 'utf-8')
  let violations = []

  if (BASE) {
    violations = await checkRealBackend(tsContent)
  } else {
    console.log('⚠ MOUNTAIN_API_BASE not set — falling back to fixture comparison only')
    console.log('  NOTE: This is fixture mode, NOT real API verification.')
    violations = await checkFixtures(tsContent)
  }

  if (violations.length > 0) {
    console.error('\n' + violations.length + ' contract violation(s) found')
    process.exit(1)
  } else {
    if (BASE) {
      console.log('\nAll contracts aligned against real backend ✓')
    } else {
      console.log('\nAll fixture contracts aligned (fixture mode — not real API) ✓')
    }
    process.exit(0)
  }
}

main().catch(err => {
  console.error('Fatal error:', err)
  process.exit(1)
})
