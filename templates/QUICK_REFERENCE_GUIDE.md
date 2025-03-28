# 🔍 PORTAL ANALYSIS QUICK REFERENCE

## How to Find CSS Selectors

### Method 1: Browser Inspector
1. Right-click element → "Inspect"
2. Look for `id`, `class`, `name` attributes
3. Use format:
   - `id="username"` → `#username`
   - `class="form-input"` → `.form-input`
   - `name="email"` → `[name="email"]`

### Method 2: Browser Console Testing
```javascript
// Test if selector works
document.querySelector('#username')
document.querySelector('.patient-name')
document.querySelectorAll('.patient-row')
```

### Method 3: Copy Selector
1. Right-click element in Inspector
2. Copy → Copy selector
3. Use the generated selector

## Common Selector Patterns

### Forms
- Username: `#username`, `[name="username"]`, `.username-field`
- Password: `#password`, `[name="password"]`, `.password-field`
- Submit: `[type="submit"]`, `.submit-btn`, `#login-btn`

### Navigation
- Menu items: `.nav-item`, `.menu-link`, `[role="menuitem"]`
- Buttons: `.btn`, `button`, `[role="button"]`

### Data Tables
- Rows: `tr`, `.table-row`, `.patient-row`
- Cells: `td`, `.cell`, `.data-cell`
- Headers: `th`, `.header`, `.column-header`

### Lists
- Items: `li`, `.list-item`, `.patient-item`
- Links: `a`, `.link`, `[href]`

## Testing Your Selectors

Always test in browser console:
```javascript
// Should return the element
document.querySelector('your-selector-here')

// Should return array of elements
document.querySelectorAll('your-selector-here')

// Get text content
document.querySelector('your-selector').textContent

// Get attribute value
document.querySelector('your-selector').getAttribute('name')
```

## Troubleshooting Common Issues

### Element Not Found
- Check if element is in iframe
- Wait for dynamic content to load
- Verify spelling and case sensitivity

### Multiple Elements
- Use more specific selectors
- Add parent element context
- Use nth-child or nth-of-type

### Dynamic Content
- Look for loading indicators
- Check Network tab for AJAX calls
- Wait for content to appear before extracting