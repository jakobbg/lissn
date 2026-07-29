/* lissn Lightweight Frontend Interactions */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSectionFiltering();
  initCopyButtons();
  initShareButtons();
  initRescanButton();
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
