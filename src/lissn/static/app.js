/* lissn Lightweight Frontend Interactions & Persistent Media Player */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSectionFiltering();
  initCopyButtons();
  initShareButtons();
  initRescanButton();
  initMediaPlayer();
  initClientNavigation();
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
  btn.innerHTML = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
  btn.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
}

/**
 * Initialize section filtering tabs ('all', 'books', 'podcasts').
 */
function initSectionFiltering() {
  const tabs = document.querySelectorAll('.tab-btn');
  if (!tabs.length) return;

  const params = new URLSearchParams(window.location.search);
  const activeSection = params.get('section') || 'all';

  applyFilter(activeSection);

  tabs.forEach(tab => {
    tab.addEventListener('click', (e) => {
      const section = e.currentTarget.getAttribute('data-section');
      applyFilter(section);
      
      // Update URL query parameter cleanly without reloading page
      const url = new URL(window.location);
      if (section === 'all') {
        url.searchParams.delete('section');
      } else {
        url.searchParams.set('section', section);
      }
      window.history.pushState({}, '', url);
    });
  });
}

function applyFilter(section) {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(tab => {
    if (tab.getAttribute('data-section') === section) {
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

  cards.forEach(card => {
    const cardSection = card.getAttribute('data-section');
    if (section === 'all' || cardSection === section) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });

  if (sectionBooks) {
    sectionBooks.style.display = (section === 'all' || section === 'books') ? 'block' : 'none';
  }
  if (sectionPodcasts) {
    sectionPodcasts.style.display = (section === 'all' || section === 'podcasts') ? 'block' : 'none';
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
 */
function initClientNavigation() {
  document.addEventListener('click', (e) => {
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
      href.includes('/covers/')
    ) {
      return;
    }

    const targetUrl = new URL(href, window.location.origin);
    if (targetUrl.origin !== window.location.origin) return;

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

    // Scroll window to top
    window.scrollTo({ top: 0, behavior: 'instant' });

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
  } catch (err) {
    console.warn('Navigation fetch error, falling back to full page load:', err);
    window.location.href = urlStr;
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
  const trackTitleEl = document.getElementById('player-track-title');
  const showTitleEl = document.getElementById('player-show-title');
  const coverImg = document.getElementById('player-cover');
  const coverPlaceholder = document.getElementById('player-cover-placeholder');

  let activePlaylist = [];
  let currentTrackIndex = -1;
  let isAutoContinue = localStorage.getItem('lissn_auto_continue') !== 'false'; // Default to true

  // Sync initial auto-continue UI state
  updateAutoContinueUI();

  // Restore saved player state from sessionStorage if available
  restoreSavedPlayerState();

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
      const currentSrc = audioElement.getAttribute('src') || audioElement.src;
      if (currentSrc) {
        const foundIdx = activePlaylist.findIndex(t => currentSrc.endsWith(t.src) || t.src.endsWith(currentSrc));
        if (foundIdx !== -1) {
          currentTrackIndex = foundIdx;
        }
      }
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
      const idx = parseInt(trackRow.getAttribute('data-track-index'), 10);
      if (!isNaN(idx) && activePlaylist[idx]) {
        if (currentTrackIndex === idx && !audioElement.paused) {
          audioElement.pause();
        } else {
          playTrack(idx);
        }
      }
    }
  });

  // Support Keyboard Enter & Space key on focused track row
  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
    if (document.activeElement && document.activeElement.classList.contains('track-row')) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const idx = parseInt(document.activeElement.getAttribute('data-track-index'), 10);
        if (!isNaN(idx) && activePlaylist[idx]) {
          if (currentTrackIndex === idx && !audioElement.paused) {
            audioElement.pause();
          } else {
            playTrack(idx);
          }
        }
      }
    }
  });

  function playTrack(index) {
    if (index < 0 || index >= activePlaylist.length) return;

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
  const SVG_TRACK_PLAY = '<svg class="btn-play-icon" width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> <span>Play</span>';
  const SVG_TRACK_PAUSE = '<svg class="btn-play-icon" width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect></svg> <span>Pause</span>';

  function highlightActiveTrackRow() {
    const currentSrc = audioElement.getAttribute('src') || audioElement.src;
    const trackRows = document.querySelectorAll('.track-row');

    trackRows.forEach((row) => {
      const rowSrc = row.getAttribute('data-audio-src');
      const playBtnEl = row.querySelector('.js-play-track');

      if (rowSrc && currentSrc && (currentSrc.endsWith(rowSrc) || rowSrc.endsWith(currentSrc))) {
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
      totalTimeEl.textContent = formatTime(audioElement.duration);
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

  // Save current player state to sessionStorage
  function savePlayerState() {
    if (!audioElement.src) return;
    const state = {
      src: audioElement.getAttribute('src') || audioElement.src,
      trackTitle: trackTitleEl ? trackTitleEl.textContent : '',
      showTitle: showTitleEl ? showTitleEl.textContent : '',
      coverUrl: (coverImg && coverImg.style.display !== 'none') ? coverImg.src : null,
      currentTime: audioElement.currentTime || 0,
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
      if (state && state.src) {
        audioElement.src = state.src;
        if (state.currentTime) audioElement.currentTime = state.currentTime;

        if (trackTitleEl && state.trackTitle) trackTitleEl.textContent = state.trackTitle;
        if (showTitleEl && state.showTitle) showTitleEl.textContent = state.showTitle;

        if (state.coverUrl) {
          coverImg.src = state.coverUrl;
          coverImg.style.display = 'block';
          if (coverPlaceholder) coverPlaceholder.style.display = 'none';
        }

        bottomPlayer.classList.add('visible');
        document.body.classList.add('has-active-player');
        updatePlayButtonUI(!state.paused);
      }
    } catch (e) {
      // Ignore restoration errors
    }
  }

  // Global Keyboard Shortcuts (Space play/pause, Left/Right seek, N next, P prev)
  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;

    if (e.code === 'Space') {
      e.preventDefault();
      playBtn?.click();
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      skipBackBtn?.click();
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      skipFwdBtn?.click();
    } else if (e.key === 'n' || e.key === 'N') {
      nextBtn?.click();
    } else if (e.key === 'p' || e.key === 'P') {
      prevBtn?.click();
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
