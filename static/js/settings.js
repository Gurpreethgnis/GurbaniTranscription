/**
 * Settings Page JavaScript
 * Handles ASR provider configuration and settings persistence
 */

// Current settings state
let currentSettings = {
    primaryProvider: 'whisper',
    fallbackProvider: '',
    whisper: {
        model: 'large'
    },
    indicconformer: {
        model: 'ai4bharat/indicconformer_stt_hi_hybrid_rnnt_large',
        language: 'pa'
    },
    wav2vec2: {
        model: 'Harveenchadha/vakyansh-wav2vec2-punjabi-pam-10'
    },
    commercial: {
        enabled: false,
        apiKey: '',
        provider: 'elevenlabs'
    },
    processing: {
        denoising: false,
        denoiseBackend: 'noisereduce',
        enableFusion: true,
        fusionThreshold: 0.85
    },
    domain: {
        mode: 'sggs',
        strictGurmukhi: true,
        enableCorrection: true,
        scriptPurityThreshold: 0.95,
        latinRatioThreshold: 0.02,
        oovRatioThreshold: 0.35
    }
};

// Provider capabilities (loaded from API)
let providerCapabilities = {};

/**
 * Initialize settings page
 */
document.addEventListener('DOMContentLoaded', async () => {
    await loadProviderCapabilities();
    await loadSettings();
    setupEventListeners();
    updateUI();
});

/**
 * Load provider capabilities from API
 */
async function loadProviderCapabilities() {
    try {
        const response = await fetch('/api/providers');
        if (response.ok) {
            providerCapabilities = await response.json();
            renderProviderCards();
            updateProviderStatus();
        }
    } catch (error) {
        console.error('Failed to load provider capabilities:', error);
        showStatus('providerStatus', 'Error loading providers', 'error');
    }
}

/**
 * Load settings from server/localStorage
 */
async function loadSettings() {
    try {
        // Try to load from server first
        const response = await fetch('/api/settings');
        if (response.ok) {
            const serverSettings = await response.json();
            currentSettings = { ...currentSettings, ...serverSettings };
        }
    } catch (error) {
        console.error('Failed to load settings from server:', error);
    }
    
    // Also check localStorage for any local overrides
    const localSettings = localStorage.getItem('kathaSettings');
    if (localSettings) {
        try {
            const parsed = JSON.parse(localSettings);
            currentSettings = { ...currentSettings, ...parsed };
        } catch (e) {
            console.error('Failed to parse local settings:', e);
        }
    }
    
    // Apply settings to UI
    applySettingsToUI();
}

/**
 * Apply current settings to UI elements
 */
function applySettingsToUI() {
    // Primary provider (handled by card selection)
    selectProviderCard(currentSettings.primaryProvider);
    
    // Fallback provider
    const fallbackSelect = document.getElementById('fallbackProvider');
    if (fallbackSelect) {
        fallbackSelect.value = currentSettings.fallbackProvider || '';
    }
    
    // Whisper settings
    const whisperModel = document.getElementById('whisperModel');
    if (whisperModel) {
        whisperModel.value = currentSettings.whisper?.model || 'large';
    }
    
    // IndicConformer settings
    const indicModel = document.getElementById('indicconformerModel');
    if (indicModel) {
        indicModel.value = currentSettings.indicconformer?.model || '';
    }
    const indicLang = document.getElementById('indicconformerLanguage');
    if (indicLang) {
        indicLang.value = currentSettings.indicconformer?.language || 'pa';
    }
    
    // Wav2Vec2 settings
    const wav2vecModel = document.getElementById('wav2vec2Model');
    if (wav2vecModel) {
        wav2vecModel.value = currentSettings.wav2vec2?.model || '';
    }
    
    // Commercial settings
    const commercialEnabled = document.getElementById('commercialEnabled');
    if (commercialEnabled) {
        commercialEnabled.checked = currentSettings.commercial?.enabled || false;
        toggleCommercialFields();
    }
    const commercialApiKey = document.getElementById('commercialApiKey');
    if (commercialApiKey && currentSettings.commercial?.apiKey) {
        commercialApiKey.value = currentSettings.commercial.apiKey;
    }
    const commercialProvider = document.getElementById('commercialProvider');
    if (commercialProvider) {
        commercialProvider.value = currentSettings.commercial?.provider || 'elevenlabs';
    }
    
    // Processing settings
    const defaultDenoising = document.getElementById('defaultDenoising');
    if (defaultDenoising) {
        defaultDenoising.checked = currentSettings.processing?.denoising || false;
    }
    const defaultDenoiseBackend = document.getElementById('defaultDenoiseBackend');
    if (defaultDenoiseBackend) {
        defaultDenoiseBackend.value = currentSettings.processing?.denoiseBackend || 'noisereduce';
    }
    const enableFusion = document.getElementById('enableFusion');
    if (enableFusion) {
        enableFusion.checked = currentSettings.processing?.enableFusion !== false;
    }
    const fusionThreshold = document.getElementById('fusionThreshold');
    if (fusionThreshold) {
        fusionThreshold.value = currentSettings.processing?.fusionThreshold || 0.85;
        updateSliderValue('fusionThreshold', 'fusionThresholdValue');
    }
    
    // Domain settings
    const domainMode = currentSettings.domain?.mode || 'sggs';
    const domainRadio = document.querySelector(`input[name="domainMode"][value="${domainMode}"]`);
    if (domainRadio) {
        domainRadio.checked = true;
    }
    
    const strictGurmukhi = document.getElementById('strictGurmukhi');
    if (strictGurmukhi) {
        strictGurmukhi.checked = currentSettings.domain?.strictGurmukhi !== false;
    }
    
    const enableDomainCorrection = document.getElementById('enableDomainCorrection');
    if (enableDomainCorrection) {
        enableDomainCorrection.checked = currentSettings.domain?.enableCorrection !== false;
    }
    
    const scriptPurityThreshold = document.getElementById('scriptPurityThreshold');
    if (scriptPurityThreshold) {
        scriptPurityThreshold.value = currentSettings.domain?.scriptPurityThreshold || 0.95;
        updateSliderValue('scriptPurityThreshold', 'scriptPurityThresholdValue');
    }
    
    const latinRatioThreshold = document.getElementById('latinRatioThreshold');
    if (latinRatioThreshold) {
        latinRatioThreshold.value = currentSettings.domain?.latinRatioThreshold || 0.02;
        updateSliderValue('latinRatioThreshold', 'latinRatioThresholdValue');
    }
    
    const oovRatioThreshold = document.getElementById('oovRatioThreshold');
    if (oovRatioThreshold) {
        oovRatioThreshold.value = currentSettings.domain?.oovRatioThreshold || 0.35;
        updateSliderValue('oovRatioThreshold', 'oovRatioThresholdValue');
    }
}

/**
 * Render provider selection cards
 */
function renderProviderCards() {
    const grid = document.getElementById('primaryProviderGrid');
    if (!grid) return;
    
    const providers = [
        {
            id: 'whisper',
            name: 'Whisper',
            description: 'Fast, multilingual baseline with excellent timestamps',
            icon: '🎤',
            features: ['Timestamps', 'Word-level', 'Multi-language']
        },
        {
            id: 'indicconformer',
            name: 'IndicConformer',
            description: 'AI4Bharat model optimized for Indian languages',
            icon: '🇮🇳',
            features: ['Indic native', 'Gurmukhi', 'Timestamps']
        },
        {
            id: 'wav2vec2',
            name: 'Wav2Vec2 Punjabi',
            description: 'Direct Punjabi transcription without translation',
            icon: '🔊',
            features: ['Punjabi native', 'Gurmukhi', 'Open-source']
        },
        {
            id: 'commercial',
            name: 'Commercial',
            description: 'ElevenLabs API for high-quality results',
            icon: '💼',
            features: ['High accuracy', 'Word timestamps', 'API required']
        }
    ];
    
    grid.innerHTML = providers.map(provider => {
        const capabilities = providerCapabilities[provider.id] || {};
        const isAvailable = capabilities.is_available !== false;
        const isSelected = currentSettings.primaryProvider === provider.id;
        
        return `
            <div class="provider-card ${isSelected ? 'selected' : ''} ${!isAvailable ? 'unavailable' : ''}"
                 data-provider="${provider.id}"
                 onclick="selectProvider('${provider.id}')">
                <div class="provider-card-header">
                    <span class="provider-icon">${provider.icon}</span>
                    <span class="provider-name">${provider.name}</span>
                    ${!isAvailable ? '<span class="unavailable-badge">Unavailable</span>' : ''}
                </div>
                <p class="provider-description">${provider.description}</p>
                <div class="provider-features">
                    ${provider.features.map(f => `<span class="feature-tag">${f}</span>`).join('')}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Select a provider card
 */
function selectProvider(providerId) {
    // Check if provider is available
    const capabilities = providerCapabilities[providerId];
    if (capabilities && capabilities.is_available === false) {
        showStatus('saveStatus', `Provider "${providerId}" is not available. Install required dependencies.`, 'error');
        return;
    }
    
    // Update selection
    currentSettings.primaryProvider = providerId;
    selectProviderCard(providerId);
    
    // Show provider-specific settings
    highlightProviderSettings(providerId);
}

/**
 * Update provider card selection UI
 */
function selectProviderCard(providerId) {
    const cards = document.querySelectorAll('.provider-card');
    cards.forEach(card => {
        if (card.dataset.provider === providerId) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });
}

/**
 * Highlight the settings card for selected provider
 */
function highlightProviderSettings(providerId) {
    const settingsCards = document.querySelectorAll('.settings-card[data-provider]');
    settingsCards.forEach(card => {
        if (card.dataset.provider === providerId) {
            card.classList.add('highlighted');
            // Expand the card
            const content = card.querySelector('.card-content');
            if (content) content.style.display = 'block';
        } else {
            card.classList.remove('highlighted');
        }
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Commercial enabled toggle
    const commercialEnabled = document.getElementById('commercialEnabled');
    if (commercialEnabled) {
        commercialEnabled.addEventListener('change', toggleCommercialFields);
    }
    
    // Fusion threshold slider
    const fusionThreshold = document.getElementById('fusionThreshold');
    if (fusionThreshold) {
        fusionThreshold.addEventListener('input', () => {
            updateSliderValue('fusionThreshold', 'fusionThresholdValue');
        });
    }
    
    // Domain threshold sliders
    const scriptPurityThreshold = document.getElementById('scriptPurityThreshold');
    if (scriptPurityThreshold) {
        scriptPurityThreshold.addEventListener('input', () => {
            updateSliderValue('scriptPurityThreshold', 'scriptPurityThresholdValue');
        });
    }
    
    const latinRatioThreshold = document.getElementById('latinRatioThreshold');
    if (latinRatioThreshold) {
        latinRatioThreshold.addEventListener('input', () => {
            updateSliderValue('latinRatioThreshold', 'latinRatioThresholdValue');
        });
    }
    
    const oovRatioThreshold = document.getElementById('oovRatioThreshold');
    if (oovRatioThreshold) {
        oovRatioThreshold.addEventListener('input', () => {
            updateSliderValue('oovRatioThreshold', 'oovRatioThresholdValue');
        });
    }
    
    // Auto-save on input changes (debounced)
    const inputs = document.querySelectorAll('.settings-input, .settings-select, input[type="checkbox"], input[type="range"], input[type="radio"]');
    inputs.forEach(input => {
        input.addEventListener('change', debounce(autoSave, 1000));
    });
}

/**
 * Toggle commercial provider fields visibility
 */
function toggleCommercialFields() {
    const enabled = document.getElementById('commercialEnabled')?.checked;
    const fields = document.querySelectorAll('.commercial-field');
    fields.forEach(field => {
        field.style.display = enabled ? 'flex' : 'none';
    });
}

/**
 * Toggle API key visibility
 */
function toggleApiKeyVisibility() {
    const input = document.getElementById('commercialApiKey');
    if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
    }
}

/**
 * Test commercial API connection
 */
async function testCommercialApi() {
    const resultSpan = document.getElementById('apiTestResult');
    const apiKey = document.getElementById('commercialApiKey')?.value;
    
    if (!apiKey) {
        resultSpan.textContent = 'Please enter an API key';
        resultSpan.className = 'test-result error';
        return;
    }
    
    resultSpan.textContent = 'Testing...';
    resultSpan.className = 'test-result';
    
    try {
        const response = await fetch('/api/test-commercial', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });
        
        const result = await response.json();
        
        if (result.success) {
            resultSpan.textContent = '✓ Connection successful';
            resultSpan.className = 'test-result success';
            if (result.quota) {
                resultSpan.textContent += ` (${result.quota.character_count}/${result.quota.character_limit} chars)`;
            }
        } else {
            resultSpan.textContent = '✗ ' + (result.error || 'Connection failed');
            resultSpan.className = 'test-result error';
        }
    } catch (error) {
        resultSpan.textContent = '✗ Test failed: ' + error.message;
        resultSpan.className = 'test-result error';
    }
}

/**
 * Toggle collapsible card
 */
function toggleCard(header) {
    const card = header.closest('.collapsible');
    const content = card.querySelector('.card-content');
    const icon = header.querySelector('.collapse-icon');
    
    if (content.style.display === 'none' || !content.style.display) {
        content.style.display = 'block';
        icon.textContent = '▲';
    } else {
        content.style.display = 'none';
        icon.textContent = '▼';
    }
}

/**
 * Update slider value display
 */
function updateSliderValue(sliderId, valueId) {
    const slider = document.getElementById(sliderId);
    const valueSpan = document.getElementById(valueId);
    if (slider && valueSpan) {
        valueSpan.textContent = slider.value;
    }
}

/**
 * Collect current settings from UI
 */
function collectSettingsFromUI() {
    // Get selected domain mode
    const domainModeRadio = document.querySelector('input[name="domainMode"]:checked');
    const domainMode = domainModeRadio?.value || 'sggs';
    
    return {
        primaryProvider: currentSettings.primaryProvider,
        fallbackProvider: document.getElementById('fallbackProvider')?.value || '',
        whisper: {
            model: document.getElementById('whisperModel')?.value || 'large'
        },
        indicconformer: {
            model: document.getElementById('indicconformerModel')?.value || '',
            language: document.getElementById('indicconformerLanguage')?.value || 'pa'
        },
        wav2vec2: {
            model: document.getElementById('wav2vec2Model')?.value || ''
        },
        commercial: {
            enabled: document.getElementById('commercialEnabled')?.checked || false,
            apiKey: document.getElementById('commercialApiKey')?.value || '',
            provider: document.getElementById('commercialProvider')?.value || 'elevenlabs'
        },
        processing: {
            denoising: document.getElementById('defaultDenoising')?.checked || false,
            denoiseBackend: document.getElementById('defaultDenoiseBackend')?.value || 'noisereduce',
            enableFusion: document.getElementById('enableFusion')?.checked !== false,
            fusionThreshold: parseFloat(document.getElementById('fusionThreshold')?.value || 0.85)
        },
        domain: {
            mode: domainMode,
            strictGurmukhi: document.getElementById('strictGurmukhi')?.checked !== false,
            enableCorrection: document.getElementById('enableDomainCorrection')?.checked !== false,
            scriptPurityThreshold: parseFloat(document.getElementById('scriptPurityThreshold')?.value || 0.95),
            latinRatioThreshold: parseFloat(document.getElementById('latinRatioThreshold')?.value || 0.02),
            oovRatioThreshold: parseFloat(document.getElementById('oovRatioThreshold')?.value || 0.35)
        }
    };
}

/**
 * Save settings to server and localStorage
 */
async function saveSettings() {
    const settings = collectSettingsFromUI();
    
    showStatus('saveStatus', 'Saving...', '');
    
    try {
        // Save to server
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            // Also save to localStorage
            localStorage.setItem('kathaSettings', JSON.stringify(settings));
            currentSettings = settings;
            
            showStatus('saveStatus', '✓ Settings saved', 'success');
        } else {
            const error = await response.json();
            showStatus('saveStatus', '✗ ' + (error.error || 'Save failed'), 'error');
        }
    } catch (error) {
        console.error('Failed to save settings:', error);
        
        // Save to localStorage as fallback
        localStorage.setItem('kathaSettings', JSON.stringify(settings));
        currentSettings = settings;
        
        showStatus('saveStatus', '⚠ Saved locally only', 'warning');
    }
}

/**
 * Auto-save settings (called on input change)
 */
function autoSave() {
    const settings = collectSettingsFromUI();
    localStorage.setItem('kathaSettings', JSON.stringify(settings));
    currentSettings = settings;
}

/**
 * Reset settings to defaults
 */
function resetSettings() {
    if (!confirm('Reset all settings to defaults? This cannot be undone.')) {
        return;
    }
    
    currentSettings = {
        primaryProvider: 'whisper',
        fallbackProvider: '',
        whisper: { model: 'large' },
        indicconformer: { model: 'ai4bharat/indicconformer_stt_hi_hybrid_rnnt_large', language: 'pa' },
        wav2vec2: { model: 'Harveenchadha/vakyansh-wav2vec2-punjabi-pam-10' },
        commercial: { enabled: false, apiKey: '', provider: 'elevenlabs' },
        processing: { denoising: false, denoiseBackend: 'noisereduce', enableFusion: true, fusionThreshold: 0.85 },
        domain: { mode: 'sggs', strictGurmukhi: true, enableCorrection: true, scriptPurityThreshold: 0.95, latinRatioThreshold: 0.02, oovRatioThreshold: 0.35 }
    };
    
    localStorage.removeItem('kathaSettings');
    applySettingsToUI();
    selectProviderCard('whisper');
    
    showStatus('saveStatus', 'Settings reset to defaults', 'success');
}

/**
 * Update provider status badge
 */
function updateProviderStatus() {
    const statusBadge = document.getElementById('providerStatus');
    if (!statusBadge) return;
    
    const available = Object.values(providerCapabilities).filter(c => c.is_available).length;
    const total = Object.keys(providerCapabilities).length;
    
    statusBadge.textContent = `${available}/${total} providers available`;
    statusBadge.className = available === total ? 'section-badge success' : 'section-badge warning';
}

/**
 * Update UI based on current state
 */
function updateUI() {
    toggleCommercialFields();
}

/**
 * Show status message
 */
function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.className = `save-status ${type}`;
        
        // Auto-clear after 5 seconds for success messages
        if (type === 'success') {
            setTimeout(() => {
                element.textContent = '';
                element.className = 'save-status';
            }, 5000);
        }
    }
}

/**
 * Debounce helper
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

