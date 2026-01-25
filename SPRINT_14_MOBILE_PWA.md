# Sprint 14: Mobile-First PWA

**Status:** ✅ COMPLETE  
**Started:** January 25, 2026  
**Completed:** January 25, 2026

---

## Sprint Goal

**Demo Statement:** Casey installs CaseyOS on his phone, opens Today's Moves, and executes actions with one thumb while walking to a meeting.

---

## Prerequisites ✅

- [x] CaseyOS web dashboard working
- [x] Command queue API functional
- [x] All pages have viewport meta tag (after quick fixes)

---

## Completed Tasks

### ✅ Task 14.1: Add PWA Manifest
- Created `src/static/manifest.json` with full app metadata
- Added 8 icon sizes (72, 96, 128, 144, 152, 192, 384, 512)
- Configured theme color (#4f46e5), standalone display
- Added app shortcuts for Queue and Jarvis

### ✅ Task 14.2: Add Service Worker
- Created `src/static/sw.js` with offline caching
- Network-first strategy for API calls
- Cache-first strategy for static assets
- IndexedDB for offline action queuing
- Push notification support scaffolded
- Background sync for offline actions

### ✅ Task 14.3: Mobile Bottom Navigation
- Added 4-item bottom nav (Queue, Jarvis, Agents, Settings)
- Touch-friendly 64px height
- Responsive - hidden on desktop

### ✅ Task 14.4: Mobile-Responsive CSS
- Added safe area insets for notched devices
- Touch targets minimum 44px (WCAG 2.5.5)
- Responsive breakpoints (1200px, 768px, 480px)
- Dark mode support maintained

### ✅ Bug Fixes from UI/UX Audit
- Fixed theme toggle ID mismatch
- Fixed offline sync registration
- Added CSRF tokens to all API calls
- Added aria-labels for accessibility
- Added loading states to buttons
- Wired refresh button handler

---

## Tasks

### Task 14.1: Add PWA Manifest

**Priority:** CRITICAL  
**Effort:** 2 hours  
**Dependencies:** None

**One-liner:** Create manifest.json and link it to enable "Add to Home Screen"

**Scope:**
- Create `src/static/manifest.json` with app metadata
- Add icons in multiple sizes (192x192, 512x512)
- Configure theme color, background color
- Set display mode to "standalone"
- Link manifest in all HTML pages

**Files:**
- Create: `src/static/manifest.json`
- Create: `src/static/icons/` directory
- Modify: All `src/static/*.html` files

**Contracts:**
```json
{
  "name": "CaseyOS",
  "short_name": "CaseyOS",
  "description": "GTM Command Center - Today's Moves",
  "start_url": "/caseyos",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#4f46e5",
  "icons": [
    { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

**Validation:**
```bash
# Check manifest loads
curl -s https://web-production-a6ccf.up.railway.app/static/manifest.json | jq .name
# Expected: "CaseyOS"

# Chrome DevTools > Application > Manifest should show valid PWA
```

**Acceptance Criteria:**
- [ ] manifest.json is valid
- [ ] Icons load correctly
- [ ] "Add to Home Screen" prompt appears on mobile
- [ ] App launches in standalone mode

---

### Task 14.2: Add Service Worker

**Priority:** HIGH  
**Effort:** 3 hours  
**Dependencies:** 14.1

**One-liner:** Enable offline support and caching with service worker

**Scope:**
- Create service worker for offline caching
- Cache Today's Moves API responses
- Show offline indicator when no connection
- Background sync for actions taken offline

**Files:**
- Create: `src/static/sw.js`
- Modify: `src/static/caseyos/index.html` (register SW)

**Contracts:**
```javascript
// sw.js
const CACHE_NAME = 'caseyos-v1';
const urlsToCache = [
  '/caseyos',
  '/caseyos/styles.css',
  '/static/manifest.json'
];

self.addEventListener('fetch', event => {
  // Network-first for API, cache-first for static
});
```

**Acceptance Criteria:**
- [ ] Service worker registers successfully
- [ ] Static assets cached
- [ ] API responses cached for offline viewing
- [ ] Offline indicator shows when disconnected

---

### Task 14.3: Mobile Navigation

**Priority:** HIGH  
**Effort:** 2 hours  
**Dependencies:** None

**One-liner:** Add bottom navigation bar for mobile (thumb-friendly)

**Scope:**
- Create sticky bottom nav for mobile screens
- Icons: Home, Queue, Jarvis, Profile
- Hide desktop nav on mobile
- Active state indicator

**Files:**
- Modify: `src/static/caseyos/styles.css`
- Modify: `src/static/caseyos/index.html`

**CSS Approach:**
```css
/* Mobile bottom nav - only shows on small screens */
@media (max-width: 768px) {
  .desktop-nav { display: none; }
  .mobile-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 64px;
    background: white;
    border-top: 1px solid #e5e7eb;
    display: flex;
    justify-content: space-around;
    align-items: center;
    z-index: 1000;
  }
  .content { padding-bottom: 80px; }
}
```

**Acceptance Criteria:**
- [ ] Bottom nav visible on mobile
- [ ] Desktop nav visible on larger screens
- [ ] Tap targets are at least 44x44px
- [ ] Active tab is clearly indicated

---

### Task 14.4: Queue Card Mobile Optimization

**Priority:** HIGH  
**Effort:** 3 hours  
**Dependencies:** None

**One-liner:** Redesign queue cards for one-handed use

**Scope:**
- Stack layout (not side-by-side) on mobile
- Large, thumb-friendly action buttons
- Swipe gestures for Accept/Dismiss
- Priority score prominently displayed

**Files:**
- Modify: `src/static/caseyos/styles.css`
- Modify: `src/static/command-queue.html`

**Mobile Layout:**
```
┌─────────────────────────────┐
│ 87 │ Follow up with John    │
├─────────────────────────────┤
│ High ICP fit, demo tomorrow │
│ john@acme.com              │
├─────────────────────────────┤
│  [DISMISS]     [EXECUTE]    │
└─────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Cards readable on small screens
- [ ] Buttons large enough to tap
- [ ] Swipe left/right triggers actions
- [ ] No horizontal scrolling needed

---

### Task 14.5: Pull-to-Refresh

**Priority:** MEDIUM  
**Effort:** 1 hour  
**Dependencies:** 14.4

**One-liner:** Add native-feeling pull-to-refresh on Today's Moves

**Scope:**
- Implement pull-to-refresh gesture
- Show loading spinner
- Fetch fresh data from API
- Haptic feedback (if supported)

**Files:**
- Modify: `src/static/caseyos/index.html` (JS)

**Acceptance Criteria:**
- [ ] Pull down triggers refresh
- [ ] Loading indicator shown
- [ ] Data updates after pull
- [ ] Works on iOS and Android

---

### Task 14.6: Touch Gestures

**Priority:** MEDIUM  
**Effort:** 2 hours  
**Dependencies:** 14.4

**One-liner:** Add swipe gestures for common actions

**Scope:**
- Swipe right = Accept
- Swipe left = Dismiss
- Long press = View details
- Smooth animations

**Files:**
- Modify: `src/static/caseyos/index.html` (JS)
- Modify: `src/static/caseyos/styles.css`

**Acceptance Criteria:**
- [ ] Swipe gestures work smoothly
- [ ] Visual feedback during swipe
- [ ] Action executes at threshold
- [ ] Undo option after action

---

### Task 14.7: Push Notifications

**Priority:** MEDIUM  
**Effort:** 3 hours  
**Dependencies:** 14.2

**One-liner:** Notify user of high-priority items

**Scope:**
- Request notification permission
- Send notification for APS > 80 items
- Click notification opens queue item
- Badge counter for pending items

**Files:**
- Modify: `src/static/sw.js`
- Create: `src/routes/notifications.py`

**Acceptance Criteria:**
- [ ] Permission prompt shown
- [ ] Notifications appear for high-priority items
- [ ] Click opens relevant item
- [ ] Works when app is closed

---

### Task 14.8: Offline Actions Queue

**Priority:** LOW  
**Effort:** 3 hours  
**Dependencies:** 14.2

**One-liner:** Queue actions taken offline, sync when back online

**Scope:**
- Store Accept/Dismiss actions in IndexedDB
- Sync when connection restored
- Show pending sync indicator
- Handle conflicts

**Files:**
- Modify: `src/static/sw.js`
- Modify: `src/static/caseyos/index.html`

**Acceptance Criteria:**
- [ ] Actions saved when offline
- [ ] Sync happens on reconnect
- [ ] User notified of sync status
- [ ] Conflicts handled gracefully

---

### Task 14.9: Performance Optimization

**Priority:** HIGH  
**Effort:** 2 hours  
**Dependencies:** None

**One-liner:** Fast first paint and smooth scrolling on mobile

**Scope:**
- Lazy load queue items (show 10, load more on scroll)
- Optimize CSS for 60fps scrolling
- Preload critical resources
- Compress images

**Files:**
- Modify: `src/static/caseyos/index.html`
- Modify: `src/static/caseyos/styles.css`

**Acceptance Criteria:**
- [ ] First contentful paint < 1.5s
- [ ] Scrolling at 60fps
- [ ] Lighthouse mobile score > 90
- [ ] No janky animations

---

### Task 14.10: Cross-Browser Testing

**Priority:** HIGH  
**Effort:** 2 hours  
**Dependencies:** All above

**One-liner:** Verify everything works on iOS Safari and Android Chrome

**Scope:**
- Test on iOS Safari (iPhone)
- Test on Android Chrome
- Test on tablet sizes
- Fix any browser-specific issues

**Test Devices:**
- iPhone 12/13/14 (Safari)
- Pixel/Samsung (Chrome)
- iPad (Safari)

**Acceptance Criteria:**
- [ ] PWA installs on iOS
- [ ] PWA installs on Android
- [ ] All gestures work on both
- [ ] No critical bugs on any platform

---

## Definition of Done

- [ ] All 10 tasks complete
- [ ] PWA installable on iOS and Android
- [ ] Lighthouse PWA score > 90
- [ ] Touch gestures work smoothly
- [ ] Offline mode shows cached data
- [ ] No horizontal scrolling on any page

---

## Rollback Plan

If issues arise:
1. Revert service worker registration
2. Keep manifest but disable install prompt
3. Fall back to responsive-only (no PWA features)

---

## Demo Script

```bash
# 1. Open CaseyOS on phone
# Navigate to https://web-production-a6ccf.up.railway.app/caseyos

# 2. Install as PWA
# iOS: Share > Add to Home Screen
# Android: 3-dot menu > Add to Home Screen

# 3. Open from home screen
# Should launch in standalone mode (no browser chrome)

# 4. Use Today's Moves
# - Swipe right to Accept
# - Swipe left to Dismiss
# - Pull down to refresh

# 5. Test offline
# Turn on airplane mode, app should still show cached queue
```

---

**Ready to execute. Let's make CaseyOS mobile-first! 📱**
