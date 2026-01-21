/**
 * Translation page JavaScript
 * Handles language selection, translation requests, and result display
 */

// Use shared utilities
const { escapeHtml, formatTime } = window.KathaUtils || {
    escapeHtml: (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    formatTime: (seconds) => {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
};

// Application state
const translateState = {
    transcriptions: [],
    selectedTranscription: null,
    transcriptionData: null,
    languages: [],
    languageStatuses: [],
    selectedLanguages: new Set(),
    sourceLanguage: 'pa',
    translationResults: {},
    currentTab: null,
    providers: {}
};

// DOM elements
const transcriptionSelect = document.getElementById('transcriptionSelect');
const loadBtn = document.getElementById('loadBtn');
const transcriptionInfo = document.getElementById('transcriptionInfo');
const languageSection = document.getElementById('languageSection');
const languageGrid = document.getElementById('languageGrid');
const translateBtn = document.getElementById('translateBtn');
const selectedCount = document.getElementById('selectedCount');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const progressDetails = document.getElementById('progressDetails');
const resultsSection = document.getElementById('resultsSection');
const resultsTabs = document.getElementById('resultsTabs');
const resultsContent = document.getElementById('resultsContent');
const statusMessage = document.getElementById('statusMessage');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadTranscriptions();
    loadProviders();
});

function initializeEventListeners() {
    // Transcription selection
    transcriptionSelect.addEventListener('change', handleTranscriptionChange);
    loadBtn.addEventListener('click', loadSelectedTranscription);
    
    // Translation
    translateBtn.addEventListener('click', startTranslation);
    
    // Results
    document.getElementById('downloadAllBtn')?.addEventListener('click', downloadAllTranslations);
    document.getElementById('copyBtn')?.addEventListener('click', copyCurrentTranslation);
    
    // Provider settings toggle
    const toggleProviderBtn = document.getElementById('toggleProviderBtn');
    if (toggleProviderBtn) {
        toggleProviderBtn.addEventListener('click', toggleProviderSettings);
    }
}

async function loadTranscriptions() {
    try {
        const response = await fetch('/log');
        if (!response.ok) throw new Error('Failed to load transcriptions');
        
        const data = await response.json();
        translateState.transcriptions = data.log || [];
        
        // Filter to only successful transcriptions
        const successful = translateState.transcriptions.filter(t => t.status === 'success');
        
        transcriptionSelect.innerHTML = '<option value="">Select a transcription...</option>';
        
        successful.forEach(t => {
            const option = document.createElement('option');
            option.value = t.filename;
            option.textContent = `${t.filename} (${t.timestamp || 'Unknown date'})`;
            transcriptionSelect.appendChild(option);
        });
        
        loadBtn.disabled = true;
        
    } catch (error) {
        console.error('Failed to load transcriptions:', error);
        updateStatus('Failed to load transcriptions', 'error');
    }
}

async function loadProviders() {
    try {
        const response = await fetch('/api/translation-providers');
        if (!response.ok) throw new Error('Failed to load providers');
        
        const data = await response.json();
        translateState.providers = data.providers || {};
        
        // Update provider status indicators
        Object.entries(translateState.providers).forEach(([name, info]) => {
            const statusEl = document.getElementById(`${name}Status`);
            if (statusEl) {
                if (info.available) {
                    statusEl.textContent = '✓ Available';
                    statusEl.className = 'provider-status available';
                } else {
                    statusEl.textContent = '✗ Not configured';
                    statusEl.className = 'provider-status unavailable';
                }
            }
        });
        
    } catch (error) {
        console.error('Failed to load providers:', error);
    }
}

function handleTranscriptionChange() {
    const filename = transcriptionSelect.value;
    loadBtn.disabled = !filename;
    
    // Reset state
    translateState.selectedTranscription = filename;
    translateState.transcriptionData = null;
    translateState.selectedLanguages.clear();
    translateState.translationResults = {};
    
    // Hide sections
    transcriptionInfo.style.display = 'none';
    languageSection.style.display = 'none';
    resultsSection.style.display = 'none';
    progressSection.style.display = 'none';
}

async function loadSelectedTranscription() {
    const filename = translateState.selectedTranscription;
    if (!filename) return;
    
    loadBtn.disabled = true;
    loadBtn.textContent = 'Loading...';
    
    try {
        // Get languages with cache status for this transcription
        const langResponse = await fetch(`/api/translation-languages?filename=${encodeURIComponent(filename)}`);
        if (!langResponse.ok) throw new Error('Failed to load language information');
        
        const langData = await langResponse.json();
        translateState.languages = langData.languages || [];
        translateState.languageStatuses = langData.language_statuses || [];
        translateState.sourceLanguage = langData.source_language || 'pa';
        
        // Show transcription info
        document.getElementById('sourceLanguage').textContent = 
            translateState.sourceLanguage === 'pa' ? 'Punjabi (ਪੰਜਾਬੀ)' : 'English';
        
        // Get segment info from log
        const transcription = translateState.transcriptions.find(t => t.filename === filename);
        if (transcription) {
            document.getElementById('segmentCount').textContent = 'Loaded';
        }
        
        transcriptionInfo.style.display = 'block';
        
        // Populate language grid
        populateLanguageGrid();
        languageSection.style.display = 'block';
        
        updateStatus('Transcription loaded. Select languages to translate.', 'success');
        
    } catch (error) {
        console.error('Failed to load transcription:', error);
        updateStatus(`Failed to load transcription: ${error.message}`, 'error');
    } finally {
        loadBtn.disabled = false;
        loadBtn.textContent = 'Load';
    }
}

function populateLanguageGrid() {
    languageGrid.innerHTML = '';
    
    // Build a map of language statuses
    const statusMap = {};
    translateState.languageStatuses.forEach(ls => {
        statusMap[ls.language.code] = ls;
    });
    
    // Get languages (either from statuses or base languages)
    const languages = translateState.languageStatuses.length > 0 
        ? translateState.languageStatuses.map(ls => ({
            ...ls.language,
            status: ls.status,
            cached_segments: ls.cached_segments,
            total_segments: ls.total_segments
        }))
        : translateState.languages;
    
    languages.forEach(lang => {
        // Skip source language
        if (lang.code === translateState.sourceLanguage) return;
        
        const card = document.createElement('div');
        card.className = 'language-card';
        card.dataset.code = lang.code;
        
        const status = lang.status || 'will_translate';
        const statusClass = status === 'cached' ? 'cached' : 
                           status === 'unavailable' ? 'unavailable' : 'will-translate';
        const statusText = status === 'cached' ? 'Cached' :
                          status === 'unavailable' ? 'Unavailable' : 'Will translate';
        
        card.innerHTML = `
            <div class="language-flag">${lang.flag_emoji || '🌐'}</div>
            <div class="language-details">
                <span class="language-name">${escapeHtml(lang.name)}</span>
                <span class="language-native">${escapeHtml(lang.native_name || lang.name)}</span>
            </div>
            <div class="language-status ${statusClass}">${statusText}</div>
            <div class="language-check">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            </div>
        `;
        
        if (status !== 'unavailable') {
            card.addEventListener('click', () => toggleLanguageSelection(lang.code, card));
        } else {
            card.classList.add('disabled');
        }
        
        languageGrid.appendChild(card);
    });
    
    updateSelectedCount();
}

function toggleLanguageSelection(code, card) {
    if (translateState.selectedLanguages.has(code)) {
        translateState.selectedLanguages.delete(code);
        card.classList.remove('selected');
    } else {
        translateState.selectedLanguages.add(code);
        card.classList.add('selected');
    }
    
    updateSelectedCount();
}

function updateSelectedCount() {
    const count = translateState.selectedLanguages.size;
    selectedCount.textContent = `${count} language${count !== 1 ? 's' : ''} selected`;
    translateBtn.disabled = count === 0;
}

async function startTranslation() {
    if (translateState.selectedLanguages.size === 0) {
        updateStatus('Please select at least one language', 'warning');
        return;
    }
    
    const filename = translateState.selectedTranscription;
    const targetLanguages = Array.from(translateState.selectedLanguages);
    const provider = document.querySelector('input[name="provider"]:checked')?.value || 'auto';
    
    // Show progress
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';
    translateBtn.disabled = true;
    progressBar.style.width = '0%';
    progressText.textContent = 'Starting translation...';
    progressDetails.innerHTML = '';
    
    try {
        // Make translation request
        const response = await fetch('/api/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: filename,
                target_languages: targetLanguages,
                provider: provider
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Translation failed');
        }
        
        const data = await response.json();
        
        // Store results
        translateState.translationResults = data.translations || {};
        
        // Update progress
        progressBar.style.width = '100%';
        progressText.textContent = 'Translation complete!';
        
        // Show results
        displayTranslationResults();
        
        updateStatus('Translation complete!', 'success');
        
    } catch (error) {
        console.error('Translation error:', error);
        progressText.textContent = `Error: ${error.message}`;
        updateStatus(`Translation failed: ${error.message}`, 'error');
    } finally {
        translateBtn.disabled = false;
    }
}

function displayTranslationResults() {
    resultsSection.style.display = 'block';
    
    // Build tabs
    resultsTabs.innerHTML = '';
    const languages = Object.keys(translateState.translationResults);
    
    languages.forEach((langCode, index) => {
        const result = translateState.translationResults[langCode];
        const langInfo = translateState.languages.find(l => l.code === langCode) || { name: langCode };
        
        const tab = document.createElement('button');
        tab.className = `result-tab ${index === 0 ? 'active' : ''}`;
        tab.dataset.lang = langCode;
        tab.innerHTML = `
            ${langInfo.flag_emoji || '🌐'} ${langInfo.name || langCode}
            ${result.error ? '<span class="tab-error">⚠</span>' : ''}
        `;
        tab.addEventListener('click', () => switchResultTab(langCode));
        resultsTabs.appendChild(tab);
    });
    
    // Show first result
    if (languages.length > 0) {
        translateState.currentTab = languages[0];
        displayResultContent(languages[0]);
    }
}

function switchResultTab(langCode) {
    // Update tab active state
    document.querySelectorAll('.result-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.lang === langCode);
    });
    
    translateState.currentTab = langCode;
    displayResultContent(langCode);
}

function displayResultContent(langCode) {
    const result = translateState.translationResults[langCode];
    
    if (result.error) {
        resultsContent.innerHTML = `
            <div class="result-error">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <h3>Translation Failed</h3>
                <p>${escapeHtml(result.error)}</p>
            </div>
        `;
        return;
    }
    
    const langInfo = translateState.languages.find(l => l.code === langCode) || { name: langCode };
    
    // Count scripture segments (preserved) and segments with embedded quotes
    const scriptureCount = result.segments ? result.segments.filter(s => s.is_scripture).length : 0;
    const embeddedQuoteCount = result.segments ? result.segments.filter(s => s.has_embedded_quote).length : 0;
    const totalPreservedCount = scriptureCount + embeddedQuoteCount;
    const kathaCount = result.segments ? result.segments.filter(s => !s.is_scripture && !s.has_embedded_quote).length : 0;
    
    resultsContent.innerHTML = `
        <div class="result-header">
            <h3>${langInfo.flag_emoji || '🌐'} ${langInfo.name || langCode}</h3>
            <div class="result-meta">
                <span class="meta-item">
                    <strong>Provider:</strong> ${result.provider || 'auto'}
                </span>
                <span class="meta-item">
                    <strong>Cached:</strong> ${result.cached_count || 0}
                </span>
                <span class="meta-item">
                    <strong>Translated:</strong> ${result.translated_count || 0}
                </span>
                ${scriptureCount > 0 ? `
                    <span class="meta-item scripture-preserved">
                        <strong>Scripture (Preserved):</strong> ${scriptureCount}
                    </span>
                ` : ''}
                ${embeddedQuoteCount > 0 ? `
                    <span class="meta-item embedded-quote-count">
                        <strong>Embedded Quotes:</strong> ${embeddedQuoteCount}
                    </span>
                ` : ''}
            </div>
            ${totalPreservedCount > 0 ? `
                <div class="scripture-notice">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    </svg>
                    <span>Gurbani/Shabad text is sacred and has been <strong>preserved unchanged</strong>. 
                    This includes ${scriptureCount > 0 ? `${scriptureCount} scripture segment${scriptureCount !== 1 ? 's' : ''}` : ''}${scriptureCount > 0 && embeddedQuoteCount > 0 ? ' and ' : ''}${embeddedQuoteCount > 0 ? `${embeddedQuoteCount} quoted line${embeddedQuoteCount !== 1 ? 's' : ''} within katha` : ''}.
                    Only the meaning/interpretation is provided in the target language.</span>
                </div>
            ` : ''}
        </div>
        <div class="result-text" id="resultText">
            ${escapeHtml(result.full_translation || '').replace(/\n/g, '<br>')}
        </div>
        ${result.segments && result.segments.length > 0 ? `
            <details class="segments-details">
                <summary>View Segments (${result.segments.length})</summary>
                <div class="segments-list">
                    ${result.segments.map((seg, i) => renderSegmentItem(seg, i)).join('')}
                </div>
            </details>
        ` : ''}
    `;
}

/**
 * Render a single segment item with proper handling for scripture vs katha
 * CRITICAL: 
 * - Scripture segments show preserved original Gurmukhi, NOT translated text
 * - Katha segments with embedded quotes preserve the quoted Gurbani unchanged
 */
function renderSegmentItem(seg, index) {
    if (seg.is_scripture) {
        // Scripture segment: Show preserved original Gurmukhi + meaning (not replacement)
        return `
            <div class="segment-item scripture-segment">
                <div class="segment-header">
                    <span class="segment-time">${formatTime(seg.start)} - ${formatTime(seg.end)}</span>
                    <span class="segment-badge scripture-badge">ੴ Gurbani (Preserved)</span>
                    ${seg.is_cached ? '<span class="segment-badge cached">Meaning Cached</span>' : ''}
                </div>
                <div class="scripture-preserved-box">
                    <div class="scripture-label">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                        </svg>
                        Original Gurmukhi (Sacred, Unchanged)
                    </div>
                    <div class="segment-gurmukhi-preserved">${escapeHtml(seg.preserved_original || seg.source_text)}</div>
                    ${seg.transliteration ? `
                        <div class="segment-transliteration">
                            <span class="translit-label">Transliteration:</span>
                            ${escapeHtml(seg.transliteration)}
                        </div>
                    ` : ''}
                </div>
                <div class="meaning-box">
                    <div class="meaning-label">Meaning / Interpretation:</div>
                    <div class="segment-meaning">${escapeHtml(seg.translated_text)}</div>
                </div>
            </div>
        `;
    } else if (seg.has_embedded_quote && seg.embedded_quotes && seg.embedded_quotes.length > 0) {
        // Katha segment with embedded Gurbani quote(s) - preserve the quoted scripture!
        return `
            <div class="segment-item katha-with-quote-segment">
                <div class="segment-header">
                    <span class="segment-time">${formatTime(seg.start)} - ${formatTime(seg.end)}</span>
                    <span class="segment-badge katha-quote-badge">Katha with Scripture Quote</span>
                </div>
                
                <!-- Embedded Gurbani Quote(s) - NEVER TRANSLATED -->
                ${seg.embedded_quotes.map((quote, qi) => `
                    <div class="embedded-quote-box">
                        <div class="embedded-quote-label">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                            </svg>
                            Quoted Gurbani (Sacred, Unchanged)
                            ${quote.ang ? `<span class="quote-ref">Ang ${quote.ang}</span>` : ''}
                        </div>
                        <div class="embedded-quote-gurmukhi">${escapeHtml(quote.canonical_text)}</div>
                        ${quote.transliteration ? `
                            <div class="embedded-quote-translit">
                                <span class="translit-label">Transliteration:</span>
                                ${escapeHtml(quote.transliteration)}
                            </div>
                        ` : ''}
                        ${quote.meaning ? `
                            <div class="embedded-quote-meaning">
                                <span class="meaning-label-inline">Meaning:</span>
                                ${escapeHtml(quote.meaning)}
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
                
                <!-- Katha/Explanation (Translated) -->
                <div class="katha-explanation-box">
                    <div class="katha-label">Explanation (Translated):</div>
                    <div class="segment-translation">${escapeHtml(seg.translated_text)}</div>
                </div>
            </div>
        `;
    } else {
        // Pure katha segment (no embedded quotes): Normal translation display
        return `
            <div class="segment-item katha-segment">
                <div class="segment-header">
                    <span class="segment-time">${formatTime(seg.start)} - ${formatTime(seg.end)}</span>
                    <span class="segment-badge katha-badge">Katha (Translated)</span>
                </div>
                <div class="segment-source">
                    <span class="source-label">Original:</span>
                    ${escapeHtml(seg.source_text)}
                </div>
                <div class="segment-translation">
                    <span class="translation-label">Translation:</span>
                    ${escapeHtml(seg.translated_text)}
                </div>
            </div>
        `;
    }
}
}

function copyCurrentTranslation() {
    const langCode = translateState.currentTab;
    if (!langCode) return;
    
    const result = translateState.translationResults[langCode];
    if (!result || result.error) return;
    
    const text = result.full_translation || '';
    
    navigator.clipboard.writeText(text).then(() => {
        const copyBtn = document.getElementById('copyBtn');
        const originalHtml = copyBtn.innerHTML;
        copyBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Copied!
        `;
        copyBtn.style.background = 'var(--color-success)';
        copyBtn.style.color = 'white';
        
        setTimeout(() => {
            copyBtn.innerHTML = originalHtml;
            copyBtn.style.background = '';
            copyBtn.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Copy failed:', err);
        updateStatus('Failed to copy to clipboard', 'error');
    });
}

function downloadAllTranslations() {
    const results = translateState.translationResults;
    if (Object.keys(results).length === 0) return;
    
    // Create combined JSON
    const downloadData = {
        source_filename: translateState.selectedTranscription,
        source_language: translateState.sourceLanguage,
        translations: results,
        created_at: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(downloadData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const filename = translateState.selectedTranscription.replace(/\.[^/.]+$/, '') + '_translations.json';
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    updateStatus('Translations downloaded', 'success');
}

function toggleProviderSettings() {
    const panel = document.getElementById('providerPanel');
    const toggleBtn = document.getElementById('toggleProviderBtn');
    
    const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
    panel.style.display = isExpanded ? 'none' : 'block';
    toggleBtn.setAttribute('aria-expanded', !isExpanded);
    
    const toggleText = toggleBtn.querySelector('.toggle-text');
    if (toggleText) {
        toggleText.textContent = isExpanded ? 'Show Settings' : 'Hide Settings';
    }
}

function updateStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    
    // Auto-hide success/info messages
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            statusMessage.textContent = '';
            statusMessage.className = 'status-message';
        }, 5000);
    }
}

