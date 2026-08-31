/**
 * contract-checker-core — Production verification logic for API contract checking
 *
 * This module is the single source of truth for:
 *   - Interface field extraction with required/optional distinction
 *   - Bidirectional field verification (undeclared / missing required)
 *   - JSON type validation from TypeScript type strings
 *   - Nested structure recursive verification
 *   - Full endpoint response verification
 *   - Real backend and fixture checking flows
 *
 * CLI (check-api-contract.mjs) and tests both import this module.
 */

// ── Configuration ──────────────────────────────────────────────────────────

export const ENDPOINTS = [
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

export const DYNAMIC_ENDPOINTS = [
  { suffix: '', method: 'GET', type: 'ServiceDefinition', description: 'Service detail' },
  { suffix: '/secrets', method: 'GET', type: 'ServiceSecretListResponse', description: 'Service secrets' },
  { suffix: '/probe', method: 'POST', type: 'ServiceAvailability', description: 'Service probe' },
]

export const ERROR_ENDPOINT = {
  path: '/nonexistent-path-404',
  method: 'GET',
  type: 'ErrorResponse',
  description: 'Unified error response',
}

export const FIXTURE_MAP = [
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

export const NESTED_STRUCTURES = {
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

// ── Core Functions ──────────────────────────────────────────────────────────

/**
 * Extract interface fields with required/optional distinction and TypeScript types.
 * Returns { required: Map<name, tsType>, optional: Map<name, tsType> } or null.
 */
export function extractInterfaceFields(tsContent, ifaceName) {
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

/**
 * Map TypeScript type string to expected JSON typeof value(s).
 * Returns array of valid typeof strings, or null to skip validation.
 */
export function tsTypeToJsonTypes(tsType) {
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
  if (t.includes('|')) return null // union types: skip validation
  return null // complex types: skip
}

/**
 * Validate JSON type against expected TypeScript type.
 * Returns violation message or null if OK.
 * @param {boolean} [allowNull=false] - Allow null for optional fields
 */
export function validateJsonType(value, tsType, path, allowNull = false) {
  if (value === null) {
    if (tsType.includes('| null') || tsType === 'null') return null
    if (allowNull) return null // optional fields accept null
    return path + ': expected ' + tsType + ', got null'
  }

  const expectedTypes = tsTypeToJsonTypes(tsType)
  if (!expectedTypes) return null

  const actualType = typeof value

  // For array types, the value must actually be an array (not a plain object)
  if (tsType.endsWith('[]')) {
    if (!Array.isArray(value)) {
      return path + ': expected ' + tsType + ' (array), got ' + actualType
    }
    // Check element types
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
    return null
  }

  // For Record types, the value must be a plain object (not an array)
  if (tsType.startsWith('Record<')) {
    if (actualType !== 'object' || Array.isArray(value)) {
      return path + ': expected ' + tsType + ' (object), got ' + (Array.isArray(value) ? 'array' : actualType)
    }
    return null
  }

  if (!expectedTypes.includes(actualType)) {
    return path + ': expected ' + tsType + ' (JSON ' + expectedTypes.join('|') + '), got ' + actualType
  }

  return null
}

/**
 * Bidirectional field verification with required/optional distinction.
 * Returns { backendExtra, missingRequired, missingOptional }.
 */
export function verifyFieldsBidirectional(dataKeys, fields) {
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
 * Mutates `violations` array in place.
 */
export function verifyNested(tsContent, data, typeName, basePath, violations) {
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
        const { backendExtra, missingRequired } = verifyFieldsBidirectional(itemKeys, nestedFields)

        if (backendExtra.length > 0) {
          violations.push(...backendExtra.map(k => itemPath + '.' + k))
        }
        if (missingRequired.length > 0) {
          violations.push(...missingRequired.map(k => itemPath + '.' + k + ' (required)'))
        }

        // Type validation for array element fields
        for (const key of itemKeys) {
          const isOptional = nestedFields.optional.has(key)
          const elemTsType = nestedFields.required.get(key) || nestedFields.optional.get(key)
          if (elemTsType) {
            const typeViolation = validateJsonType(value[i][key], elemTsType, itemPath + '.' + key, isOptional)
            if (typeViolation) violations.push(typeViolation)
          }
        }

        verifyNested(tsContent, value[i], nestedCleanType, itemPath, violations)
      }
    } else if (typeof value === 'object' && !Array.isArray(value)) {
      const objPath = basePath + '.' + field
      const itemKeys = Object.keys(value)
      const { backendExtra, missingRequired } = verifyFieldsBidirectional(itemKeys, nestedFields)

      if (backendExtra.length > 0) {
        violations.push(...backendExtra.map(k => objPath + '.' + k))
      }
      if (missingRequired.length > 0) {
        violations.push(...missingRequired.map(k => objPath + '.' + k + ' (required)'))
      }

      // Type validation for nested object fields
      for (const key of itemKeys) {
        const isOptional = nestedFields.optional.has(key)
        const fieldTsType = nestedFields.required.get(key) || nestedFields.optional.get(key)
        if (fieldTsType) {
          const typeViolation = validateJsonType(value[key], fieldTsType, objPath + '.' + key, isOptional)
          if (typeViolation) violations.push(typeViolation)
        }
      }

      verifyNested(tsContent, value, nestedCleanType, objPath, violations)
    }
  }
}

/**
 * Verify one endpoint/response against its DTO type.
 * Checks field names (bidirectional) and JSON types.
 * Mutates `violations` array in place.
 */
export function verifyResponse(tsContent, data, type, description, violations) {
  const fields = extractInterfaceFields(tsContent, type)

  if (!fields) {
    violations.push(description + ': interface ' + type + ' not found')
    return
  }

  const dataKeys = Object.keys(data)
  const { backendExtra, missingRequired } = verifyFieldsBidirectional(dataKeys, fields)

  if (backendExtra.length > 0) {
    violations.push(...backendExtra.map(k => description + '.' + k))
  }
  if (missingRequired.length > 0) {
    violations.push(...missingRequired.map(k => description + '.' + k + ' (required)'))
  }

  // Type validation for all present fields
  for (const key of dataKeys) {
    const isOptional = fields.optional.has(key)
    const tsType = fields.required.get(key) || fields.optional.get(key)
    if (tsType) {
      const typeViolation = validateJsonType(data[key], tsType, description + '.' + key, isOptional)
      if (typeViolation) {
        violations.push(typeViolation)
      }
    }
  }

  verifyNested(tsContent, data, type, description, violations)
}

/**
 * Fetch with explicit HTTP method. Returns { status, body }.
 * Accept optional fetchFn for test injection.
 */
export async function fetchWithMethod(url, method, fetchFn) {
  const fn = fetchFn || fetch
  const res = await fn(url, { method })
  const status = res.status

  if (status === 404) {
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
 * Run real backend contract check.
 * @param {string} tsContent - TypeScript source content
 * @param {string} base - API base URL
 * @param {object} [options]
 * @param {string} [options.serviceId] - Override service ID
 * @param {function} [options.fetchFn] - Custom fetch for testing
 * @returns {Promise<string[]>} violations
 */
export async function checkRealBackend(tsContent, base, options = {}) {
  const fetchFn = options.fetchFn || fetch
  const violations = []

  // Check static endpoints
  for (const ep of ENDPOINTS) {
    const url = base + ep.path
    try {
      const { status, body } = await fetchWithMethod(url, ep.method, fetchFn)

      if (status === 404) {
        violations.push(ep.description + ': 404 Not Found')
        continue
      }

      verifyResponse(tsContent, body, ep.type, ep.description, violations)
    } catch (err) {
      violations.push(ep.description + ': ' + err.message)
    }
  }

  // Resolve dynamic service ID
  let serviceId = options.serviceId || ''

  if (!serviceId) {
    try {
      const servicesUrl = base + '/services?limit=1'
      const { body: servicesData } = await fetchWithMethod(servicesUrl, 'GET', fetchFn)
      const services = servicesData.items || []
      if (services.length > 0) {
        serviceId = services[0].service_id
      }
    } catch {
      // handled below
    }
  }

  if (!serviceId) {
    violations.push('Dynamic endpoints: No service ID available — set MOUNTAIN_CONTRACT_SERVICE_ID or ensure /services returns items')
  } else {
    for (const de of DYNAMIC_ENDPOINTS) {
      const url = base + '/services/' + encodeURIComponent(serviceId) + de.suffix
      try {
        const { status, body } = await fetchWithMethod(url, de.method, fetchFn)

        if (status === 404) {
          violations.push(de.description + ': 404 Not Found')
          continue
        }

        verifyResponse(tsContent, body, de.type, de.description, violations)
      } catch (err) {
        violations.push(de.description + ': ' + err.message)
      }
    }
  }

  // Check unified error response
  try {
    const url = base + ERROR_ENDPOINT.path
    const { status, body } = await fetchWithMethod(url, ERROR_ENDPOINT.method, fetchFn)

    if (body) {
      verifyResponse(tsContent, body, ERROR_ENDPOINT.type, ERROR_ENDPOINT.description, violations)
    } else {
      violations.push(ERROR_ENDPOINT.description + ': no JSON body on 404')
    }
  } catch (err) {
    violations.push(ERROR_ENDPOINT.description + ': ' + err.message)
  }

  return violations
}

/**
 * Run fixture contract check.
 * @param {string} tsContent - TypeScript source content
 * @param {string} fixturesDir - Path to fixtures directory
 * @param {object} deps - { fs, path } Node modules
 * @returns {string[]} violations (synchronous)
 */
export function checkFixtures(tsContent, fixturesDir, deps) {
  const { fs, path } = deps
  const violations = []

  for (const fm of FIXTURE_MAP) {
    const fixturePath = path.join(fixturesDir, fm.fixture)

    if (!fs.existsSync(fixturePath)) continue

    const data = JSON.parse(fs.readFileSync(fixturePath, 'utf-8'))
    const fixtureKeys = Object.keys(data)

    const fields = extractInterfaceFields(tsContent, fm.interface)
    if (!fields) {
      violations.push(fm.fixture + ': interface ' + fm.interface + ' not found')
      continue
    }

    const { backendExtra, missingRequired } = verifyFieldsBidirectional(fixtureKeys, fields)

    if (backendExtra.length > 0) {
      violations.push(...backendExtra.map(k => fm.fixture + '.' + k))
    }
    if (missingRequired.length > 0) {
      violations.push(...missingRequired.map(k => fm.fixture + '.' + k + ' (required)'))
    }

    verifyNested(tsContent, data, fm.interface, fm.fixture, violations)
  }

  return violations
}
