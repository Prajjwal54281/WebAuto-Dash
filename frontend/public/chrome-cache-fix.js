// Chrome-specific cache clearing for WebAutoDash
console.log('🧹 Chrome Cache Fix: Clearing all caches...');

// Clear all types of Chrome caches
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(function (registrations) {
        for (let registration of registrations) {
            registration.unregister();
            console.log('🧹 Service worker unregistered');
        }
    });
}

// Clear Cache API
if ('caches' in window) {
    caches.keys().then(function (names) {
        for (let name of names) {
            caches.delete(name);
            console.log('🧹 Cache deleted:', name);
        }
    });
}

// Clear localStorage and sessionStorage
try {
    localStorage.clear();
    sessionStorage.clear();
    console.log('🧹 Local and session storage cleared');
} catch (e) {
    console.log('🧹 Storage clearing failed:', e);
}

// Force reload without cache
window.location.reload(true); 