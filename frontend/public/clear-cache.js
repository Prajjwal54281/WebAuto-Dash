// Clear browser cache and force reload
console.log('🧹 Clearing browser cache...');

// Clear localStorage
localStorage.clear();

// Clear sessionStorage
sessionStorage.clear();

// Clear any service worker cache
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(function (registrations) {
        for (let registration of registrations) {
            registration.unregister();
        }
    });
}

// Clear browser cache using Cache API
if ('caches' in window) {
    caches.keys().then(function (names) {
        for (let name of names) {
            caches.delete(name);
        }
    });
}

console.log('✅ Browser cache cleared. Reloading...');

// Force reload without cache
window.location.reload(true); 