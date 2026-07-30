/* lissn Lightweight Frontend Interactions & Persistent Media Player */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initAuthSystem();
  initMarkdownEditor();
  initSectionFiltering();
  initCopyButtons();
  initShareButtons();
  initPageShortcuts();
  initRescanButton();
  initMediaPlayer();
  initCoverModal();
  initClientNavigation();
  handleHashNavigation(window.location.href);
});

/**
 * Initialize Light / Dark Mode theme toggle with localStorage persistence.
 */
function initTheme() {
  const toggleBtn = document.getElementById('theme-toggle');
  if (!toggleBtn) return;

  const currentTheme = localStorage.getItem('lissn_theme');
  if (currentTheme) {
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeButtonText(toggleBtn, currentTheme);
  }

  toggleBtn.addEventListener('click', () => {
    const activeTheme = document.documentElement.getAttribute('data-theme') ||
      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    
    const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('lissn_theme', newTheme);
    updateThemeButtonText(toggleBtn, newTheme);
  });
}

function updateThemeButtonText(btn, theme) {
  const isDark = theme === 'dark';
  btn.innerHTML = `<span class="btn-icon">${isDark ? '☀️' : '🌙'}</span><span class="btn-text"> ${isDark ? 'Light' : 'Dark'}</span>`;
  btn.setAttribute('aria-label', `Switch to ${isDark ? 'light' : 'dark'} mode`);
}

let activeSectionFilter = 'all';
let currentSearchQuery = '';

/**
 * Initialize section filtering tabs ('all', 'books', 'podcasts') & real-time search input.
 */
function initSectionFiltering() {
  const tabs = document.querySelectorAll('.toolbar .tab-btn');
  if (!tabs.length) return;

  const params = new URLSearchParams(window.location.search);
  activeSectionFilter = params.get('section') || 'all';
  currentSearchQuery = (params.get('q') || '').trim();

  const searchInput = document.getElementById('library-search-input');
  if (searchInput && currentSearchQuery) {
    searchInput.value = currentSearchQuery;
  }

  initSearchFilter();
  applyCombinedFilters();

  tabs.forEach(tab => {
    tab.addEventListener('click', (e) => {
      activeSectionFilter = e.currentTarget.getAttribute('data-section') || 'all';
      applyCombinedFilters();
      updateFilterUrl();
    });
  });
}

/**
 * Initialize real-time text input search filter (title, author, publisher).
 */
function initSearchFilter() {
  const searchInput = document.getElementById('library-search-input');
  const clearBtn = document.getElementById('search-clear-btn');
  if (!searchInput) return;

  const handleInput = () => {
    currentSearchQuery = searchInput.value.trim();
    if (clearBtn) {
      clearBtn.hidden = !currentSearchQuery;
    }
    applyCombinedFilters();
    updateFilterUrl();
  };

  searchInput.addEventListener('input', handleInput);

  if (clearBtn) {
    clearBtn.hidden = !searchInput.value.trim();
    clearBtn.addEventListener('click', () => {
      searchInput.value = '';
      clearBtn.hidden = true;
      currentSearchQuery = '';
      applyCombinedFilters();
      updateFilterUrl();
      searchInput.focus();
    });
  }
}

function updateFilterUrl() {
  const url = new URL(window.location);
  if (activeSectionFilter === 'all') {
    url.searchParams.delete('section');
  } else {
    url.searchParams.set('section', activeSectionFilter);
  }
  if (!currentSearchQuery) {
    url.searchParams.delete('q');
  } else {
    url.searchParams.set('q', currentSearchQuery);
  }
  window.history.pushState({}, '', url);
}

function applyCombinedFilters() {
  const tabs = document.querySelectorAll('.toolbar .tab-btn');
  tabs.forEach(tab => {
    const sec = tab.getAttribute('data-section');
    if (sec === activeSectionFilter) {
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
    } else {
      tab.classList.remove('active');
      tab.setAttribute('aria-selected', 'false');
    }
  });

  const cards = document.querySelectorAll('.show-card');
  const sectionBooks = document.getElementById('section-books');
  const sectionPodcasts = document.getElementById('section-podcasts');
  const noResultsDiv = document.getElementById('no-search-results');
  const searchQuerySpan = document.getElementById('search-query-text');

  const query = currentSearchQuery.toLowerCase();
  let visibleBooksCount = 0;
  let visiblePodcastsCount = 0;
  let totalVisibleCount = 0;

  cards.forEach(card => {
    const cardSection = card.getAttribute('data-section');
    const title = (card.getAttribute('data-title') || card.querySelector('.show-title-link')?.textContent || '').toLowerCase();
    const author = (card.getAttribute('data-author') || '').toLowerCase();
    const publisher = (card.getAttribute('data-publisher') || '').toLowerCase();

    const matchesSection = (activeSectionFilter === 'all' || cardSection === activeSectionFilter);
    const matchesSearch = !query || title.includes(query) || author.includes(query) || publisher.includes(query);

    if (matchesSection && matchesSearch) {
      card.style.display = 'flex';
      totalVisibleCount++;
      if (cardSection === 'books') visibleBooksCount++;
      if (cardSection === 'podcasts') visiblePodcastsCount++;
    } else {
      card.style.display = 'none';
    }
  });

  if (sectionBooks) {
    const showBooksSection = (activeSectionFilter === 'all' || activeSectionFilter === 'books') && visibleBooksCount > 0;
    sectionBooks.style.display = showBooksSection ? 'block' : 'none';
  }

  if (sectionPodcasts) {
    const showPodcastsSection = (activeSectionFilter === 'all' || activeSectionFilter === 'podcasts') && visiblePodcastsCount > 0;
    sectionPodcasts.style.display = showPodcastsSection ? 'block' : 'none';
  }

  if (noResultsDiv) {
    if (totalVisibleCount === 0 && (cards.length > 0)) {
      noResultsDiv.style.display = 'block';
      if (searchQuerySpan) {
        searchQuerySpan.textContent = currentSearchQuery || activeSectionFilter;
      }
    } else {
      noResultsDiv.style.display = 'none';
    }
  }
}

/**
 * Copy RSS feed URL to clipboard with visual toast confirmation.
 */
function initCopyButtons() {
  document.addEventListener('click', (e) => {
    const copyBtn = e.target.closest('.js-copy-rss');
    if (!copyBtn) return;

    const url = copyBtn.getAttribute('data-rss-url');
    if (!url) return;

    navigator.clipboard.writeText(url).then(() => {
      showToast('📋 RSS feed URL copied to clipboard!');
    }).catch(() => {
      showToast('❌ Failed to copy RSS feed link.');
    });
  });
}

/**
 * Share button using Web Share API or clipboard copy fallback.
 */
function initShareButtons() {
  document.addEventListener('click', (e) => {
    const shareBtn = e.target.closest('.js-share-show');
    if (!shareBtn) return;

    const title = shareBtn.getAttribute('data-title');
    const url = shareBtn.getAttribute('data-url') || window.location.href;

    if (navigator.share) {
      navigator.share({
        title: title,
        url: url
      }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url).then(() => {
        showToast('🔗 Show link copied to clipboard!');
      });
    }
  });
}

/**
 * Create or get the Keyboard Shortcuts Help Modal.
 */
function getOrCreateShortcutsModal() {
  let modal = document.getElementById('shortcuts-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'shortcuts-modal';
    modal.className = 'modal-backdrop shortcuts-modal-backdrop';
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-labelledby', 'shortcuts-modal-title');
    modal.innerHTML = `
      <div class="modal-card shortcuts-modal-card">
        <div class="modal-header shortcuts-modal-header">
          <h2 id="shortcuts-modal-title" class="modal-title">⌨️ Keyboard Shortcuts</h2>
          <button type="button" class="modal-close-btn js-close-shortcuts-modal" aria-label="Close keyboard shortcuts modal">&times;</button>
        </div>
        <div class="modal-body shortcuts-modal-body">
          <div class="shortcuts-group">
            <h3 class="shortcuts-group-title">Show Actions</h3>
            <div class="shortcut-row">
              <span class="shortcut-desc">Share show link</span>
              <span class="shortcut-keys"><kbd>s</kbd></span>
            </div>
            <div class="shortcut-row">
              <span class="shortcut-desc">Copy RSS feed URL</span>
              <span class="shortcut-keys"><kbd>r</kbd></span>
            </div>
            <div class="shortcut-row">
              <span class="shortcut-desc">Edit show details</span>
              <span class="shortcut-keys"><kbd>e</kbd></span>
            </div>
            <div class="shortcut-row">
              <span class="shortcut-desc">Download show archive</span>
              <span class="shortcut-keys"><kbd>d</kbd></span>
            </div>
          </div>

          <div class="shortcuts-group">
            <h3 class="shortcuts-group-title">Media Player</h3>
            <div class="shortcut-row">
              <span class="shortcut-desc">Play / Pause active track</span>
              <span class="shortcut-keys"><kbd>Space</kbd> / <kbd>Enter</kbd></span>
            </div>
            <div class="shortcut-row">
              <span class="shortcut-desc">Seek backward / forward 15s</span>
              <span class="shortcut-keys"><kbd>←</kbd> / <kbd>→</kbd></span>
            </div>
            <div class="shortcut-row">
              <span class="shortcut-desc">Next / Previous track</span>
              <span class="shortcut-keys"><kbd>n</kbd> / <kbd>p</kbd></span>
            </div>
            <div class="shortcut-row">
              <span class="shortcut-desc">Close player / Close modal</span>
              <span class="shortcut-keys"><kbd>Esc</kbd></span>
            </div>
          </div>

          <div class="shortcuts-group">
            <h3 class="shortcuts-group-title">General</h3>
            <div class="shortcut-row">
              <span class="shortcut-desc">Toggle keyboard shortcuts help</span>
              <span class="shortcut-keys"><kbd>?</kbd></span>
            </div>
          </div>
        </div>
        <div class="modal-actions" style="padding: 1rem 1.5rem; border-top: 1px solid var(--border-color);">
          <button type="button" class="btn btn-secondary js-close-shortcuts-modal" style="width: 100%;">Close</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', (e) => {
      if (e.target === modal || e.target.closest('.js-close-shortcuts-modal')) {
        closeShortcutsModal();
      }
    });
  }
  return modal;
}

function openShortcutsModal() {
  const modal = getOrCreateShortcutsModal();
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
}

function closeShortcutsModal() {
  const modal = document.getElementById('shortcuts-modal');
  if (modal) {
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
  }
}

function toggleShortcutsModal() {
  const modal = getOrCreateShortcutsModal();
  if (modal.hidden) {
    openShortcutsModal();
  } else {
    closeShortcutsModal();
  }
}

/**
 * Page-level single character keyboard shortcuts (s, r, e, d, ?).
 * Follows Web Accessibility & UX best practices:
 * - Active only when typing focus is not inside form fields / inputs / editable elements.
 * - Does not override browser system key combinations (Cmd/Ctrl + S/R/E/D).
 */
function initPageShortcuts() {
  document.addEventListener('keydown', (e) => {
    const activeEl = document.activeElement;
    if (activeEl && (['INPUT', 'TEXTAREA', 'SELECT'].includes(activeEl.tagName) || activeEl.isContentEditable)) {
      return;
    }
    if (e.ctrlKey || e.metaKey || e.altKey) {
      return;
    }

    // Toggle shortcuts modal on '?' keypress
    if (e.key === '?') {
      e.preventDefault();
      toggleShortcutsModal();
      return;
    }

    const shortcutsModal = document.getElementById('shortcuts-modal');
    if (e.key === 'Escape' || e.code === 'Escape') {
      if (shortcutsModal && !shortcutsModal.hidden) {
        closeShortcutsModal();
        return;
      }
    }

    if (isAnyModalOpen()) {
      return;
    }

    const key = e.key.toLowerCase();
    if (key === 's') {
      const shareBtn = document.querySelector('.js-share-show');
      if (shareBtn) {
        e.preventDefault();
        shareBtn.click();
      }
    } else if (key === 'r') {
      const copyRssBtn = document.querySelector('.js-copy-rss');
      if (copyRssBtn) {
        e.preventDefault();
        copyRssBtn.click();
      }
    } else if (key === 'e') {
      const editBtn = document.querySelector('.js-edit-show');
      if (editBtn) {
        e.preventDefault();
        editBtn.click();
      }
    } else if (key === 'd') {
      const downloadBtn = document.querySelector('.js-download-show');
      if (downloadBtn) {
        e.preventDefault();
        downloadBtn.click();
      }
    }
  });
}

/**
 * Trigger library rescan via API.
 */
function initRescanButton() {
  const rescanBtn = document.getElementById('rescan-btn');
  if (!rescanBtn) return;

  rescanBtn.addEventListener('click', async () => {
    rescanBtn.disabled = true;
    rescanBtn.textContent = '🔄 Rescanning...';

    try {
      const response = await fetch('/api/scan', { method: 'POST' });
      if (response.ok) {
        showToast('✅ Library rescan complete!');
        setTimeout(() => window.location.reload(), 1000);
      } else {
        showToast('❌ Failed to rescan library.');
      }
    } catch (err) {
      showToast('❌ Error connecting to server.');
    } finally {
      rescanBtn.disabled = false;
      rescanBtn.textContent = '🔄 Rescan Library';
    }
  });
}

/**
 * Display a temporary floating toast message.
 */
function showToast(message) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}

/**
 * Initialize Client-Side PJAX Navigation to preserve media player across page changes.
 * Supports Alt-click on podcast show cards and show links to open show in a new window.
 */
function initClientNavigation() {
  document.addEventListener('click', (e) => {
    // Handle Alt-click (Option key on macOS) on podcast show cards or show elements to open show in new window
    if (e.altKey) {
      const showCard = e.target.closest('.show-card');
      if (showCard && !e.target.closest('.card-actions, .js-copy-rss, a[href^="podcast:"]')) {
        const showLink = showCard.querySelector('a[href^="/show/"]');
        if (showLink) {
          const href = showLink.getAttribute('href');
          if (href) {
            const targetUrl = new URL(href, window.location.origin);
            e.preventDefault();
            window.open(targetUrl.href, '_blank');
            return;
          }
        }
      }
    }

    const anchor = e.target.closest('a');
    if (!anchor) return;

    const href = anchor.getAttribute('href');
    if (!href) return;

    // Skip external links, non-HTTP schemas, RSS, direct audio, cover downloads, or new window links
    if (
      href.startsWith('#') ||
      href.startsWith('javascript:') ||
      href.startsWith('podcast:') ||
      href.startsWith('mailto:') ||
      anchor.getAttribute('target') === '_blank' ||
      anchor.hasAttribute('download') ||
      href.includes('/rss/') ||
      href.includes('/audio/') ||
      href.includes('/download/') ||
      href.includes('/covers/')
    ) {
      return;
    }

    const targetUrl = new URL(href, window.location.origin);
    if (targetUrl.origin !== window.location.origin) return;

    // Open link target in new window when alt-clicked
    if (e.altKey) {
      e.preventDefault();
      window.open(targetUrl.href, '_blank');
      return;
    }

    // Let default browser behavior execute for Cmd / Ctrl / Shift clicks
    if (e.metaKey || e.ctrlKey || e.shiftKey) {
      return;
    }

    // Perform smooth client-side page load
    e.preventDefault();
    navigateTo(targetUrl.href, true);
  });

  // Handle browser Back / Forward buttons
  window.addEventListener('popstate', () => {
    navigateTo(window.location.href, false);
  });
}

/**
 * Fetch destination page HTML dynamically and update DOM without stopping audio.
 */
async function navigateTo(urlStr, isPushState = true) {
  try {
    const response = await fetch(urlStr, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    if (!response.ok) {
      window.location.href = urlStr;
      return;
    }

    const htmlText = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlText, 'text/html');

    const newMain = doc.querySelector('main.main-content');
    const currentMain = document.querySelector('main.main-content');

    if (!newMain || !currentMain) {
      window.location.href = urlStr;
      return;
    }

    // Update document title
    document.title = doc.title || 'lissn';

    // Update body inline styling (for show accent color variables)
    const newBodyStyle = doc.body.getAttribute('style') || '';
    document.body.setAttribute('style', newBodyStyle);

    // Replace main content
    currentMain.innerHTML = newMain.innerHTML;

    // Push browser history
    if (isPushState) {
      window.history.pushState({}, '', urlStr);
    }

    // Announce page title change for screen readers
    const announcer = document.getElementById('aria-announcer');
    if (announcer) {
      announcer.textContent = `Navigated to ${doc.title || 'page'}`;
    }

    // Re-initialize section filter tabs if returning to home
    initSectionFiltering();

    // Re-bind player track list for newly injected page elements
    if (window.syncPlayerWithPage) {
      window.syncPlayerWithPage();
    }

    // Scroll down to and focus target show card if returning to library
    handleHashNavigation(urlStr);
  } catch (err) {
    console.warn('Navigation fetch error, falling back to full page load:', err);
    window.location.href = urlStr;
  }
}

/**
 * Handle scrolling down to and focusing on a relevant show card when returning to library.
 */
function handleHashNavigation(urlStr) {
  try {
    const targetUrl = new URL(urlStr || window.location.href, window.location.origin);
    let targetId = null;

    if (targetUrl.hash) {
      targetId = targetUrl.hash.substring(1);
    }

    if (!targetId) {
      window.scrollTo({ top: 0, behavior: 'instant' });
      return;
    }

    const targetCard = document.getElementById(targetId);
    if (!targetCard) {
      window.scrollTo({ top: 0, behavior: 'instant' });
      return;
    }

    // Ensure section filter displays the card if currently hidden by tab filter
    const cardSection = targetCard.getAttribute('data-section');
    if (cardSection) {
      const activeTab = document.querySelector('.tab-btn.active');
      const activeSection = activeTab ? activeTab.getAttribute('data-section') : 'all';
      if (activeSection !== 'all' && activeSection !== cardSection) {
        applyFilter('all');
      }
    }

    const scrollAndFocus = () => {
      targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      try {
        targetCard.focus({ preventScroll: true });
      } catch (e) {
        targetCard.focus();
      }
      targetCard.classList.add('show-card-highlighted');

      setTimeout(() => {
        targetCard.classList.remove('show-card-highlighted');
      }, 2500);
    };

    setTimeout(scrollAndFocus, 60);

  } catch (err) {
    console.warn('Error handling hash navigation:', err);
    window.scrollTo({ top: 0, behavior: 'instant' });
  }
}

/**
 * Initialize Bottom Media Player with auto-continue playlist support and session persistence.
 */
function initMediaPlayer() {
  const bottomPlayer = document.getElementById('bottom-player');
  const audioElement = document.getElementById('global-audio-element');
  if (!bottomPlayer || !audioElement) return;

  const playBtn = document.getElementById('player-play-btn');
  const prevBtn = document.getElementById('player-prev-btn');
  const nextBtn = document.getElementById('player-next-btn');
  const skipBackBtn = document.getElementById('player-skip-back-btn');
  const skipFwdBtn = document.getElementById('player-skip-fwd-btn');
  const autoContinueBtn = document.getElementById('auto-continue-btn');
  const autoContinueStatus = document.getElementById('auto-continue-status');
  const seekBar = document.getElementById('player-seek-bar');
  const currentTimeEl = document.getElementById('player-current-time');
  const totalTimeEl = document.getElementById('player-total-time');
  const speedSelect = document.getElementById('player-speed-select');
  const muteBtn = document.getElementById('player-mute-btn');
  const volumeSlider = document.getElementById('player-volume-slider');
  const closeBtn = document.getElementById('player-close-btn');
  const trackTitleEl = document.getElementById('player-track-title');
  const showTitleEl = document.getElementById('player-show-title');
  const coverImg = document.getElementById('player-cover');
  const coverPlaceholder = document.getElementById('player-cover-placeholder');

  const sleepTimerBtn = document.getElementById('sleep-timer-btn');
  const sleepTimerBadge = document.getElementById('sleep-timer-badge');
  const sleepTimerSelect = document.getElementById('sleep-timer-select');

  let activePlaylist = [];
  let currentTrackIndex = -1;
  let isAutoContinue = localStorage.getItem('lissn_auto_continue') !== 'false'; // Default to true
  let isRemainingTimeMode = localStorage.getItem('lissn_remaining_time_mode') === 'true';
  let sleepTimerInterval = null;
  let sleepTimerEndTime = null;
  let pendingRestoreTime = null;

  // Toggle duration display between total length and remaining time
  function toggleDurationMode() {
    isRemainingTimeMode = !isRemainingTimeMode;
    localStorage.setItem('lissn_remaining_time_mode', isRemainingTimeMode);
    updateTotalTimeDisplay();

    const announcer = document.getElementById('aria-announcer');
    if (announcer) {
      announcer.textContent = isRemainingTimeMode ? 'Displaying remaining episode time' : 'Displaying total episode duration';
    }
  }

  if (totalTimeEl) {
    totalTimeEl.addEventListener('click', toggleDurationMode);
    totalTimeEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        toggleDurationMode();
      }
    });
  }

  function updateTotalTimeDisplay() {
    if (!totalTimeEl) return;
    const dur = audioElement.duration;
    const cur = audioElement.currentTime || 0;

    if (isNaN(dur) || dur <= 0) {
      totalTimeEl.textContent = isRemainingTimeMode ? '-0:00' : '0:00';
      return;
    }

    if (isRemainingTimeMode) {
      const remaining = Math.max(0, dur - cur);
      totalTimeEl.textContent = '-' + formatTime(remaining);
      totalTimeEl.setAttribute('aria-label', `Remaining time: ${formatTime(remaining)}. Click to toggle total duration`);
      totalTimeEl.setAttribute('title', 'Click to toggle total duration');
    } else {
      totalTimeEl.textContent = formatTime(dur);
      totalTimeEl.setAttribute('aria-label', `Total duration: ${formatTime(dur)}. Click to toggle remaining time`);
      totalTimeEl.setAttribute('title', 'Click to toggle remaining time');
    }
  }

  // Sleep Timer Handler
  if (sleepTimerSelect) {
    sleepTimerSelect.addEventListener('change', () => {
      const value = sleepTimerSelect.value;
      if (value === 'off') {
        cancelSleepTimer(true);
      } else {
        const minutes = parseInt(value, 10);
        if (!isNaN(minutes)) {
          startSleepTimer(minutes);
        }
      }
    });
  }

  function startSleepTimer(minutes) {
    cancelSleepTimer(false);
    sleepTimerEndTime = Date.now() + (minutes * 60 * 1000);

    const labelStr = minutes === 60 ? '1 hour' : `${minutes} minutes`;
    showToast(`🌙 Sleep timer set for ${labelStr}`);
    updateSleepTimerUI(minutes * 60);

    // Restore select to the active timer value so that choosing "Off"
    // later fires a change event (the select was reset to 'off' by
    // cancelSleepTimer above, which would make selecting "Off" a no-op).
    if (sleepTimerSelect) sleepTimerSelect.value = String(minutes);

    sleepTimerInterval = setInterval(tickSleepTimer, 1000);
  }

  function tickSleepTimer() {
    if (!sleepTimerEndTime) return;
    const remainingMs = sleepTimerEndTime - Date.now();
    const remainingSecs = Math.max(0, Math.ceil(remainingMs / 1000));

    if (remainingSecs <= 0) {
      cancelSleepTimer(false);
      audioElement.pause();
      showToast('🌙 Sleep timer finished. Audio playback paused.');
      const announcer = document.getElementById('aria-announcer');
      if (announcer) {
        announcer.textContent = 'Sleep timer finished. Audio playback paused.';
      }
    } else {
      updateSleepTimerUI(remainingSecs);
    }
  }

  function cancelSleepTimer(notify = false) {
    if (sleepTimerInterval) {
      clearInterval(sleepTimerInterval);
      sleepTimerInterval = null;
    }
    sleepTimerEndTime = null;

    if (sleepTimerSelect) sleepTimerSelect.value = 'off';
    if (sleepTimerBtn) sleepTimerBtn.classList.remove('active');
    if (sleepTimerBadge) sleepTimerBadge.textContent = 'OFF';

    if (notify) {
      showToast('🌙 Sleep timer turned off');
    }
  }

  function updateSleepTimerUI(remainingSecs) {
    if (!sleepTimerBtn || !sleepTimerBadge) return;
    sleepTimerBtn.classList.add('active');

    if (remainingSecs >= 3600) {
      const h = Math.floor(remainingSecs / 3600);
      const m = Math.floor((remainingSecs % 3600) / 60);
      sleepTimerBadge.textContent = `${h}h${m > 0 ? m + 'm' : ''}`;
    } else if (remainingSecs >= 60) {
      const m = Math.ceil(remainingSecs / 60);
      sleepTimerBadge.textContent = `${m}m`;
    } else {
      sleepTimerBadge.textContent = `${remainingSecs}s`;
    }
  }

  // Sync initial auto-continue UI state
  updateAutoContinueUI();

  // Restore saved player state from sessionStorage if available
  restoreSavedPlayerState();

  // Helper to check if a playlist track matches the currently loaded audio element src
  function isCurrentlyLoadedTrack(track) {
    if (!track || !track.src) return false;
    const currentSrc = audioElement.getAttribute('src') || audioElement.src;
    if (!currentSrc) return false;
    try {
      const normCurrent = new URL(currentSrc, window.location.origin).href;
      const normTrack = new URL(track.src, window.location.origin).href;
      return normCurrent === normTrack;
    } catch (e) {
      return currentSrc.endsWith(track.src) || track.src.endsWith(currentSrc);
    }
  }

  // Function to scan current DOM for track rows and update playlist reference
  function syncPlayerWithPage() {
    const trackRows = Array.from(document.querySelectorAll('.track-row'));
    if (trackRows.length > 0) {
      activePlaylist = trackRows.map((row, idx) => ({
        index: idx,
        src: row.getAttribute('data-audio-src'),
        trackTitle: row.getAttribute('data-track-title'),
        showTitle: row.getAttribute('data-show-title'),
        coverUrl: row.getAttribute('data-cover-url'),
        element: row
      }));

      // Check if current playing src matches any track on the current page
      const foundIdx = activePlaylist.findIndex(t => isCurrentlyLoadedTrack(t));
      currentTrackIndex = foundIdx;
    } else {
      activePlaylist = [];
      currentTrackIndex = -1;
    }
    highlightActiveTrackRow();
  }

  // Expose sync helper globally for PJAX page transitions
  window.syncPlayerWithPage = syncPlayerWithPage;
  syncPlayerWithPage();

  // Handle click on track rows anywhere in the page (via delegation)
  document.addEventListener('click', (e) => {
    if (e.target.closest('audio') || e.target.closest('a') || e.target.closest('button.btn-secondary') || e.target.closest('.js-copy-rss')) return;

    const trackRow = e.target.closest('.track-row');
    if (trackRow) {
      if (globalAuthState.passwordRequired && !globalAuthState.authenticated) {
        openPasswordModal();
        return;
      }
      const idx = parseInt(trackRow.getAttribute('data-track-index'), 10);
      if (!isNaN(idx) && activePlaylist[idx]) {
        const targetTrack = activePlaylist[idx];
        if (isCurrentlyLoadedTrack(targetTrack)) {
          if (!audioElement.paused) {
            audioElement.pause();
          } else {
            audioElement.play();
          }
        } else {
          playTrack(idx);
        }
      }
    }
  });

  // Support Keyboard Enter key on focused track row
  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
    if (document.activeElement && document.activeElement.classList.contains('track-row')) {
      if (e.key === 'Enter') {
        e.preventDefault();
        const idx = parseInt(document.activeElement.getAttribute('data-track-index'), 10);
        if (!isNaN(idx) && activePlaylist[idx]) {
          const targetTrack = activePlaylist[idx];
          if (isCurrentlyLoadedTrack(targetTrack)) {
            if (!audioElement.paused) {
              audioElement.pause();
            } else {
              audioElement.play();
            }
          } else {
            playTrack(idx);
          }
        }
      }
    }
  });

  function playTrack(index) {
    if (index < 0 || index >= activePlaylist.length) return;

    if (globalAuthState.passwordRequired && !globalAuthState.authenticated) {
      openPasswordModal(() => playTrack(index));
      return;
    }

    pendingRestoreTime = null;
    currentTrackIndex = index;
    const track = activePlaylist[index];

    // Make bottom player visible
    bottomPlayer.classList.add('visible');
    document.body.classList.add('has-active-player');

    audioElement.src = track.src;
    audioElement.playbackRate = parseFloat(speedSelect.value) || 1.0;

    const playPromise = audioElement.play();
    if (playPromise !== undefined) {
      playPromise.then(() => {
        updatePlayButtonUI(true);
        savePlayerState();
      }).catch(err => {
        console.warn('Playback play promise error:', err);
        updatePlayButtonUI(false);
      });
    }

    // Update metadata UI
    if (trackTitleEl) trackTitleEl.textContent = track.trackTitle;
    if (showTitleEl) showTitleEl.textContent = track.showTitle;

    if (track.coverUrl) {
      coverImg.src = track.coverUrl;
      coverImg.style.display = 'block';
      if (coverPlaceholder) coverPlaceholder.style.display = 'none';
    } else {
      coverImg.style.display = 'none';
      if (coverPlaceholder) coverPlaceholder.style.display = 'flex';
    }

    highlightActiveTrackRow();
  }

  const SVG_PLAY = '<svg class="player-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>';
  const SVG_PAUSE = '<svg class="player-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect></svg>';
  const SVG_VOL_HIGH = '<svg class="player-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>';
  const SVG_VOL_MUTE = '<svg class="player-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="1" y1="1" x2="23" y2="23"></line><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon></svg>';
  const SVG_TRACK_PLAY = '<svg class="btn-play-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
  const SVG_TRACK_PAUSE = '<svg class="btn-play-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect></svg>';

  function highlightActiveTrackRow() {
    const trackRows = document.querySelectorAll('.track-row');

    trackRows.forEach((row) => {
      const rowSrc = row.getAttribute('data-audio-src');
      const playBtnEl = row.querySelector('.js-play-track');
      const isCurrent = isCurrentlyLoadedTrack({ src: rowSrc });

      if (isCurrent) {
        row.classList.add('active-track');
        if (playBtnEl) playBtnEl.innerHTML = audioElement.paused ? SVG_TRACK_PLAY : SVG_TRACK_PAUSE;
      } else {
        row.classList.remove('active-track');
        if (playBtnEl) playBtnEl.innerHTML = SVG_TRACK_PLAY;
      }
    });
  }

  function updatePlayButtonUI(isPlaying) {
    if (playBtn) {
      playBtn.innerHTML = isPlaying ? SVG_PAUSE : SVG_PLAY;
      playBtn.setAttribute('aria-label', isPlaying ? 'Pause audio' : 'Play audio');
    }
    highlightActiveTrackRow();
  }

  // Play / Pause toggle button
  if (playBtn) {
    playBtn.addEventListener('click', () => {
      if (!audioElement.src && activePlaylist.length > 0) {
        playTrack(0);
        return;
      }
      if (audioElement.paused) {
        audioElement.play();
      } else {
        audioElement.pause();
      }
    });
  }

  // Prev / Next track navigation
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (audioElement.currentTime > 3) {
        audioElement.currentTime = 0;
      } else if (currentTrackIndex > 0) {
        playTrack(currentTrackIndex - 1);
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (currentTrackIndex < activePlaylist.length - 1) {
        playTrack(currentTrackIndex + 1);
      }
    });
  }

  // Skip -10s / +10s
  if (skipBackBtn) {
    skipBackBtn.addEventListener('click', () => {
      audioElement.currentTime = Math.max(0, audioElement.currentTime - 10);
    });
  }

  if (skipFwdBtn) {
    skipFwdBtn.addEventListener('click', () => {
      audioElement.currentTime = Math.min(audioElement.duration || 0, audioElement.currentTime + 10);
    });
  }

  // Auto-Continue toggle handler
  if (autoContinueBtn) {
    autoContinueBtn.addEventListener('click', () => {
      isAutoContinue = !isAutoContinue;
      localStorage.setItem('lissn_auto_continue', isAutoContinue);
      updateAutoContinueUI();
      showToast(isAutoContinue ? '🔁 Auto-continue enabled' : '⏸ Auto-continue disabled');
    });
  }

  function updateAutoContinueUI() {
    if (!autoContinueBtn) return;
    if (isAutoContinue) {
      autoContinueBtn.classList.add('active');
      if (autoContinueStatus) autoContinueStatus.textContent = 'ON';
    } else {
      autoContinueBtn.classList.remove('active');
      if (autoContinueStatus) autoContinueStatus.textContent = 'OFF';
    }
  }

  // Handle End of Track (Auto-Continue to next episode/chapter)
  audioElement.addEventListener('ended', () => {
    updatePlayButtonUI(false);
    if (isAutoContinue && currentTrackIndex >= 0 && currentTrackIndex < activePlaylist.length - 1) {
      showToast(`▶ Auto-continuing: ${activePlaylist[currentTrackIndex + 1].trackTitle}`);
      playTrack(currentTrackIndex + 1);
    } else if (currentTrackIndex >= activePlaylist.length - 1 && activePlaylist.length > 0) {
      showToast('🎉 End of show playlist');
    }
  });

  // Audio status events
  audioElement.addEventListener('play', () => {
    updatePlayButtonUI(true);
    savePlayerState();
  });
  audioElement.addEventListener('pause', () => {
    updatePlayButtonUI(false);
    savePlayerState();
  });

  // Time & Seek Bar updates
  audioElement.addEventListener('timeupdate', () => {
    if (!isNaN(audioElement.duration) && audioElement.duration > 0) {
      const pct = (audioElement.currentTime / audioElement.duration) * 100;
      seekBar.value = pct;
      currentTimeEl.textContent = formatTime(audioElement.currentTime);
      updateTotalTimeDisplay();
      savePlayerState();
    }
  });

  seekBar.addEventListener('input', () => {
    if (!isNaN(audioElement.duration) && audioElement.duration > 0) {
      audioElement.currentTime = (seekBar.value / 100) * audioElement.duration;
    }
  });

  // Speed selection
  if (speedSelect) {
    speedSelect.addEventListener('change', () => {
      audioElement.playbackRate = parseFloat(speedSelect.value);
    });
  }

  // Volume & Mute control
  if (volumeSlider) {
    volumeSlider.addEventListener('input', () => {
      audioElement.volume = parseFloat(volumeSlider.value);
      audioElement.muted = audioElement.volume === 0;
      updateMuteBtnUI();
    });
  }

  if (muteBtn) {
    muteBtn.addEventListener('click', () => {
      audioElement.muted = !audioElement.muted;
      updateMuteBtnUI();
    });
  }

  function updateMuteBtnUI() {
    if (!muteBtn) return;
    const isMuted = audioElement.muted || audioElement.volume === 0;
    muteBtn.innerHTML = isMuted ? SVG_VOL_MUTE : SVG_VOL_HIGH;
    muteBtn.setAttribute('aria-label', isMuted ? 'Unmute audio' : 'Mute audio');
  }

  // Helper to safely apply pending seek position when audio metadata is ready
  function applyPendingRestoreTime() {
    if (pendingRestoreTime === null || pendingRestoreTime <= 0) return;
    try {
      if (audioElement.readyState >= 1) {
        audioElement.currentTime = pendingRestoreTime;
        if (currentTimeEl) currentTimeEl.textContent = formatTime(pendingRestoreTime);
        if (!isNaN(audioElement.duration) && audioElement.duration > 0 && seekBar) {
          seekBar.value = (pendingRestoreTime / audioElement.duration) * 100;
        }
        pendingRestoreTime = null;
      }
    } catch (e) {
      console.warn('Failed to apply pending restore time on audio element:', e);
    }
  }

  audioElement.addEventListener('loadedmetadata', () => {
    updateTotalTimeDisplay();
    applyPendingRestoreTime();
  });

  audioElement.addEventListener('canplay', () => {
    applyPendingRestoreTime();
  });

  // Save current player state to sessionStorage
  function savePlayerState() {
    if (!audioElement.src) return;

    let timeToSave = audioElement.currentTime || 0;
    if (pendingRestoreTime !== null && pendingRestoreTime > 0 && timeToSave === 0) {
      timeToSave = pendingRestoreTime;
    }

    const state = {
      src: audioElement.getAttribute('src') || audioElement.src,
      trackTitle: trackTitleEl ? trackTitleEl.textContent : '',
      showTitle: showTitleEl ? showTitleEl.textContent : '',
      coverUrl: (coverImg && coverImg.style.display !== 'none') ? coverImg.src : null,
      currentTime: timeToSave,
      paused: audioElement.paused
    };
    try {
      sessionStorage.setItem('lissn_player_state', JSON.stringify(state));
    } catch (e) {
      // Ignore storage errors
    }
  }

  // Restore saved player state from sessionStorage
  function restoreSavedPlayerState() {
    try {
      const raw = sessionStorage.getItem('lissn_player_state');
      if (!raw) return;
      const state = JSON.parse(raw);
      if (!state || !state.src) return;

      audioElement.setAttribute('src', state.src);
      audioElement.src = state.src;

      if (trackTitleEl && state.trackTitle) trackTitleEl.textContent = state.trackTitle;
      if (showTitleEl && state.showTitle) showTitleEl.textContent = state.showTitle;

      if (state.coverUrl) {
        coverImg.src = state.coverUrl;
        coverImg.style.display = 'block';
        if (coverPlaceholder) coverPlaceholder.style.display = 'none';
      }

      bottomPlayer.classList.add('visible');
      document.body.classList.add('has-active-player');

      const restoreTime = state.currentTime || 0;
      if (restoreTime > 0) {
        pendingRestoreTime = restoreTime;
        if (currentTimeEl) currentTimeEl.textContent = formatTime(restoreTime);
        applyPendingRestoreTime();
      }

      if (!state.paused) {
        if (globalAuthState.passwordRequired && !globalAuthState.authenticated) {
          openPasswordModal(() => {
            const playPromise = audioElement.play();
            if (playPromise !== undefined) {
              playPromise.then(() => {
                updatePlayButtonUI(true);
              }).catch((err) => {
                console.warn('Playback error after auth unlock:', err);
                updatePlayButtonUI(false);
              });
            }
          });
          return;
        }

        const playPromise = audioElement.play();
        if (playPromise !== undefined) {
          playPromise.then(() => {
            updatePlayButtonUI(true);
          }).catch((err) => {
            console.warn('Autoplay on restore blocked by browser policy:', err);
            updatePlayButtonUI(false);
          });
        } else {
          updatePlayButtonUI(false);
        }
      } else {
        updatePlayButtonUI(false);
      }
    } catch (e) {
      console.warn('Error restoring player state:', e);
    }
  }

  /**
   * Terminate audio playback and remove player UI.
   */
  function closePlayer() {
    pendingRestoreTime = null;
    audioElement.pause();
    audioElement.removeAttribute('src');
    audioElement.load();
    currentTrackIndex = -1;

    cancelSleepTimer(false);

    bottomPlayer.classList.remove('visible');
    document.body.classList.remove('has-active-player');

    sessionStorage.removeItem('lissn_player_state');

    if (trackTitleEl) trackTitleEl.textContent = 'Select a track';
    if (showTitleEl) showTitleEl.textContent = 'lissn player';
    if (currentTimeEl) currentTimeEl.textContent = '0:00';
    if (totalTimeEl) totalTimeEl.textContent = isRemainingTimeMode ? '-0:00' : '0:00';
    if (seekBar) seekBar.value = 0;

    highlightActiveTrackRow();
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', closePlayer);
  }

  // Global Keyboard Shortcuts (Left/Right seek, N next, P prev, Esc close)
  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;

    if (e.code === 'ArrowLeft') {
      e.preventDefault();
      skipBackBtn?.click();
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      skipFwdBtn?.click();
    } else if (e.key === 'n' || e.key === 'N') {
      nextBtn?.click();
    } else if (e.key === 'p' || e.key === 'P') {
      prevBtn?.click();
    } else if (e.key === 'Escape' || e.code === 'Escape') {
      if (!isAnyModalOpen() && bottomPlayer.classList.contains('visible')) {
        closePlayer();
      }
    }
  });
}

function formatTime(seconds) {
  if (isNaN(seconds)) return '0:00';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  const formattedSecs = secs < 10 ? `0${secs}` : secs;

  if (hrs > 0) {
    const formattedMins = mins < 10 ? `0${mins}` : mins;
    return `${hrs}:${formattedMins}:${formattedSecs}`;
  }
  return `${mins}:${formattedSecs}`;
}

/* Authentication & Password Protected Actions */
function getInitialAuthState() {
  const el = document.getElementById('lissn-auth-state');
  if (el) {
    try {
      const data = JSON.parse(el.textContent);
      return {
        authenticated: Boolean(data.authenticated),
        passwordRequired: Boolean(data.password_required)
      };
    } catch (e) {}
  }
  return { authenticated: true, passwordRequired: false };
}

let globalAuthState = getInitialAuthState();
let pendingAuthAction = null;

function updateAuthButtonUI() {
  const authBtn = document.getElementById('auth-btn');
  if (!authBtn) return;

  authBtn.hidden = false;
  if (globalAuthState.authenticated) {
    authBtn.innerHTML = '<span class="btn-icon">🚪</span><span class="btn-text"> Log Out</span>';
    authBtn.setAttribute('aria-label', 'Log out of session');
  } else {
    authBtn.innerHTML = '<span class="btn-icon">🔑</span><span class="btn-text"> Log In</span>';
    authBtn.setAttribute('aria-label', 'Log in to session');
  }
}

async function checkAuthStatus() {
  try {
    const res = await fetch('/api/auth/status');
    if (res.ok) {
      const data = await res.json();
      globalAuthState.authenticated = data.authenticated;
      globalAuthState.passwordRequired = data.password_required;
      updateAuthButtonUI();
    }
  } catch (e) {
    console.warn('Failed to check auth status:', e);
  }
}

function requireAuthOr(action) {
  if (globalAuthState.passwordRequired && !globalAuthState.authenticated) {
    openPasswordModal(action);
    return false;
  }
  if (typeof action === 'function') action();
  return true;
}

let pendingDownloadAction = null;

function isAnyModalOpen() {
  const passwordModal = document.getElementById('password-modal');
  const editModal = document.getElementById('edit-modal');
  const downloadWarningModal = document.getElementById('download-warning-modal');
  const coverModal = document.getElementById('cover-modal');
  const shortcutsModal = document.getElementById('shortcuts-modal');
  return (passwordModal && !passwordModal.hidden) ||
         (editModal && !editModal.hidden) ||
         (downloadWarningModal && !downloadWarningModal.hidden) ||
         (coverModal && !coverModal.hasAttribute('hidden')) ||
         (shortcutsModal && !shortcutsModal.hidden);
}

function openDownloadWarningModal(pendingAction, formattedSize) {
  pendingDownloadAction = pendingAction || null;
  const modal = document.getElementById('download-warning-modal');
  const textEl = document.getElementById('download-warning-modal-text');
  const confirmBtn = document.getElementById('confirm-download-btn');

  if (textEl) {
    const sizeStr = formattedSize ? ` (${formattedSize})` : '';
    textEl.innerHTML = `This show is over 100 MB${sizeStr}.<br><br>Audio files are already compressed, so the ZIP archive will be large with minimal additional compression.<br><br>Do you want to proceed with downloading?`;
  }
  if (modal) {
    modal.removeAttribute('hidden');
    modal.setAttribute('aria-hidden', 'false');
    if (confirmBtn) confirmBtn.focus();
  }
}

function closeDownloadWarningModal() {
  const modal = document.getElementById('download-warning-modal');
  if (modal) {
    modal.setAttribute('hidden', '');
    modal.setAttribute('aria-hidden', 'true');
  }
  pendingDownloadAction = null;
}

function openPasswordModal(pendingAction) {
  pendingAuthAction = pendingAction || null;
  const modal = document.getElementById('password-modal');
  const errorEl = document.getElementById('password-error');
  const inputEl = document.getElementById('password-input');

  if (errorEl) errorEl.hidden = true;
  if (inputEl) inputEl.value = '';
  if (modal) {
    modal.removeAttribute('hidden');
    modal.setAttribute('aria-hidden', 'false');
    if (inputEl) inputEl.focus();
  }
}

function closePasswordModal() {
  const modal = document.getElementById('password-modal');
  if (modal) {
    modal.setAttribute('hidden', '');
    modal.setAttribute('aria-hidden', 'true');
  }
  pendingAuthAction = null;
}

function initAuthSystem() {
  updateAuthButtonUI();
  checkAuthStatus();

  const authBtn = document.getElementById('auth-btn');
  if (authBtn) {
    authBtn.addEventListener('click', async () => {
      if (globalAuthState.authenticated) {
        try {
          const res = await fetch('/api/logout', { method: 'POST' });
          if (res.ok) {
            globalAuthState.authenticated = false;
            updateAuthButtonUI();
            showToast('🔒 Logged out successfully');
            setTimeout(() => window.location.reload(), 400);
          } else {
            showToast('❌ Logout failed');
          }
        } catch (err) {
          showToast('❌ Error connecting to server');
        }
      } else {
        openPasswordModal(() => {
          updateAuthButtonUI();
          setTimeout(() => window.location.reload(), 400);
        });
      }
    });
  }

  const passwordForm = document.getElementById('password-form');
  const passwordError = document.getElementById('password-error');

  if (passwordForm) {
    passwordForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const passwordInput = document.getElementById('password-input');
      const password = passwordInput ? passwordInput.value : '';

      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password })
        });

        if (res.ok) {
          const data = await res.json();
          globalAuthState.authenticated = true;
          if (passwordError) passwordError.hidden = true;
          closePasswordModal();
          updateAuthButtonUI();
          showToast('🔓 Session authenticated');
          if (pendingAuthAction) {
            const act = pendingAuthAction;
            pendingAuthAction = null;
            act();
          } else {
            setTimeout(() => window.location.reload(), 400);
          }
        } else {
          const errData = await res.json().catch(() => ({}));
          globalAuthState.authenticated = false;
          updateAuthButtonUI();
          if (passwordError) {
            passwordError.textContent = errData.detail || 'Sorry, the password is incorrect.';
            passwordError.hidden = false;
          }
        }
      } catch (err) {
        if (passwordError) {
          passwordError.textContent = 'Sorry, the password is incorrect.';
          passwordError.hidden = false;
        }
      }
    });
  }

  // Intercept media player audio element 401 error
  const audioElement = document.getElementById('global-audio-element');
  if (audioElement) {
    audioElement.addEventListener('error', () => {
      if (globalAuthState.passwordRequired && !globalAuthState.authenticated) {
        openPasswordModal(() => {
          if (audioElement.src) {
            const playPromise = audioElement.play();
            if (playPromise !== undefined) {
              playPromise.then(() => updatePlayButtonUI(true)).catch(() => updatePlayButtonUI(false));
            }
          }
        });
      }
    });
  }

  // Track mousedown target to ensure backdrop clicks originated on the backdrop (not text selection drags)
  let mouseDownTarget = null;
  document.addEventListener('mousedown', (e) => {
    mouseDownTarget = e.target;
  });

  // Modal close button delegation and backdrop click listener for login, edit, and download warning modals
  document.addEventListener('click', (e) => {
    const isCloseBtn = e.target.matches('.js-close-modal') || e.target.closest('.js-close-modal');
    const target = e.target;
    const isBackdropClick = target.classList && target.classList.contains('modal-backdrop') && mouseDownTarget === target;

    if (isCloseBtn) {
      closePasswordModal();
      closeEditModal();
      closeDownloadWarningModal();
    } else if (isBackdropClick) {
      if (target.id === 'password-modal') {
        closePasswordModal();
      } else if (target.id === 'edit-modal') {
        closeEditModal();
      } else if (target.id === 'download-warning-modal') {
        closeDownloadWarningModal();
      }
    }
  });

  const confirmDownloadBtn = document.getElementById('confirm-download-btn');
  if (confirmDownloadBtn) {
    confirmDownloadBtn.addEventListener('click', () => {
      if (pendingDownloadAction) {
        const act = pendingDownloadAction;
        pendingDownloadAction = null;
        closeDownloadWarningModal();
        act();
      } else {
        closeDownloadWarningModal();
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' || e.code === 'Escape') {
      if (isAnyModalOpen()) {
        closePasswordModal();
        closeEditModal();
        closeDownloadWarningModal();
        closeCoverModal();
        closeShortcutsModal();
      }
    }
  });
}

/**
 * Initialize Show Cover Image Zoom Modal logic.
 */
function initCoverModal() {
  document.addEventListener('click', (e) => {
    const zoomBtn = e.target.closest('.js-zoom-cover');
    if (zoomBtn) {
      e.preventDefault();
      e.stopPropagation();
      const modal = document.getElementById('cover-modal');
      if (modal && !modal.hasAttribute('hidden')) {
        closeCoverModal();
      } else {
        const coverUrl = zoomBtn.getAttribute('data-cover-url') || zoomBtn.querySelector('img')?.src;
        const showTitle = zoomBtn.getAttribute('data-show-title') || '';
        if (coverUrl) {
          openCoverModal(coverUrl, showTitle);
        }
      }
      return;
    }

    const coverModal = e.target.closest('#cover-modal');
    if (coverModal && !coverModal.hasAttribute('hidden')) {
      closeCoverModal();
      return;
    }
  });
}

function openCoverModal(src, title) {
  const modal = document.getElementById('cover-modal');
  const img = document.getElementById('cover-modal-image');
  if (!modal || !img) return;

  img.src = src;
  img.alt = title ? `Zoomed cover image for ${title}` : 'Zoomed cover image';

  modal.removeAttribute('hidden');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function closeCoverModal() {
  const modal = document.getElementById('cover-modal');
  const img = document.getElementById('cover-modal-image');
  if (modal) {
    modal.setAttribute('hidden', '');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
  if (img) {
    img.src = '';
  }
}

/* Markdown Show Details Editor */
function initMarkdownEditor() {
  // Delegated click listener for Edit Show Details button
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.js-edit-show');
    if (btn) {
      e.preventDefault();
      requireAuthOr(() => openEditModal(btn));
    }
  });

  // Delegated click listener for protected download actions
  document.addEventListener('click', (e) => {
    const downloadBtn = e.target.closest('.js-download-track, .js-download-show');
    if (downloadBtn) {
      const href = downloadBtn.getAttribute('href');

      const triggerDownload = () => {
        if (globalAuthState.passwordRequired && !globalAuthState.authenticated) {
          openPasswordModal(() => {
            if (href) window.location.href = href;
          });
        } else {
          if (href) window.location.href = href;
        }
      };

      if (downloadBtn.classList.contains('js-download-show')) {
        const totalBytes = parseInt(downloadBtn.getAttribute('data-total-bytes') || '0', 10);
        const formattedSize = downloadBtn.getAttribute('data-formatted-size') || '';
        const hundredMB = 100 * 1024 * 1024;
        if (totalBytes >= hundredMB) {
          e.preventDefault();
          e.stopImmediatePropagation();
          openDownloadWarningModal(() => {
            triggerDownload();
          }, formattedSize);
          return;
        }
      }

      if (globalAuthState.passwordRequired && !globalAuthState.authenticated) {
        e.preventDefault();
        openPasswordModal(() => {
          if (href) window.location.href = href;
        });
      }
    }
  });

  // Tab switching between Write and Preview
  document.addEventListener('click', (e) => {
    if (e.target.closest('#tab-write-btn')) {
      switchToWriteTab();
    } else if (e.target.closest('#tab-preview-btn')) {
      switchToPreviewTab();
    }
  });

  // Markdown formatting toolbar button click handlers
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.md-btn');
    if (!btn) return;
    const descInput = document.getElementById('edit-description-input');
    if (!descInput) return;
    e.preventDefault();

    const action = btn.getAttribute('data-md-action');
    applyMarkdownFormatting(descInput, action);
  });

  // Ctrl+Enter / Cmd+Enter keyboard shortcut to submit edit form
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      const editModal = document.getElementById('edit-modal');
      const editForm = document.getElementById('edit-show-form');
      if (editModal && !editModal.hidden && editForm) {
        e.preventDefault();
        if (typeof editForm.requestSubmit === 'function') {
          editForm.requestSubmit();
        } else {
          editForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        }
      }
    }
  });

  // Save changes form submission
  document.addEventListener('submit', async (e) => {
    if (e.target && e.target.id === 'edit-show-form') {
      e.preventDefault();
      const showId = document.getElementById('edit-show-id')?.value;
      const title = document.getElementById('edit-title-input')?.value || '';
      const author = document.getElementById('edit-author-input')?.value || '';
      const publisher = document.getElementById('edit-publisher-input')?.value || '';
      const descInput = document.getElementById('edit-description-input');
      const description = descInput ? descInput.value : '';
      const coverFileInput = document.getElementById('edit-cover-file');
      const coverSelect = document.getElementById('edit-cover-select');
      const errorEl = document.getElementById('edit-form-error');

      if (!showId) return;

      try {
        let updatedCoverShow = null;
        // Handle cover file upload if selected
        if (coverFileInput && coverFileInput.files && coverFileInput.files.length > 0) {
          const file = coverFileInput.files[0];
          const formData = new FormData();
          formData.append('file', file);

          const uploadRes = await fetch(`/api/shows/${showId}/upload-cover`, {
            method: 'POST',
            body: formData
          });

          if (!uploadRes.ok) {
            const errData = await uploadRes.json().catch(() => ({}));
            if (errorEl) {
              errorEl.textContent = errData.detail || 'Failed to upload cover image.';
              errorEl.hidden = false;
            }
            return;
          } else {
            const uData = await uploadRes.json().catch(() => ({}));
            if (uData.show) updatedCoverShow = uData.show;
          }
        } else if (coverSelect && coverSelect.value) {
          // Handle existing image selection
          const selectRes = await fetch(`/api/shows/${showId}/select-cover`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: coverSelect.value })
          });

          if (!selectRes.ok) {
            const errData = await selectRes.json().catch(() => ({}));
            if (errorEl) {
              errorEl.textContent = errData.detail || 'Failed to select cover image.';
              errorEl.hidden = false;
            }
            return;
          } else {
            const sData = await selectRes.json().catch(() => ({}));
            if (sData.show) updatedCoverShow = sData.show;
          }
        }

        // Save text metadata
        const res = await fetch(`/api/shows/${showId}/edit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, author, publisher, description })
        });

        if (res.ok) {
          const data = await res.json();
          showToast('✨ Show details saved successfully!');
          closeEditModal();
          const finalShow = data.show || updatedCoverShow;
          if (updatedCoverShow && updatedCoverShow.updated_at && finalShow) {
            finalShow.updated_at = updatedCoverShow.updated_at;
          }
          updateShowPageDOM(finalShow);
        } else {
          const errData = await res.json().catch(() => ({}));
          if (res.status === 401) {
            closeEditModal();
            openPasswordModal();
          } else if (errorEl) {
            errorEl.textContent = errData.detail || 'Failed to update show metadata.';
            errorEl.hidden = false;
          }
        }
      } catch (err) {
        if (errorEl) {
          errorEl.textContent = 'Error connecting to server.';
          errorEl.hidden = false;
        }
      }
    }
  });

  // Dynamic cover preview update when selecting image from show folder dropdown
  document.addEventListener('change', (e) => {
    if (e.target && e.target.id === 'edit-cover-select') {
      const showId = document.getElementById('edit-show-id')?.value;
      const coverPreview = document.getElementById('edit-cover-preview');
      const coverPlaceholder = document.getElementById('edit-cover-placeholder');
      const coverFileInput = document.getElementById('edit-cover-file');
      const errorEl = document.getElementById('edit-form-error');

      if (errorEl) errorEl.hidden = true;
      if (coverFileInput) coverFileInput.value = '';

      const selectedFilename = e.target.value;
      if (selectedFilename && showId && coverPreview) {
        coverPreview.src = `/covers/${showId}?file=${encodeURIComponent(selectedFilename)}&t=${Date.now()}`;
        coverPreview.style.display = 'block';
        if (coverPlaceholder) coverPlaceholder.style.display = 'none';
      } else if (showId && coverPreview) {
        coverPreview.src = `/covers/${showId}?t=${Date.now()}`;
        coverPreview.style.display = 'block';
      }
    }
  });

  // Client-side validation and dynamic preview update for cover image file upload
  document.addEventListener('change', (e) => {
    if (e.target && e.target.id === 'edit-cover-file') {
      const file = e.target.files && e.target.files[0];
      const errorEl = document.getElementById('edit-form-error');
      const coverSelect = document.getElementById('edit-cover-select');
      const coverPreview = document.getElementById('edit-cover-preview');
      const coverPlaceholder = document.getElementById('edit-cover-placeholder');

      if (coverSelect) coverSelect.value = '';
      if (!file) return;

      const allowedExts = ['.webp', '.png', '.jpg', '.jpeg'];
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      if (!allowedExts.includes(ext)) {
        if (errorEl) {
          errorEl.textContent = 'Invalid file format. Please choose a WebP, PNG, or JPEG image.';
          errorEl.hidden = false;
        }
        e.target.value = '';
        return;
      }

      if (file.size > 5 * 1024 * 1024) {
        if (errorEl) {
          errorEl.textContent = 'File size exceeds maximum limit of 5MB.';
          errorEl.hidden = false;
        }
        e.target.value = '';
        return;
      }

      if (errorEl) errorEl.hidden = true;

      if (coverPreview) {
        coverPreview.src = URL.createObjectURL(file);
        coverPreview.style.display = 'block';
        if (coverPlaceholder) coverPlaceholder.style.display = 'none';
      }
    }
  });

  // Handle click and drag-and-drop file upload on cover preview wrapper button
  let coverDragCounter = 0;

  document.addEventListener('click', (e) => {
    const wrapper = e.target.closest('.cover-preview-wrapper');
    if (wrapper) {
      const coverFileInput = document.getElementById('edit-cover-file');
      if (coverFileInput) coverFileInput.click();
    }
  });

  document.addEventListener('dragenter', (e) => {
    const wrapper = e.target.closest('.cover-preview-wrapper');
    if (wrapper) {
      e.preventDefault();
      coverDragCounter++;
      wrapper.classList.add('drag-over');
    }
  });

  document.addEventListener('dragover', (e) => {
    const wrapper = e.target.closest('.cover-preview-wrapper');
    if (wrapper) {
      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
      wrapper.classList.add('drag-over');
    } else {
      const modal = e.target.closest('#edit-modal');
      if (modal) {
        e.preventDefault();
      }
    }
  });

  document.addEventListener('dragleave', (e) => {
    const wrapper = e.target.closest('.cover-preview-wrapper');
    if (wrapper) {
      e.preventDefault();
      coverDragCounter--;
      if (coverDragCounter <= 0) {
        coverDragCounter = 0;
        wrapper.classList.remove('drag-over');
      }
    }
  });

  document.addEventListener('drop', (e) => {
    const wrapper = e.target.closest('.cover-preview-wrapper');
    if (wrapper) {
      e.preventDefault();
      coverDragCounter = 0;
      wrapper.classList.remove('drag-over');

      const files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length > 0) {
        const file = files[0];
        const coverFileInput = document.getElementById('edit-cover-file');
        if (coverFileInput) {
          try {
            const dt = new DataTransfer();
            dt.items.add(file);
            coverFileInput.files = dt.files;
          } catch (err) {
            // Fallback for environment without DataTransfer constructor
          }
          coverFileInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }
    } else {
      const modal = e.target.closest('#edit-modal');
      if (modal) {
        e.preventDefault();
      }
    }
  });
}

async function openEditModal(btn) {
  const editModal = document.getElementById('edit-modal');
  if (!editModal) return;

  const showId = btn.getAttribute('data-show-id') || document.getElementById('edit-show-id')?.value;
  const title = btn.getAttribute('data-title') || '';
  const author = btn.getAttribute('data-author') || '';
  const publisher = btn.getAttribute('data-publisher') || '';
  const description = btn.getAttribute('data-description') || '';

  const showIdInput = document.getElementById('edit-show-id');
  const titleInput = document.getElementById('edit-title-input');
  const authorInput = document.getElementById('edit-author-input');
  const publisherInput = document.getElementById('edit-publisher-input');
  const descInput = document.getElementById('edit-description-input');
  const coverSelect = document.getElementById('edit-cover-select');
  const coverFileInput = document.getElementById('edit-cover-file');
  const coverPreview = document.getElementById('edit-cover-preview');
  const coverPlaceholder = document.getElementById('edit-cover-placeholder');
  const errorEl = document.getElementById('edit-form-error');

  const section = btn.getAttribute('data-section') || '';
  const authorGroup = document.getElementById('edit-author-group');
  const publisherGroup = document.getElementById('edit-publisher-group');
  if (authorGroup) authorGroup.style.display = (section === 'podcasts') ? 'none' : 'block';
  if (publisherGroup) publisherGroup.style.display = (section === 'books' || !section) ? 'none' : 'block';

  if (showIdInput) showIdInput.value = showId;
  if (titleInput) titleInput.value = title;
  if (authorInput) authorInput.value = author;
  if (publisherInput) publisherInput.value = publisher;
  if (descInput) descInput.value = description;
  if (coverFileInput) coverFileInput.value = '';

  if (coverPreview) {
    coverPreview.src = `/covers/${showId}?t=${Date.now()}`;
    coverPreview.style.display = 'block';
    coverPreview.onerror = () => {
      coverPreview.style.display = 'none';
      if (coverPlaceholder) coverPlaceholder.style.display = 'flex';
    };
  }
  if (coverPlaceholder) coverPlaceholder.style.display = 'none';

  if (coverSelect) {
    coverSelect.innerHTML = '<option value="">-- Keep current cover --</option>';
    try {
      const imgRes = await fetch(`/api/shows/${showId}/images`);
      if (imgRes.ok) {
        const imgData = await imgRes.json();
        if (imgData.images && imgData.images.length > 0) {
          imgData.images.forEach(img => {
            const opt = document.createElement('option');
            opt.value = img.filename;
            opt.textContent = `${img.filename} (${img.formatted_size})`;
            coverSelect.appendChild(opt);
          });
        }
      }
    } catch (e) {}
  }

  switchToWriteTab();
  if (errorEl) errorEl.hidden = true;

  editModal.removeAttribute('hidden');
  editModal.setAttribute('aria-hidden', 'false');
  if (titleInput) titleInput.focus();
}

function switchToWriteTab() {
  const writeBtn = document.getElementById('tab-write-btn');
  const previewBtn = document.getElementById('tab-preview-btn');
  const descInput = document.getElementById('edit-description-input');
  const descPreview = document.getElementById('edit-description-preview');
  const mdToolbar = document.getElementById('md-toolbar');

  if (writeBtn) writeBtn.classList.add('active');
  if (previewBtn) previewBtn.classList.remove('active');
  if (descInput) descInput.hidden = false;
  if (mdToolbar) mdToolbar.style.display = 'flex';
  if (descPreview) descPreview.hidden = true;
}

function switchToPreviewTab() {
  const writeBtn = document.getElementById('tab-write-btn');
  const previewBtn = document.getElementById('tab-preview-btn');
  const descInput = document.getElementById('edit-description-input');
  const descPreview = document.getElementById('edit-description-preview');
  const mdToolbar = document.getElementById('md-toolbar');

  if (previewBtn) previewBtn.classList.add('active');
  if (writeBtn) writeBtn.classList.remove('active');
  if (descInput) descInput.hidden = true;
  if (mdToolbar) mdToolbar.style.display = 'none';
  if (descPreview) {
    descPreview.innerHTML = renderSimpleMarkdown(descInput ? descInput.value : '');
    descPreview.hidden = false;
  }
}

function closeEditModal() {
  const editModal = document.getElementById('edit-modal');
  if (editModal) {
    editModal.setAttribute('hidden', '');
    editModal.setAttribute('aria-hidden', 'true');
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function updateShowPageDOM(show) {
  if (!show) return;

  if (show.show_colors && show.show_colors.css_variables) {
    document.body.setAttribute('style', show.show_colors.css_variables);
  }

  const detailTitle = document.querySelector('.detail-title');
  if (detailTitle) detailTitle.textContent = show.title;

  const detailHeader = document.querySelector('.show-detail-header');
  if (detailHeader) {
    const detailInfo = detailHeader.querySelector('.detail-info');
    if (detailInfo) {
      let bylineEl = detailInfo.querySelector('div[style*="color: var(--text-muted)"]');
      const isBook = show.section === 'books';
      const labelText = isBook ? (show.author ? `by ${show.author}` : '') : (show.publisher ? show.publisher : '');

      if (labelText) {
        if (!bylineEl) {
          bylineEl = document.createElement('div');
          bylineEl.style.cssText = 'font-size: 1.1rem; color: var(--text-muted); margin-top: -0.5rem; margin-bottom: 0.8rem; font-weight: 500;';
          if (detailTitle) detailTitle.after(bylineEl);
        }
        if (isBook) {
          bylineEl.textContent = labelText;
        } else {
          bylineEl.innerHTML = `<span class="publisher-label">${escapeHtml(labelText)}</span>`;
        }
      } else if (bylineEl) {
        bylineEl.remove();
      }
    }
  }

  const detailDesc = document.querySelector('.detail-description');
  if (detailDesc) {
    detailDesc.innerHTML = show.description_html || show.description || '';
  }

  if (show.show_id) {
    const timestamp = Date.now();
    const coverUrl = `/covers/${show.show_id}?v=${timestamp}`;

    // 1. Update show page detail cover container (show.html)
    const detailCoverContainer = document.querySelector('.detail-cover-container');
    if (detailCoverContainer) {
      if (show.cover_path) {
        const existingImg = detailCoverContainer.querySelector('img.detail-cover');
        const existingLink = detailCoverContainer.querySelector('.detail-cover-link, .js-zoom-cover');
        if (existingImg) {
          existingImg.src = coverUrl;
          existingImg.alt = `Cover for ${show.title}`;
          if (existingLink) {
            existingLink.setAttribute('data-cover-url', coverUrl);
            existingLink.setAttribute('data-show-title', show.title);
            existingLink.setAttribute('aria-label', `Zoom cover image for ${show.title}`);
          }
        } else {
          const placeholder = detailCoverContainer.querySelector('.placeholder-cover');
          if (placeholder) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'detail-cover-link js-zoom-cover';
            btn.setAttribute('data-cover-url', coverUrl);
            btn.setAttribute('data-show-title', show.title);
            btn.setAttribute('aria-label', `Zoom cover image for ${show.title}`);
            btn.setAttribute('title', 'Click to zoom cover image');
            btn.innerHTML = `<img src="${coverUrl}" alt="Cover for ${escapeHtml(show.title)}" class="detail-cover"><span class="cover-zoom-hint" aria-hidden="true">🔍 Zoom</span>`;
            placeholder.replaceWith(btn);
          }
        }
      } else {
        const existingLink = detailCoverContainer.querySelector('.detail-cover-link');
        if (existingLink) {
          const placeholder = document.createElement('div');
          placeholder.className = 'placeholder-cover detail-cover';
          placeholder.innerHTML = '<span>🎙️</span>';
          existingLink.replaceWith(placeholder);
        }
      }
    }

    // 2. Update index listing card (index.html)
    const showCard = document.getElementById(`show-${show.show_id}`);
    if (showCard) {
      showCard.setAttribute('data-title', (show.title || '').toLowerCase());
      showCard.setAttribute('data-author', (show.author || '').toLowerCase());
      showCard.setAttribute('data-publisher', (show.publisher || '').toLowerCase());

      const cardTitleLink = showCard.querySelector('.show-title-link');
      if (cardTitleLink) cardTitleLink.textContent = show.title;

      const coverWrapper = showCard.querySelector('.cover-wrapper');
      if (coverWrapper) {
        coverWrapper.setAttribute('aria-label', `View ${show.title}`);
        if (show.cover_path) {
          const cardImg = coverWrapper.querySelector('.cover-image');
          if (cardImg) {
            cardImg.src = coverUrl;
            cardImg.alt = `Cover for ${show.title}`;
          } else {
            const cardPlaceholder = coverWrapper.querySelector('.placeholder-cover');
            if (cardPlaceholder) {
              const newImg = document.createElement('img');
              newImg.src = coverUrl;
              newImg.alt = `Cover for ${show.title}`;
              newImg.className = 'cover-image';
              newImg.loading = 'lazy';
              cardPlaceholder.replaceWith(newImg);
            }
          }
        } else {
          const cardImg = coverWrapper.querySelector('.cover-image');
          if (cardImg) {
            const isBook = show.section === 'books';
            const icon = isBook ? '📚' : '🎙️';
            const placeholder = document.createElement('div');
            placeholder.className = 'placeholder-cover';
            placeholder.innerHTML = `<span>${icon}</span><span>${escapeHtml(show.title)}</span>`;
            cardImg.replaceWith(placeholder);
          }
        }
      }

      // Update card byline on index
      const isBook = show.section === 'books';
      let cardByline = showCard.querySelector('.card-body .card-byline');
      const labelText = isBook ? (show.author ? `by ${show.author}` : '') : (show.publisher ? show.publisher : '');
      if (labelText) {
        if (!cardByline) {
          cardByline = document.createElement('div');
          cardByline.className = 'card-byline';
          const cardBody = showCard.querySelector('.card-body');
          if (cardBody) cardBody.appendChild(cardByline);
        }
        if (isBook) {
          cardByline.textContent = labelText;
        } else {
          cardByline.innerHTML = `<span class="publisher-label">${escapeHtml(labelText)}</span>`;
        }
      } else if (cardByline) {
        cardByline.remove();
      }
    }

    // 3. Update any other matching cover images on page
    const coverImgs = document.querySelectorAll(`.cover-image, #show-${show.show_id} .cover-image, img.detail-cover`);
    coverImgs.forEach(img => {
      img.src = coverUrl;
    });

    // 4. Update data-cover-url on episode table/list rows
    if (show.cover_path) {
      document.querySelectorAll(`[data-audio-src*="/audio/${show.show_id}/"]`).forEach(el => {
        el.setAttribute('data-cover-url', coverUrl);
      });
    }

    // 5. Update audio player cover image if currently playing this show
    const playerCover = document.getElementById('player-cover');
    const playerPlaceholder = document.getElementById('player-cover-placeholder');
    if (playerCover && playerCover.src && playerCover.src.includes(`/covers/${show.show_id}`)) {
      if (show.cover_path) {
        playerCover.src = coverUrl;
        playerCover.style.display = 'block';
        if (playerPlaceholder) playerPlaceholder.style.display = 'none';
      }
    }
  }

  const editBtn = document.querySelector('.js-edit-show');
  if (editBtn) {
    editBtn.setAttribute('data-title', show.title);
    editBtn.setAttribute('data-author', show.author || '');
    editBtn.setAttribute('data-publisher', show.publisher || '');
    editBtn.setAttribute('data-description', show.description || '');
  }

  if (show.author) {
    const authorsDatalist = document.getElementById('all-authors-list');
    if (authorsDatalist && !Array.from(authorsDatalist.options).some(opt => opt.value === show.author)) {
      const opt = document.createElement('option');
      opt.value = show.author;
      authorsDatalist.appendChild(opt);
    }
  }
  if (show.publisher) {
    const publishersDatalist = document.getElementById('all-publishers-list');
    if (publishersDatalist && !Array.from(publishersDatalist.options).some(opt => opt.value === show.publisher)) {
      const opt = document.createElement('option');
      opt.value = show.publisher;
      publishersDatalist.appendChild(opt);
    }
  }
}

function applyMarkdownFormatting(textarea, action) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selectedText = textarea.value.substring(start, end);
  let replacement = '';

  switch (action) {
    case 'bold':
      replacement = `**${selectedText || 'bold text'}**`;
      break;
    case 'italic':
      replacement = `*${selectedText || 'italic text'}*`;
      break;
    case 'heading':
      replacement = `### ${selectedText || 'Heading'}`;
      break;
    case 'list':
      replacement = selectedText ? selectedText.split('\n').map(l => `- ${l}`).join('\n') : '- List item';
      break;
    case 'olist':
      replacement = selectedText ? selectedText.split('\n').map((l, i) => `${i + 1}. ${l}`).join('\n') : '1. List item';
      break;
    case 'code':
      replacement = `\`${selectedText || 'code'}\``;
      break;
    case 'quote':
      replacement = `> ${selectedText || 'Quote text'}`;
      break;
    case 'link':
      replacement = `[${selectedText || 'link text'}](url)`;
      break;
    default:
      return;
  }

  textarea.setRangeText(replacement, start, end, 'select');
  textarea.focus();
}

function renderSimpleMarkdown(md) {
  if (!md) return '<em>No description provided.</em>';
  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$2</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/^\- (.*$)/gim, '<ul><li>$1</li></ul>')
    .replace(/\n\n/g, '<br><br>');
  return html;
}
