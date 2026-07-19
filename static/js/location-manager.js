(function () {
    'use strict';

    const STORAGE_KEY = 'grabbite_selected_location';
    const PROMPTED_KEY = 'grabbite_location_prompted';
    const SEARCH_CACHE_KEY = 'grabbite_location_search_cache';
    const NOMINATIM_BASE = 'https://nominatim.openstreetmap.org';
    const SEARCH_DEBOUNCE_MS = 320;

    let searchTimer = null;
    let searchAbortController = null;

    function safeJsonParse(value, fallback) {
        try {
            return value ? JSON.parse(value) : fallback;
        } catch (_) {
            return fallback;
        }
    }

    function normalizeText(value) {
        return String(value || '').trim();
    }

    function compactParts(parts) {
        const seen = new Set();
        return parts
            .map(normalizeText)
            .filter(Boolean)
            .filter((part) => {
                const key = part.toLowerCase();
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
    }

    function pickArea(address) {
        return address.suburb ||
            address.neighbourhood ||
            address.quarter ||
            address.residential ||
            address.city_district ||
            address.town ||
            address.village ||
            address.hamlet ||
            address.county ||
            '';
    }

    function pickCity(address) {
        return address.city ||
            address.town ||
            address.village ||
            address.municipality ||
            address.county ||
            address.state_district ||
            '';
    }

    function formatDisplayName(location) {
        const area = normalizeText(location.area);
        const city = normalizeText(location.city);
        const state = normalizeText(location.state);
        const parts = compactParts([area, city || state]);
        return parts.join(', ') || normalizeText(location.name) || 'Select location';
    }

    function formatAddress(location) {
        const parts = compactParts([
            location.area,
            location.city,
            location.state,
            location.country,
        ]);
        return parts.join(', ') || location.name || '';
    }

    function createLocationFromNominatim(item, source) {
        const address = item.address || {};
        const lat = parseFloat(item.lat);
        const lon = parseFloat(item.lon);
        const area = pickArea(address);
        const city = pickCity(address);
        const state = address.state || address.region || '';
        const country = address.country || '';
        const name = formatDisplayName({
            area,
            city,
            state,
            name: item.name || item.display_name,
        });

        return {
            name,
            area,
            city,
            state,
            country,
            latitude: Number.isFinite(lat) ? lat : null,
            longitude: Number.isFinite(lon) ? lon : null,
            formattedAddress: formatAddress({ area, city, state, country, name: item.display_name }),
            source: source || 'manual',
            updatedAt: new Date().toISOString(),
        };
    }

    function getSavedLocation() {
        const value = safeJsonParse(localStorage.getItem(STORAGE_KEY), null);
        if (!value || typeof value !== 'object') return null;
        return value;
    }

    function saveLocation(location) {
        if (!location || typeof location !== 'object') return null;
        const normalized = {
            name: normalizeText(location.name) || formatDisplayName(location),
            area: normalizeText(location.area),
            city: normalizeText(location.city),
            state: normalizeText(location.state),
            country: normalizeText(location.country),
            latitude: location.latitude === null || location.latitude === undefined ? null : Number(location.latitude),
            longitude: location.longitude === null || location.longitude === undefined ? null : Number(location.longitude),
            formattedAddress: normalizeText(location.formattedAddress) || formatAddress(location),
            source: normalizeText(location.source) || 'manual',
            updatedAt: location.updatedAt || new Date().toISOString(),
        };

        localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
        localStorage.setItem(PROMPTED_KEY, '1');
        updateHeaderLocation(normalized);
        window.dispatchEvent(new CustomEvent('grabbite:location-updated', { detail: normalized }));
        return normalized;
    }

    function getSearchCache() {
        return safeJsonParse(sessionStorage.getItem(SEARCH_CACHE_KEY), {});
    }

    function setSearchCache(cache) {
        try {
            sessionStorage.setItem(SEARCH_CACHE_KEY, JSON.stringify(cache || {}));
        } catch (_) {
            // Ignore storage quota errors. Search still works without cache.
        }
    }

    async function reverseGeocode(latitude, longitude) {
        const url = `${NOMINATIM_BASE}/reverse?format=jsonv2&addressdetails=1&lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}&zoom=16&accept-language=en`;
        const response = await fetch(url, { method: 'GET' });
        if (!response.ok) throw new Error('Reverse geocoding failed');
        const data = await response.json();
        return createLocationFromNominatim({
            lat: latitude,
            lon: longitude,
            display_name: data.display_name,
            address: data.address || {},
        }, 'gps');
    }

    async function searchLocations(query) {
        const cleaned = normalizeText(query);
        if (cleaned.length < 2) return [];

        const cacheKey = cleaned.toLowerCase();
        const cache = getSearchCache();
        if (cache[cacheKey]) return cache[cacheKey];

        if (searchAbortController) searchAbortController.abort();
        searchAbortController = new AbortController();

        const url = `${NOMINATIM_BASE}/search?format=jsonv2&addressdetails=1&limit=6&q=${encodeURIComponent(cleaned)}&accept-language=en`;
        const response = await fetch(url, { signal: searchAbortController.signal });
        if (!response.ok) throw new Error('Location search failed');

        const data = await response.json();
        const results = (Array.isArray(data) ? data : []).map((item) => createLocationFromNominatim(item, 'manual'));
        cache[cacheKey] = results;
        setSearchCache(cache);
        return results;
    }

    function requestBrowserPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by this browser'));
                return;
            }

            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 12000,
                maximumAge: 1000 * 60 * 20,
            });
        });
    }

    async function useCurrentLocation(options) {
        const opts = options || {};
        setLocationStatus('Detecting your location...', 'loading');

        try {
            const position = await requestBrowserPosition();
            const coords = position.coords || {};
            const location = await reverseGeocode(coords.latitude, coords.longitude);
            const saved = saveLocation(location);
            setLocationStatus(`Delivering to ${formatDisplayName(saved)}`, 'success');
            closeDropdownSoon();
            return saved;
        } catch (error) {
            localStorage.setItem(PROMPTED_KEY, '1');
            const denied = error && error.code === 1;
            const message = denied
                ? 'Location permission was blocked. Search and select your delivery area.'
                : 'Could not detect your location. Search and select your delivery area.';
            setLocationStatus(message, 'warning');
            if (!opts.silent && window.showToast) window.showToast(message, 'warning');
            return null;
        }
    }

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, (char) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
        }[char]));
    }

    function getLocationTokens(location) {
        return compactParts([
            location && location.area,
            location && location.city,
            location && location.state,
            location && location.name,
        ]).map((part) => part.toLowerCase());
    }

    function locationScore(text, location) {
        const haystack = String(text || '').toLowerCase();
        if (!haystack || !location) return 0;
        const tokens = getLocationTokens(location);
        return tokens.reduce((score, token, index) => {
            if (!token) return score;
            if (haystack === token) return score + 100 - index;
            if (haystack.includes(token)) return score + 40 - index;
            return score;
        }, 0);
    }

    function updateHeaderLocation(location) {
        const label = document.getElementById('location-label');
        const detail = document.getElementById('location-detail');
        const currentAddress = document.getElementById('location-current-address');

        const activeLocation = location || getSavedLocation();
        if (label) {
            label.textContent = activeLocation ? formatDisplayName(activeLocation) : 'Set location';
            label.title = activeLocation ? formatAddress(activeLocation) : 'Choose delivery location';
        }
        if (detail) {
            detail.textContent = activeLocation ? 'Delivering to' : 'Choose delivery area';
        }
        if (currentAddress) {
            currentAddress.textContent = activeLocation
                ? formatAddress(activeLocation)
                : 'No delivery location selected yet.';
        }
    }

    function setLocationStatus(message, type) {
        const status = document.getElementById('location-status');
        if (!status) return;
        status.textContent = message || '';
        status.className = `location-status ${type || ''}`.trim();
    }

    function setSearchResults(results) {
        const resultsBox = document.getElementById('location-results');
        if (!resultsBox) return;

        if (!results || results.length === 0) {
            resultsBox.innerHTML = '<div class="location-result-empty">No matching locations found</div>';
            resultsBox.style.display = 'block';
            return;
        }

        resultsBox.innerHTML = results.map((location, index) => `
            <button type="button" class="location-result-item" data-index="${index}">
                <i class="fas fa-map-marker-alt"></i>
                <span>
                    <strong>${escapeHtml(formatDisplayName(location))}</strong>
                    <small>${escapeHtml(formatAddress(location))}</small>
                </span>
            </button>
        `).join('');
        resultsBox.__locationResults = results;
        resultsBox.style.display = 'block';
    }

    function closeDropdownSoon() {
        window.setTimeout(() => {
            const dropdown = document.getElementById('location-dropdown');
            const toggle = document.getElementById('location-toggle');
            if (dropdown) dropdown.classList.remove('open');
            if (toggle) toggle.setAttribute('aria-expanded', 'false');
        }, 650);
    }

    function toggleLocationDropdown(forceOpen) {
        const dropdown = document.getElementById('location-dropdown');
        const toggle = document.getElementById('location-toggle');
        if (!dropdown || !toggle) return;

        const shouldOpen = typeof forceOpen === 'boolean'
            ? forceOpen
            : !dropdown.classList.contains('open');
        dropdown.classList.toggle('open', shouldOpen);
        toggle.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');

        if (shouldOpen) {
            updateHeaderLocation();
            const input = document.getElementById('location-search-input');
            if (input) window.setTimeout(() => input.focus(), 80);
        }
    }

    function initHeaderLocation() {
        const wrapper = document.getElementById('header-location');
        if (!wrapper) return;

        const toggle = document.getElementById('location-toggle');
        const useCurrentBtn = document.getElementById('use-current-location-btn');
        const changeBtn = document.getElementById('change-location-btn');
        const input = document.getElementById('location-search-input');
        const resultsBox = document.getElementById('location-results');

        updateHeaderLocation();

        if (toggle) {
            toggle.addEventListener('click', (event) => {
                event.preventDefault();
                toggleLocationDropdown();
            });
        }

        if (useCurrentBtn) {
            useCurrentBtn.addEventListener('click', () => useCurrentLocation({ silent: false }));
        }

        if (changeBtn && input) {
            changeBtn.addEventListener('click', () => {
                toggleLocationDropdown(true);
                input.value = '';
                setLocationStatus('Search by area, city, society, or landmark.', 'info');
                input.focus();
            });
        }

        if (input) {
            input.addEventListener('input', () => {
                window.clearTimeout(searchTimer);
                const q = input.value.trim();

                if (q.length < 2) {
                    if (resultsBox) {
                        resultsBox.innerHTML = '';
                        resultsBox.style.display = 'none';
                    }
                    setLocationStatus('Type at least 2 characters to search.', 'info');
                    return;
                }

                setLocationStatus('Searching locations...', 'loading');
                searchTimer = window.setTimeout(async () => {
                    try {
                        const results = await searchLocations(q);
                        setSearchResults(results);
                        setLocationStatus(results.length ? 'Select a location from the list.' : 'No locations found.', results.length ? 'info' : 'warning');
                    } catch (error) {
                        if (error && error.name === 'AbortError') return;
                        setLocationStatus('Location search is unavailable right now. Try a more specific city or area.', 'warning');
                        if (resultsBox) resultsBox.style.display = 'none';
                    }
                }, SEARCH_DEBOUNCE_MS);
            });

            input.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    const firstResult = resultsBox && resultsBox.querySelector('.location-result-item');
                    if (firstResult) firstResult.click();
                }
            });
        }

        if (resultsBox) {
            resultsBox.addEventListener('click', (event) => {
                const item = event.target.closest('.location-result-item[data-index]');
                if (!item) return;
                const selected = resultsBox.__locationResults && resultsBox.__locationResults[Number(item.dataset.index)];
                if (!selected) return;
                const saved = saveLocation(selected);
                setLocationStatus(`Delivering to ${formatDisplayName(saved)}`, 'success');
                resultsBox.style.display = 'none';
                if (input) input.value = '';
                closeDropdownSoon();
            });
        }

        document.addEventListener('click', (event) => {
            if (!wrapper.contains(event.target)) toggleLocationDropdown(false);
        });

        const shouldPrompt = !getSavedLocation() && localStorage.getItem(PROMPTED_KEY) !== '1';
        if (shouldPrompt) {
            window.setTimeout(() => useCurrentLocation({ silent: true }), 700);
        }
    }

    function updateDeliveringCopy(location) {
        const targets = document.querySelectorAll('[data-location-text="deliver-to"]');
        const text = location ? formatDisplayName(location) : 'your selected location';
        targets.forEach((target) => {
            target.textContent = text;
        });
    }

    function sortRestaurantCards(location) {
        const grids = document.querySelectorAll('[data-location-sort="restaurants"]');
        grids.forEach((grid) => {
            const cards = Array.from(grid.querySelectorAll('[data-restaurant-location]'));
            if (cards.length < 2) return;
            cards.sort((a, b) => {
                const bScore = locationScore(b.dataset.restaurantLocation, location);
                const aScore = locationScore(a.dataset.restaurantLocation, location);
                if (bScore !== aScore) return bScore - aScore;
                return Number(b.dataset.restaurantRating || 0) - Number(a.dataset.restaurantRating || 0);
            });
            cards.forEach((card) => grid.appendChild(card));
        });
    }

    function applyLocationToCheckout(location) {
        const textarea = document.getElementById('delivery-address');
        if (!textarea || textarea.value.trim() || !location) return;
        textarea.value = formatAddress(location);
    }

    function applyPageLocation(location) {
        const activeLocation = location || getSavedLocation();
        updateDeliveringCopy(activeLocation);
        sortRestaurantCards(activeLocation);
        applyLocationToCheckout(activeLocation);
    }

    document.addEventListener('DOMContentLoaded', () => {
        initHeaderLocation();
        applyPageLocation(getSavedLocation());
    });

    window.addEventListener('grabbite:location-updated', (event) => {
        applyPageLocation(event.detail);
    });

    window.GrabBiteLocation = {
        getSavedLocation,
        saveLocation,
        useCurrentLocation,
        reverseGeocode,
        searchLocations,
        formatDisplayName,
        formatAddress,
        locationScore,
    };
})();
