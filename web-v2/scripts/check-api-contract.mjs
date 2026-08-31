/**
 * check-api-contract — Verify API contract against real backend or fixtures
 *
 * §3A.4: "MOUNTAIN_API_BASE=http://127.0.0.1:8000/api/v1 node web-v2/scripts/check-api-contract.mjs"
 *
 * When MOUNTAIN_API_BASE is set, requests real backend and verifies fields.
 * When not set, falls back to local fixture comparison.
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
  { path: '/services', type: 'ServiceListResponse', description: 'Service list' },
  { path: '/services?limit=1', type: 'ServiceListResponse', description: 'Service list (filtered)' },
  { path: '/assets/styles', type: 'StyleListResponse', description: 'Style list' },
  { path: '/assets/styles?kind=preset', type: 'StyleListResponse', description: 'Style list (preset)' },
  { path: '/assets/voices', type: 'VoiceListResponse', description: 'Voice list' },
  { path: '/settings/voice-alignment', type: 'VoiceAlignmentSettings', description: 'Voice alignment' },
  { path: '/settings/toolchain', type: 'ToolchainSettings', description: 'Toolchain' },
  { path: '/settings/storage', type: 'StorageSettings', description: 'Storage' },
  { path: '/settings/diagnostics', type: 'DiagnosticsSettings', description: 'Diagnostics' },
]

// Fixture fallback mapping
const FIXTURE_MAP = [
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
    throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  }
  return res.json()
}

async function checkRealBackend(tsContent) {
  console.log(`\n🔗 Connecting to real backend: ${BASE}\n`)
  let violations = 0

  for (const { path, type, description } of ENDPOINTS) {
    const url = `${BASE}${path}`
    try {
      const data = await fetchJson(url)
      const ifaceKeys = extractInterfaceKeys(tsContent, type)

      if (!ifaceKeys) {
        console.error(`✗ FAIL  ${description} → ${type} — interface not found`)
        violations++
        continue
      }

      const dataKeys = Object.keys(data)
      const missing = dataKeys.filter(k => !ifaceKeys.includes(k))

      if (missing.length > 0) {
        console.error(`✗ FAIL  ${description} → ${type}`)
        console.error(`        Backend returns keys not in DTO: ${missing.join(', ')}`)
        violations++
      } else {
        console.log(`✓ OK    ${description} → ${type}`)
      }
    } catch (err) {
      console.error(`✗ ERR   ${description} — ${err.message}`)
      violations++
    }
  }

  return violations
}

async function checkFixtures(tsContent) {
  console.log(`\n📁 Checking local fixtures (MOUNTAIN_API_BASE not set)\n`)
  let violations = 0

  for (const { fixture, interface: ifaceName } of FIXTURE_MAP) {
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

  return violations
}

async function main() {
  const tsContent = fs.readFileSync(TYPES_FILE, 'utf-8')
  let violations = 0

  if (BASE) {
    violations = await checkRealBackend(tsContent)
  } else {
    console.log('⚠ MOUNTAIN_API_BASE not set — falling back to fixture comparison')
    violations = await checkFixtures(tsContent)
  }

  if (violations > 0) {
    console.error(`\n${violations} contract violation(s) found`)
    process.exit(1)
  } else {
    console.log('\nAll contracts aligned ✓')
    process.exit(0)
  }
}

main().catch(err => {
  console.error('Fatal error:', err)
  process.exit(1)
})
