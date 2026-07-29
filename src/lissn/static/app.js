/* lissn Lightweight Frontend Interactions */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSectionFiltering();
  initCopyButtons();
  initShareButtons();
  initRescanButton();
  initMediaPlayer();
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

  let booksVisible = 0;
  let podcastsVisible = 0;

  cards.forEach(card => {
    const cardSection = card.getAttribute('data-section');
    if (section === 'all' || cardSection === section) {
      card.style.display = 'flex';
      if (cardSection === 'books') booksVisible++;
      if (cardSection === 'podcasts') podcastsVisible++;
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
 * Initialize Bottom Media Player with auto-continue playlist support.
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

  let playlist = [];
  let currentTrackIndex = -1;
  let isAutoContinue = localStorage.getItem('lissn_auto_continue') !== 'false'; // Default to true

  // Sync initial auto-continue UI state
  updateAutoContinueUI();

  // Populate playlist if on show page
  const trackRows = Array.from(document.querySelectorAll('.track-row'));
  if (trackRows.length > 0) {
    playlist = trackRows.map((row, idx) => ({
      index: idx,
      src: row.getAttribute('data-audio-src'),
      trackTitle: row.getAttribute('data-track-title'),
      showTitle: row.getAttribute('data-show-title'),
      coverUrl: row.getAttribute('data-cover-url'),
      element: row
    }));
  }

  // Play button click handlers on track table
  document.addEventListener('click', (e) => {
    const playTrackBtn = e.target.closest('.js-play-track');
    if (playTrackBtn) {
      const idx = parseInt(playTrackBtn.getAttribute('data-track-index'), 10);
      if (!isNaN(idx) && playlist[idx]) {
        if (currentTrackIndex === idx && !audioElement.paused) {
          audioElement.pause();
        } else {
          playTrack(idx);
        }
      }
    }
  });

  function playTrack(index) {
    if (index < 0 || index >= playlist.length) return;

    currentTrackIndex = index;
    const track = playlist[index];

    audioElement.src = track.src;
    audioElement.playbackRate = parseFloat(speedSelect.value) || 1.0;
    audioElement.play().then(() => {
      updatePlayButtonUI(true);
    }).catch(err => {
      console.warn('Playback interrupted:', err);
    });

    bottomPlayer.classList.add('visible');

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

    highlightActiveTrackRow(index);
  }

  function highlightActiveTrackRow(index) {
    trackRows.forEach((row, i) => {
      const playBtnEl = row.querySelector('.js-play-track');
      if (i === index) {
        row.classList.add('active-track');
        if (playBtnEl) playBtnEl.textContent = '⏸ Pause';
      } else {
        row.classList.remove('active-track');
        if (playBtnEl) playBtnEl.textContent = '▶ Play';
      }
    });
  }

  function updatePlayButtonUI(isPlaying) {
    if (playBtn) {
      playBtn.textContent = isPlaying ? '⏸️' : '▶️';
      playBtn.setAttribute('aria-label', isPlaying ? 'Pause audio' : 'Play audio');
    }
    if (currentTrackIndex >= 0 && playlist[currentTrackIndex]) {
      const rowPlayBtn = playlist[currentTrackIndex].element?.querySelector('.js-play-track');
      if (rowPlayBtn) {
        rowPlayBtn.textContent = isPlaying ? '⏸ Pause' : '▶ Play';
      }
    }
  }

  // Play / Pause toggle
  if (playBtn) {
    playBtn.addEventListener('click', () => {
      if (!audioElement.src && playlist.length > 0) {
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
      if (currentTrackIndex < playlist.length - 1) {
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
    if (isAutoContinue && currentTrackIndex < playlist.length - 1) {
      showToast(`▶ Auto-continuing: ${playlist[currentTrackIndex + 1].trackTitle}`);
      playTrack(currentTrackIndex + 1);
    } else if (currentTrackIndex >= playlist.length - 1) {
      showToast('🎉 End of show playlist');
    }
  });

  // Audio status events
  audioElement.addEventListener('play', () => updatePlayButtonUI(true));
  audioElement.addEventListener('pause', () => updatePlayButtonUI(false));

  // Time & Seek Bar updates
  audioElement.addEventListener('timeupdate', () => {
    if (!isNaN(audioElement.duration) && audioElement.duration > 0) {
      const pct = (audioElement.currentTime / audioElement.duration) * 100;
      seekBar.value = pct;
      currentTimeEl.textContent = formatTime(audioElement.currentTime);
      totalTimeEl.textContent = formatTime(audioElement.duration);
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
    muteBtn.textContent = (audioElement.muted || audioElement.volume === 0) ? '🔇' : '🔊';
  }

  // Keyboard Shortcuts (Space play/pause, Left/Right seek, N next)
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

