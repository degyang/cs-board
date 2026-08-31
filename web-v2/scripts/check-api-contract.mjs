/**
 * check-api-contract — Verify API contract against real backend or fixtures
 *
 * §3B.2: Bidirectional field verification with recursive nested structure checks.
 *
 * When MOUNTAIN_API_BASE is set, requests real backend and verifies:
 *   - Backend fields are declared in DTO (no undeclared fields)
 *   - DTO required fields exist in backend response (no missing fields)
 *   - Recursive verification for nested structures (config_status, secret_status, availability, items[], error)
 *   - Network failures and field/type mismatches exit non-zero
 *
 * When MOUNTAIN_API_BASE is NOT set, falls back to local fixture comparison only.
 *   - Output explicitly states "fixture mode" — never claims real API verification passed
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

// Expected endpoints and their response types
const ENDPOINTS = [
  { path: '/services', type: 'ServiceListResponse', description: 'Service list', isList: true },
  { path: '/services?limit=1', type: 'ServiceListResponse', description: 'Service list (filtered)', isList: true },
  { path: '/assets/styles', type: 'StyleListResponse', description: 'Style list', isList: true },
  { path: '/assets/styles?kind=preset', type: 'StyleListResponse', description: 'Style list (preset)', isList: true },
  { path: '/assets/voices', type: 'VoiceListResponse', description: 'Voice list', isList: true },
  { path: '/settings/voice-alignment', type: 'VoiceAlignmentSettings', description: 'Voice alignment' },
  { path: '/settings/toolchain', type: 'ToolchainSettings', description: 'Toolchain' },
  { path: '/settings/storage', type: 'StorageSettings', description: 'Storage' },
  { path: '/settings/diagnostics', type: 'DiagnosticsSettings', description: 'Diagnostics' },
]

// Dynamic endpoints that need a service_id — resolved from /services list
const DYNAMIC_ENDPOINTS = [
  { suffix: '', type: 'ServiceDefinition', description: 'Service detail' },
  { suffix: '/secrets', type: 'ServiceSecretListResponse', description: 'Service secrets' },
  { suffix: '/probe', type: 'ServiceAvailability', description: 'Service probe' },
]

// Error endpoint for unified error contract
const ERROR_ENDPOINT = { path: '/nonexistent-path-404', type: 'ErrorResponse', description: 'Unified error response' }

// Fixture fallback mapping
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

// Nested structures that need recursive verification
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

function extractInterfaceKeys(tsContent, ifaceName) {
  const cleanName = ifaceName.replace(/\[\]$/, '')
  const patterns = [
    new RegExp('export\\s+interface\\s+' + cleanName + '\\s*\\{([^}]*)\\}', 's'),
    new RegExp('export\\s+type\\s+' + cleanName + '\\s*=\\s*\\{([^}]*)\\}', 's'),
  ]

  for (const pat of patterns) {
    const m = tsContent.match(pat)
    if (m) {
      const body = m[1]
      const keys = []
      for (const line of body.split('\n')) {
        const trimmed = line.trim()
        if (!trimmed || trimmed.startsWith('//') || trimmed.startsWith('*')) continue
        const km = trimmed.match(/^(\w+)\??\s*:/)
        if (km) keys.push(km[1])
      }
      return keys
    }
  }
  return null
}

function extractFixtureTopLevelKeys(obj) {
  return Object.keys(obj)
}

async function fetchJson(url) {
  const res = await fetch(url)
  if (!res.ok) {
    if (url.includes('nonexistent-path-404')) {
      try {
        return { _status: res.status, ...(await res.json()) }
      } catch {
        throw new Error('HTTP ' + res.status + ': ' + res.statusText)
      }
    }
    throw new Error('HTTP ' + res.status + ': ' + res.statusText)
  }
  return res.json()
}

/**
 * Bidirectional field verification:
 * - backendExtra: fields in backend but not in DTO (undeclared)
 * - dtoMissing: fields in DTO but not in backend (missing from backend)
 */
function verifyFieldsBidirectional(dataKeys, ifaceKeys) {
  const backendExtra = dataKeys.filter(k => !ifaceKeys.includes(k))
  const dtoMissing = ifaceKeys.filter(k => !dataKeys.includes(k))
  return { backendExtra, dtoMissing }
}

/**
 * Recursively verify nested structures.
 */
function verifyNested(tsContent, data, typeName, basePath, violations) {
  const nestedMap = NESTED_STRUCTURES[typeName]
  if (!nestedMap) return

  for (const [field, nestedType] of Object.entries(nestedMap)) {
    const value = data[field]
    if (value === undefined || value === null) continue

    const nestedCleanType = nestedType.replace(/\[\]$/, '')
    const nestedKeys = extractInterfaceKeys(tsContent, nestedCleanType)
    if (!nestedKeys) continue

    if (nestedType.endsWith('[]') && Array.isArray(value)) {
      for (let i = 0; i < value.length; i++) {
        const itemPath = basePath + '.' + field + '[' + i + ']'
        const itemKeys = Object.keys(value[i])
        const { backendExtra, dtoMissing } = verifyFieldsBidirectional(itemKeys, nestedKeys)
        if (backendExtra.length > 0) {
          console.error('        ' + itemPath + ' has undeclared fields: ' + backendExtra.join(', '))
          violations.push(...backendExtra.map(k => itemPath + '.' + k))
        }
        if (dtoMissing.length > 0) {
          console.error('        ' + itemPath + ' missing DTO fields: ' + dtoMissing.join(', '))
          violations.push(...dtoMissing.map(k => itemPath + '.' + k))
        }
        verifyNested(tsContent, value[i], nestedCleanType, itemPath, violations)
      }
    } else if (typeof value === 'object' && !Array.isArray(value)) {
      const objPath = basePath + '.' + field
      const itemKeys = Object.keys(value)
      const { backendExtra, dtoMissing } = verifyFieldsBidirectional(itemKeys, nestedKeys)
      if (backendExtra.length > 0) {
        console.error('        ' + objPath + ' has undeclared fields: ' + backendExtra.join(', '))
        violations.push(...backendExtra.map(k => objPath + '.' + k))
      }
      if (dtoMissing.length > 0) {
        console.error('        ' + objPath + ' missing DTO fields: ' + dtoMissing.join(', '))
        violations.push(...dtoMissing.map(k => objPath + '.' + k))
      }
      verifyNested(tsContent, value, nestedCleanType, objPath, violations)
    }
  }
}

async function checkRealBackend(tsContent) {
  console.log('\n\u{1F517} Connecting to real backend: ' + BASE + '\n')
  const violations = []

  // Check static endpoints
  for (const ep of ENDPOINTS) {
    const url = BASE + ep.path
    try {
      const data = await fetchJson(url)
      const ifaceKeys = extractInterfaceKeys(tsContent, ep.type)

      if (!ifaceKeys) {
        console.error('✗ FAIL  ' + ep.description + ' → ' + ep.type + ' — interface not found in types.ts')
        violations.push(ep.description + ': interface ' + ep.type + ' not found')
        continue
      }

      const dataKeys = Object.keys(data)
      const { backendExtra, dtoMissing } = verifyFieldsBidirectional(dataKeys, ifaceKeys)

      if (backendExtra.length > 0) {
        console.error('✗ FAIL  ' + ep.description + ' → ' + ep.type)
        console.error('        Backend returns undeclared fields: ' + backendExtra.join(', '))
        violations.push(...backendExtra.map(k => ep.description + '.' + k))
      }
      if (dtoMissing.length > 0) {
        console.error('✗ FAIL  ' + ep.description + ' → ' + ep.type)
        console.error('        DTO required fields missing from backend: ' + dtoMissing.join(', '))
        violations.push(...dtoMissing.map(k => ep.description + '.' + k))
      }
      if (backendExtra.length === 0 && dtoMissing.length === 0) {
        console.log('✓ OK    ' + ep.description + ' → ' + ep.type + ' (' + dataKeys.length + ' fields)')
      }

      verifyNested(tsContent, data, ep.type, ep.description, violations)
    } catch (err) {
      console.error('✗ ERR   ' + ep.description + ' — ' + err.message)
      violations.push(ep.description + ': ' + err.message)
    }
  }

  // Check dynamic service endpoints (detail, secrets, probe)
  try {
    const servicesUrl = BASE + '/services?limit=1'
    const servicesData = await fetchJson(servicesUrl)
    const services = servicesData.items || []

    if (services.length > 0) {
      const serviceId = services[0].service_id
      console.log('\n\u{1F517} Testing dynamic endpoints for service: ' + serviceId + '\n')

      for (const de of DYNAMIC_ENDPOINTS) {
        const url = BASE + '/services/' + encodeURIComponent(serviceId) + de.suffix
        try {
          const data = await fetchJson(url)
          const ifaceKeys = extractInterfaceKeys(tsContent, de.type)

          if (!ifaceKeys) {
            console.error('✗ FAIL  ' + de.description + ' → ' + de.type + ' — interface not found')
            violations.push(de.description + ': interface ' + de.type + ' not found')
            continue
          }

          const dataKeys = Object.keys(data)
          const { backendExtra, dtoMissing } = verifyFieldsBidirectional(dataKeys, ifaceKeys)

          if (backendExtra.length > 0) {
            console.error('✗ FAIL  ' + de.description + ' → ' + de.type)
            console.error('        Backend returns undeclared fields: ' + backendExtra.join(', '))
            violations.push(...backendExtra.map(k => de.description + '.' + k))
          }
          if (dtoMissing.length > 0) {
            console.error('✗ FAIL  ' + de.description + ' → ' + de.type)
            console.error('        DTO required fields missing from backend: ' + dtoMissing.join(', '))
            violations.push(...dtoMissing.map(k => de.description + '.' + k))
          }
          if (backendExtra.length === 0 && dtoMissing.length === 0) {
            console.log('✓ OK    ' + de.description + ' → ' + de.type + ' (' + dataKeys.length + ' fields)')
          }

          verifyNested(tsContent, data, de.type, de.description, violations)
        } catch (err) {
          console.error('✗ ERR   ' + de.description + ' — ' + err.message)
          violations.push(de.description + ': ' + err.message)
        }
      }
    } else {
      console.log('\n⚠ SKIP  Dynamic service endpoints — no services found\n')
    }
  } catch (err) {
    console.error('\n✗ ERR   Cannot fetch services list for dynamic endpoints — ' + err.message + '\n')
    violations.push('Services list: ' + err.message)
  }

  // Check unified error response
  try {
    const url = BASE + ERROR_ENDPOINT.path
    const data = await fetchJson(url)
    const ifaceKeys = extractInterfaceKeys(tsContent, ERROR_ENDPOINT.type)

    if (!ifaceKeys) {
      console.error('✗ FAIL  ' + ERROR_ENDPOINT.description + ' → ' + ERROR_ENDPOINT.type + ' — interface not found')
      violations.push(ERROR_ENDPOINT.description + ': interface not found')
    } else {
      const dataKeys = Object.keys(data)
      const { backendExtra, dtoMissing } = verifyFieldsBidirectional(dataKeys, ifaceKeys)

      if (backendExtra.length > 0) {
        console.error('✗ FAIL  ' + ERROR_ENDPOINT.description + ' → undeclared fields: ' + backendExtra.join(', '))
        violations.push(...backendExtra.map(k => ERROR_ENDPOINT.description + '.' + k))
      }
      if (dtoMissing.length > 0) {
        console.error('✗ FAIL  ' + ERROR_ENDPOINT.description + ' → missing DTO fields: ' + dtoMissing.join(', '))
        violations.push(...dtoMissing.map(k => ERROR_ENDPOINT.description + '.' + k))
      }
      if (backendExtra.length === 0 && dtoMissing.length === 0) {
        console.log('✓ OK    ' + ERROR_ENDPOINT.description + ' → ' + ERROR_ENDPOINT.type)
      }

      verifyNested(tsContent, data, ERROR_ENDPOINT.type, ERROR_ENDPOINT.description, violations)
    }
  } catch (err) {
    console.error('✗ ERR   ' + ERROR_ENDPOINT.description + ' — ' + err.message)
    violations.push(ERROR_ENDPOINT.description + ': ' + err.message)
  }

  return violations
}

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
    const ifaceKeys = extractInterfaceKeys(tsContent, fm.interface)

    if (!ifaceKeys) {
      console.error('✗ FAIL  ' + fm.fixture + ' → ' + fm.interface + ' — interface not found in types.ts')
      violations.push(fm.fixture + ': interface ' + fm.interface + ' not found')
      continue
    }

    const { backendExtra, dtoMissing } = verifyFieldsBidirectional(fixtureKeys, ifaceKeys)

    if (backendExtra.length > 0) {
      console.error('✗ FAIL  ' + fm.fixture + ' → ' + fm.interface)
      console.error('        Fixture has fields not in DTO: ' + backendExtra.join(', '))
      violations.push(...backendExtra.map(k => fm.fixture + '.' + k))
    }
    if (dtoMissing.length > 0) {
      console.error('✗ FAIL  ' + fm.fixture + ' → ' + fm.interface)
      console.error('        DTO required fields missing from fixture: ' + dtoMissing.join(', '))
      violations.push(...dtoMissing.map(k => fm.fixture + '.' + k))
    }
    if (backendExtra.length === 0 && dtoMissing.length === 0) {
      console.log('✓ OK    ' + fm.fixture + ' → ' + fm.interface + ' (' + fixtureKeys.length + ' fields)')
    }

    verifyNested(tsContent, data, fm.interface, fm.fixture, violations)
  }

  return violations
}

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
