import { useState, useEffect } from 'react'

/**
 * Like useState but reads/writes to localStorage under the given key.
 * Falls back to initialValue if storage is unavailable or the key is absent.
 */
export function useLocalStorageState(key, initialValue) {
  const [state, setState] = useState(() => {
    try {
      const stored = localStorage.getItem(key)
      return stored !== null ? JSON.parse(stored) : initialValue
    } catch {
      return initialValue
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(state))
    } catch {
      // storage unavailable — continue without persistence
    }
  }, [key, state])

  return [state, setState]
}
