/**
 * check-api-contract — CLI wrapper for contract verification
 *
 * Imports all verification logic from contract-checker-core.mjs.
 * This file only handles: environment variables, file I/O, console output, exit codes.
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  checkRealBackend,
  checkFixtures,
} from './contract-checker-core.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')
const TYPES_FILE = path.join(ROOT, 'src/lib/api/types.ts')
const FIXTURES_DIR = path.join(ROOT, 'tests/fixtures/contracts')

const BASE = process.env.MOUNTAIN_API_BASE || ''
const SERVICE_ID = process.env.MOUNTAIN_CONTRACT_SERVICE_ID || ''

async function main() {
  const tsContent = fs.readFileSync(TYPES_FILE, 'utf-8')
  let violations = []

  if (BASE) {
    console.log('\n\u{1F517} Connecting to real backend: ' + BASE + '\n')
    violations = await checkRealBackend(tsContent, BASE, { serviceId: SERVICE_ID })

    if (violations.length === 0) {
      console.log('\nAll contracts aligned against real backend ✓')
    }
  } else {
    console.log('⚠ MOUNTAIN_API_BASE not set — falling back to fixture comparison only')
    console.log('  NOTE: This is fixture mode, NOT real API verification.')
    violations = checkFixtures(tsContent, FIXTURES_DIR, { fs, path })

    if (violations.length === 0) {
      console.log('\nAll fixture contracts aligned (fixture mode — not real API) ✓')
    }
  }

  if (violations.length > 0) {
    for (const v of violations) {
      console.error('✗ ' + v)
    }
    console.error('\n' + violations.length + ' contract violation(s) found')
    process.exit(1)
  }

  process.exit(0)
}

main().catch(err => {
  console.error('Fatal error:', err)
  process.exit(1)
})
