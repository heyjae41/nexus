import { vi } from 'vitest'

/**
 * Shared test setup helpers for test/frontend/*.test.jsx
 */

/**
 * Creates a promise you can resolve later, used to simulate out-of-order
 * API responses in "stale request should not overwrite newer one" tests.
 */
export function deferred() {
  let resolve
  const promise = new Promise((done) => { resolve = done })
  return { promise, resolve }
}

/**
 * Shared `useNavigate()` mock for views that assert on navigation calls.
 * Import `mockNavigate` **before** importing the view under test so this
 * mock is registered before react-router-dom is loaded for real.
 */
export const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})
