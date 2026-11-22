/**
 * AI Overview — Modern Frontend Application Logic
 * Pure Real-Data Driven, Heroicons, Custom Language Picker & Responsive Engine
 */

document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------
    // DOM Element Selectors
    // -------------------------------------------------------------
    const $ = (id) => document.getElementById(id);

    // Inputs & Buttons
    const topSearchInput = $('topSearchInput');
    const topSendBtn = $('topSendBtn');
    const factInput = $('factInput');
    const mobileCheckBtn = $('mobileCheckBtn');
    const charCount = $('charCount');
    const presetPills = document.querySelectorAll('.preset-pill, .mini-chip');

    // Language Dropdown Components
    const customLangDropdown = $('customLangDropdown');
    const langTriggerBtn = $('langTriggerBtn');
    const langMenuDropdown = $('langMenuDropdown');
    const currentFlag = $('currentFlag');
    const currentLangText = $('currentLangText');
    const langMenuItems = document.querySelectorAll('.lang-menu-item');
    const mobileLangTrigger = $('mobileLangTrigger');
    const mobileFlag = $('mobileFlag');
    const mobileLangText = $('mobileLangText');

    let currentSelectedLang = 'uz';

    // Desktop Welcome & Results Containers
    const desktopWelcomeCard = $('desktopWelcomeCard');
    const resultsWrapper = $('resultsWrapper');

    // Overview & Content
    const overviewCard = $('overviewCard');
    const ovTitle = $('ovTitle');
    const ovIntro = $('ovIntro');
    const ovBullets = $('ovBullets');
    const ovMessage = $('ovMessage');
    const overviewStatusBadge = $('overviewStatusBadge');
    const btnExpandOverview = $('btnExpandOverview');

    // Sources & Related
    const sourcesCard = $('sourcesCard');
    const displaySourcesList = $('displaySourcesList');
    const sourcesCountBadge = $('sourcesCountBadge');
    const btnToggleAllSources = $('btnToggleAllSources');
    const relatedArticlesList = $('relatedArticlesList');
    const didYouKnowText = $('didYouKnowText');

    // Loading & Error
    const loadingSection = $('loadingSection');
    const pipelineStatusText = $('pipelineStatusText');
    const pDots = [$('dot1'), $('dot2'), $('dot3')];
    const errorBanner = $('errorBanner');
    const errorMessage = $('errorMessage');
    const dismissErrorBtn = $('dismissErrorBtn');

    // Navigation & Views
    const navItems = document.querySelectorAll('.nav-item');
    const bnavItems = document.querySelectorAll('.bnav-item');
    const viewPages = document.querySelectorAll('.view-page');
    const historyList = $('historyList');
    const btnClearHistory = $('btnClearHistory');
    const brandLogoHome = $('brandLogoHome');

    // Theme Switchers
    const headerThemeToggle = $('headerThemeToggle');
    const mobileThemeToggle = $('mobileThemeToggle');
    const btnThemeDark = $('btnThemeDark');
    const btnThemeLight = $('btnThemeLight');

    let loadingInterval = null;
    const STORAGE_KEY_HISTORY = 'ai_overview_history_v2';
    const STORAGE_KEY_THEME = 'ai_overview_theme_v2';

    // -------------------------------------------------------------
    // Theme Setup & Controller
    // -------------------------------------------------------------
    const savedTheme = localStorage.getItem(STORAGE_KEY_THEME) || 'dark';
    setTheme(savedTheme);

    function setTheme(theme) {
        if (theme === 'light') {
            document.body.classList.remove('theme-dark');
            document.body.classList.add('theme-light');
            if (btnThemeLight) btnThemeLight.classList.add('active');
            if (btnThemeDark) btnThemeDark.classList.remove('active');
        } else {
            document.body.classList.remove('theme-light');
            document.body.classList.add('theme-dark');
            if (btnThemeDark) btnThemeDark.classList.add('active');
            if (btnThemeLight) btnThemeLight.classList.remove('active');
        }
        localStorage.setItem(STORAGE_KEY_THEME, theme);
    }

    function toggleTheme() {
        const isLight = document.body.classList.contains('theme-light');
        setTheme(isLight ? 'dark' : 'light');
    }

    if (headerThemeToggle) headerThemeToggle.addEventListener('click', toggleTheme);
    if (mobileThemeToggle) mobileThemeToggle.addEventListener('click', toggleTheme);
    if (btnThemeDark) btnThemeDark.addEventListener('click', () => setTheme('dark'));
    if (btnThemeLight) btnThemeLight.addEventListener('click', () => setTheme('light'));

    // -------------------------------------------------------------
    // Custom Flag + Language Dropdown Controller
    // -------------------------------------------------------------
    if (langTriggerBtn && langMenuDropdown) {
        langTriggerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isClosed = langMenuDropdown.classList.contains('hidden');
            langMenuDropdown.classList.toggle('hidden', !isClosed);
            if (customLangDropdown) customLangDropdown.classList.toggle('open', isClosed);
        });
    }

    if (mobileLangTrigger && langMenuDropdown) {
        mobileLangTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isClosed = langMenuDropdown.classList.contains('hidden');
            langMenuDropdown.classList.toggle('hidden', !isClosed);
            if (customLangDropdown) customLangDropdown.classList.toggle('open', isClosed);
        });
    }

    langMenuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const lang = item.getAttribute('data-lang');
            const flag = item.getAttribute('data-flag');
            const name = item.getAttribute('data-name');

            currentSelectedLang = lang;

            // Update Desktop dropdown display
            if (currentFlag) currentFlag.textContent = flag;
            if (currentLangText) currentLangText.textContent = name;

            // Update Mobile dropdown display
            if (mobileFlag) mobileFlag.textContent = flag;
            if (mobileLangText) mobileLangText.textContent = name;

            // Update active state in menu
            langMenuItems.forEach(mi => mi.classList.toggle('active', mi === item));

            // Close dropdown
            if (langMenuDropdown) langMenuDropdown.classList.add('hidden');
            if (customLangDropdown) customLangDropdown.classList.remove('open');
        });
    });

    // Close language dropdown when clicking outside
    document.addEventListener('click', () => {
        if (langMenuDropdown) langMenuDropdown.classList.add('hidden');
        if (customLangDropdown) customLangDropdown.classList.remove('open');
    });

    // -------------------------------------------------------------
    // Input Handling & Sync
    // -------------------------------------------------------------
    if (factInput) {
        factInput.addEventListener('input', () => {
            if (charCount) charCount.textContent = factInput.value.length;
            if (topSearchInput && document.activeElement === factInput) {
                topSearchInput.value = factInput.value;
            }
        });

        factInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                submitQuery();
            }
        });
    }

    if (topSearchInput) {
        topSearchInput.addEventListener('input', () => {
            if (factInput && document.activeElement === topSearchInput) {
                factInput.value = topSearchInput.value;
                if (charCount) charCount.textContent = topSearchInput.value.length;
            }
        });

        topSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitQuery();
            }
        });
    }

    // Preset pills (Sinov namunalari)
    presetPills.forEach(pill => {
        pill.addEventListener('click', () => {
            const text = pill.getAttribute('data-text');
            if (!text) return;
            if (factInput) {
                factInput.value = text;
                if (charCount) charCount.textContent = text.length;
            }
            if (topSearchInput) topSearchInput.value = text;
            submitQuery();
        });
    });

    // Submit triggers
    if (topSendBtn) topSendBtn.addEventListener('click', submitQuery);
    if (mobileCheckBtn) mobileCheckBtn.addEventListener('click', submitQuery);

    // Error dismiss
    if (dismissErrorBtn) {
        dismissErrorBtn.addEventListener('click', () => {
            if (errorBanner) errorBanner.classList.add('hidden');
        });
    }

    // Logo click returns to clean home
    if (brandLogoHome) {
        brandLogoHome.addEventListener('click', () => {
            switchView('home');
            if (topSearchInput) topSearchInput.value = '';
            if (factInput) factInput.value = '';
            if (charCount) charCount.textContent = '0';
            if (desktopWelcomeCard) desktopWelcomeCard.classList.remove('hidden');
            if (resultsWrapper) resultsWrapper.classList.add('hidden');
            hideError();
        });
    }

    // -------------------------------------------------------------
    // Main Query Execution (Real Data API Call)
    // -------------------------------------------------------------
    async function submitQuery() {
        const text = (topSearchInput && topSearchInput.value.trim().length > 0 
            ? topSearchInput.value.trim() 
            : (factInput ? factInput.value.trim() : '')
        );

        if (text.length < 3) {
            showError("Iltimos, kamida 3 belgidan iborat savol yoki mavzu kiriting.");
            return;
        }

        hideError();
        switchView('home');

        // Hide Welcome Card and show Loading Skeleton
        if (desktopWelcomeCard) desktopWelcomeCard.classList.add('hidden');
        if (resultsWrapper) resultsWrapper.classList.add('hidden');
        startLoading();

        try {
            const response = await fetch('/api/overview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, language: currentSelectedLang })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.detail || data.error || "Javob olishda xatolik yuz berdi.");
            }

            // Render REAL DATA onto the cards
            renderRealOverviewResult(data, text);
            saveSearchHistory(text);

            // Reveal Results Container
            if (resultsWrapper) resultsWrapper.classList.remove('hidden');

        } catch (err) {
            showError(err.message || "Texnik xatolik yuz berdi. Iltimos qayta urinib ko'ring.");
            // Restore welcome card if nothing else to show
            if (desktopWelcomeCard) desktopWelcomeCard.classList.remove('hidden');
        } finally {
            stopLoading();
        }
    }

    // -------------------------------------------------------------
    // Render Real Data
    // -------------------------------------------------------------
    function renderRealOverviewResult(data, queryText) {
        const sources = data.sources || [];
        const intro = data.intro || [];
        const bullets = data.bullets || [];

        // 1. Article Title: query or headline
        if (ovTitle) {
            ovTitle.textContent = queryText;
        }

        // 2. Status Badge
        if (overviewStatusBadge) {
            overviewStatusBadge.removeAttribute('style');
            if (data.generated_by === 'gemini') {
                overviewStatusBadge.className = 'overview-meta-pill badge-ai';
                overviewStatusBadge.innerHTML = `<span class="status-icon">⚡</span><span class="status-text">AI tomonidan yaratilgan</span>`;
            } else {
                overviewStatusBadge.className = 'overview-meta-pill badge-sources';
                overviewStatusBadge.innerHTML = `<span class="status-icon">✓</span><span class="status-text">Manbalar asosida tayyorlandi</span>`;
            }
        }

        // 3. Intro text with citation tags
        if (ovIntro) {
            ovIntro.innerHTML = '';
            if (intro.length === 0 && bullets.length === 0) {
                ovIntro.textContent = data.message || "Ushbu so'rov bo'yicha manbalardan ma'lumot olindi.";
            } else {
                intro.forEach(seg => {
                    ovIntro.appendChild(document.createTextNode(seg.text + ' '));
                    // Real Citation tags
                    if (seg.source_ids && seg.source_ids.length > 0) {
                        seg.source_ids.forEach(id => {
                            const src = sources[id - 1];
                            if (src) {
                                const citeTag = document.createElement('a');
                                citeTag.className = 'cite-tag';
                                citeTag.href = safeUrl(src.source_url);
                                citeTag.target = '_blank';
                                citeTag.rel = 'noopener noreferrer';
                                citeTag.textContent = domainLabel(src.source_domain);
                                citeTag.title = src.source_title || src.source_domain;
                                ovIntro.appendChild(citeTag);
                            }
                        });
                        ovIntro.appendChild(document.createTextNode(' '));
                    }
                });
            }
        }

        // 4. Bullets (if any)
        if (ovBullets) {
            ovBullets.innerHTML = '';
            if (bullets.length > 0) {
                ovBullets.classList.remove('hidden');
                bullets.forEach(b => {
                    const li = document.createElement('li');
                    const strong = document.createElement('strong');
                    strong.textContent = b.label ? `${b.label}: ` : '';
                    li.appendChild(strong);
                    li.appendChild(document.createTextNode(b.text));
                    ovBullets.appendChild(li);
                });
            } else {
                ovBullets.classList.add('hidden');
            }
        }

        // 5. Render Real Sources
        renderRealSources(sources);

        // 6. Update Real Related Articles & Did You Know from search results
        updateRealRelatedArticles(queryText, sources);
        updateRealDidYouKnow(queryText, sources);

        // Smooth scroll to top of overview
        if (overviewCard) {
            overviewCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function renderRealSources(sources) {
        if (!displaySourcesList) return;
        displaySourcesList.innerHTML = '';

        if (sourcesCountBadge) {
            sourcesCountBadge.textContent = `${sources.length} ta manba`;
        }

        if (sources.length === 0) {
            displaySourcesList.innerHTML = `<p class="empty-history-placeholder" style="padding: 1.5rem 0;">ℹ️ Ushbu mavzu yoki da'vo bo'yicha internetda tasdiqlovchi rasmiy manbalar topilmadi.</p>`;
            return;
        }

        sources.forEach((src, idx) => {
            const item = document.createElement('a');
            item.className = 'source-card-item';
            item.href = safeUrl(src.source_url);
            item.target = '_blank';
            item.rel = 'noopener noreferrer';

            // Credibility label & style
            const r = src.source_reliability || 0.5;
            let credClass = 'cred-medium';
            let credText = "O'rtacha (Medium)";
            if (r >= 0.75) {
                credClass = 'cred-high';
                credText = 'Yuqori (High)';
            } else if (r < 0.45) {
                credClass = 'cred-low';
                credText = 'Past (Low)';
            }

            const dateStr = src.source_date ? src.source_date : 'Internet manbasi';

            item.innerHTML = `
                <div class="source-card-top">
                    <div class="source-badge-wrap">
                        <span class="source-index-num">[${idx + 1}]</span>
                        <span class="source-domain-name">${escapeHtml(src.source_domain || 'manba')}</span>
                    </div>
                    <span class="credibility-pill ${credClass}">${credText}</span>
                    <span class="source-arrow-icon">›</span>
                </div>
                <div class="source-card-title">${escapeHtml(src.source_title || src.source_url)}</div>
                <p class="source-card-excerpt">${escapeHtml(dateStr)} • ${escapeHtml(src.source_excerpt || '')}</p>
            `;

            displaySourcesList.appendChild(item);
        });
    }

    function updateRealRelatedArticles(query, sources) {
        if (!relatedArticlesList) return;
        relatedArticlesList.innerHTML = '';

        if (sources.length === 0) {
            relatedArticlesList.innerHTML = `<p class="empty-history-placeholder" style="padding: 0.5rem 0;">Tegishli maqolalar topilmadi.</p>`;
            return;
        }

        // Pick distinct related sources
        const related = sources.slice(1, 4);
        if (related.length === 0 && sources.length > 0) {
            related.push(sources[0]);
        }

        related.forEach((s, i) => {
            const glowStyles = ['thumb-glow-blue', 'thumb-glow-purple', 'thumb-glow-cyan'];
            const glow = glowStyles[i % glowStyles.length];
            const row = document.createElement('a');
            row.className = 'related-article-row';
            row.href = safeUrl(s.source_url);
            row.target = '_blank';
            row.rel = 'noopener noreferrer';
            row.innerHTML = `
                <div class="article-thumb ${glow}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect width="18" height="18" x="3" y="3" rx="2"/>
                        <path d="M7 7h10M7 12h10M7 17h6"/>
                    </svg>
                </div>
                <div class="article-text-col">
                    <span class="article-title">${escapeHtml(s.source_title || query)}</span>
                    <span class="article-meta">${escapeHtml(s.source_domain)} • Manba</span>
                </div>
                <span class="article-chevron">›</span>
            `;
            relatedArticlesList.appendChild(row);
        });
    }

    function updateRealDidYouKnow(query, sources) {
        if (!didYouKnowText) return;
        if (sources.length > 0 && sources[0].source_excerpt) {
            const snippet = sources[0].source_excerpt.trim();
            didYouKnowText.textContent = snippet.length > 150 ? snippet.slice(0, 150) + '...' : snippet;
        } else {
            didYouKnowText.textContent = `"${query}" mavzusi bo'yicha ma'lumotlar internet va Vikipediya qidiruvi orqali tahlil qilindi.`;
        }
    }

    // Mobile Overview Expand/Collapse
    if (btnExpandOverview && overviewCard) {
        btnExpandOverview.addEventListener('click', () => {
            overviewCard.classList.toggle('collapsed');
            const isCollapsed = overviewCard.classList.contains('collapsed');
            btnExpandOverview.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
        });
    }

    // -------------------------------------------------------------
    // Loading Pipeline Controller
    // -------------------------------------------------------------
    function startLoading() {
        if (loadingSection) loadingSection.classList.remove('hidden');
        if (topSendBtn) topSendBtn.disabled = true;
        if (mobileCheckBtn) mobileCheckBtn.disabled = true;

        const messages = [
            "1. Manbalar qidirilmoqda...",
            "2. Sahifalar o'qilmoqda va solishtirilmoqda...",
            "3. Manbalar asosida AI javob tayyorlanmoqda..."
        ];

        let step = 0;
        pDots.forEach(d => { if (d) d.classList.remove('active'); });
        if (pDots[0]) pDots[0].classList.add('active');

        loadingInterval = setInterval(() => {
            step = (step + 1) % messages.length;
            if (pipelineStatusText) pipelineStatusText.textContent = messages[step];
            pDots.forEach((d, i) => {
                if (d) d.classList.toggle('active', i === step);
            });
        }, 1600);
    }

    function stopLoading() {
        if (loadingInterval) clearInterval(loadingInterval);
        if (loadingSection) loadingSection.classList.add('hidden');
        if (topSendBtn) topSendBtn.disabled = false;
        if (mobileCheckBtn) mobileCheckBtn.disabled = false;
    }

    function showError(msg) {
        if (errorMessage) errorMessage.textContent = msg;
        if (errorBanner) {
            errorBanner.classList.remove('hidden');
            errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    function hideError() {
        if (errorBanner) errorBanner.classList.add('hidden');
    }

    // -------------------------------------------------------------
    // Navigation & Views Switcher
    // -------------------------------------------------------------
    function switchView(viewName) {
        navItems.forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-view') === viewName);
        });

        bnavItems.forEach(bitem => {
            bitem.classList.toggle('active', bitem.getAttribute('data-view') === viewName);
        });

        viewPages.forEach(page => {
            const isMatch = page.id === `${viewName}View`;
            page.classList.toggle('active', isMatch);
        });

        if (viewName === 'history') {
            loadSearchHistory();
        } else if (viewName === 'search') {
            // Focus into top search input
            if (topSearchInput && window.innerWidth >= 768) {
                topSearchInput.focus();
            } else if (factInput) {
                factInput.focus();
            }
        }
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => switchView(item.getAttribute('data-view')));
    });

    bnavItems.forEach(item => {
        item.addEventListener('click', () => switchView(item.getAttribute('data-view')));
    });

    // -------------------------------------------------------------
    // Search History Management
    // -------------------------------------------------------------
    function getSearchHistory() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY_HISTORY)) || [];
        } catch {
            return [];
        }
    }

    function saveSearchHistory(query) {
        if (!query || query.length < 3) return;
        let history = getSearchHistory();
        history = history.filter(q => q.toLowerCase() !== query.toLowerCase());
        history.unshift(query);
        if (history.length > 25) history = history.slice(0, 25);
        localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(history));
    }

    function loadSearchHistory() {
        if (!historyList) return;
        const history = getSearchHistory();
        if (history.length === 0) {
            historyList.innerHTML = `<div class="empty-history-placeholder">Hozircha qidiruvlar tarixi bo'sh.</div>`;
            return;
        }

        historyList.innerHTML = '';
        history.forEach(item => {
            const row = document.createElement('div');
            row.className = 'history-item-row';
            row.innerHTML = `
                <span class="history-item-text">🔍 ${escapeHtml(item)}</span>
                <span class="article-chevron">›</span>
            `;
            row.addEventListener('click', () => {
                if (topSearchInput) topSearchInput.value = item;
                if (factInput) factInput.value = item;
                submitQuery();
            });
            historyList.appendChild(row);
        });
    }

    if (btnClearHistory) {
        btnClearHistory.addEventListener('click', () => {
            localStorage.removeItem(STORAGE_KEY_HISTORY);
            loadSearchHistory();
        });
    }

    // -------------------------------------------------------------
    // Utility Helpers
    // -------------------------------------------------------------
    function safeUrl(url) {
        try {
            const u = new URL(url);
            return (u.protocol === 'http:' || u.protocol === 'https:') ? u.href : '#';
        } catch {
            return '#';
        }
    }

    function domainLabel(domain) {
        if (!domain) return 'Manba';
        const clean = domain.replace(/^www\./, '').split('.')[0];
        return clean.charAt(0).toUpperCase() + clean.slice(1);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
