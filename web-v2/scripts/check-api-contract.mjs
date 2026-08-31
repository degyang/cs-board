/**
 * check-api-contract — Assert JSON contract fixtures match TypeScript DTOs
 *
 * §3.9: 合同测试工具
 *   "Contract fixtures shared between component tests and HTTP tests.
 *    JSON files in `web-v2/tests/fixtures/contracts/`"
 *
 * Reads each JSON fixture, extracts its top-level keys, and verifies
 * the corresponding TypeScript interface includes all of them.
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

const CONTRACT_MAP = [
  { fixture: 'service-definition.json', interface: 'ServiceDefinition' },
  { fixture: 'service-list.json', interface: 'ServiceListResponse' },
  { fixture: 'style-template.json', interface: 'StyleTemplate' },
  { fixture: 'voice-definition.json', interface: 'VoiceDefinition' },
  { fixture: 'settings-voice-alignment.json', interface: 'VoiceAlignmentSettings' },
  { fixture: 'settings-toolchain.json', interface: 'ToolchainSettings' },
  { fixture: 'settings-storage.json', interface: 'StorageSettings' },
  { fixture: 'settings-diagnostics.json', interface: 'DiagnosticsSettings' },
]

function extractInterfaceKeys(tsContent, ifaceName) {
  // Match: export interface Foo { ... } or export type Foo = { ... }
  const patterns = [
    new RegExp(`export\\s+interface\\s+${ifaceName}\\s*\\{([^}]*)\\}`, 's'),
    new RegExp(`export\\s+type\\s+${ifaceName}\\s*=\\s*\\{([^}]*)\\}`, 's'),
  ]

  for (const pat of patterns) {
    const m = tsContent.match(pat)
    if (m) {
      const body = m[1]
      const keys = []
      for (const line of body.split('\n')) {
        const trimmed = line.trim()
        if (!trimmed || trimmed.startsWith('//') || trimmed.startsWith('*')) continue
        // Match: key?: Type  or  key: Type
        const km = trimmed.match(/^(\w+)\??\s*:/)
        if (km) keys.push(km[1])
      }
      return keys
    }
  }
  return null
}

function extractFixtureKeys(obj, prefix = '') {
  const keys = []
  for (const [k, v] of Object.entries(obj)) {
    keys.push(prefix ? `${prefix}.${k}` : k)
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      keys.push(...extractFixtureKeys(v, `${prefix || k}`))
    }
  }
  return keys
}

function extractFixtureTopLevelKeys(obj) {
  return Object.keys(obj)
}

let violations = 0
const tsContent = fs.readFileSync(TYPES_FILE, 'utf-8')

for (const { fixture, interface: ifaceName } of CONTRACT_MAP) {
  const fixturePath = path.join(FIXTURES_DIR, fixture)

  if (!fs.existsSync(fixturePath)) {
    console.log(`⚠ SKIP  ${fixture} — file not found`)
    continue
  }

  const data = JSON.parse(fs.readFileSync(fixturePath, 'utf-8'))
  const fixtureKeys = extractFixtureTopLevelKeys(data)
  const ifaceKeys = extractInterfaceKeys(tsContent, ifaceName)

  if (!ifaceKeys) {
    console.error(`✗ FAIL  ${fixture} → ${ifaceName} — interface not found in types.ts`)
    violations++
    continue
  }

  const missing = fixtureKeys.filter(k => !ifaceKeys.includes(k))
  if (missing.length > 0) {
    console.error(`✗ FAIL  ${fixture} → ${ifaceName}`)
    console.error(`        Missing in DTO: ${missing.join(', ')}`)
    violations++
  } else {
    console.log(`✓ OK    ${fixture} → ${ifaceName}`)
  }
}

if (violations > 0) {
  console.error(`\n${violations} contract violation(s) found`)
  process.exit(1)
} else {
  console.log('\nAll contracts aligned ✓')
  process.exit(0)
}
