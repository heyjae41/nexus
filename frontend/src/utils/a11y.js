/**
 * Returns props for making a non-interactive element keyboard-accessible.
 * @param {Function} onActivate - Called on click-equivalent keyboard event
 * @param {'button'|'link'} role - ARIA role
 */
export function clickableProps(onActivate, role = 'button') {
  return {
    role,
    tabIndex: 0,
    onKeyDown: (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        onActivate(e)
      }
    },
  }
}
