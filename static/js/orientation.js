(function () {
  const overlay = document.createElement('div');
  overlay.id = 'rotate-warning';
  Object.assign(overlay.style, {
    position: 'fixed',
    top: '0',
    left: '0',
    width: '100%',
    height: '100%',
    background: 'linear-gradient(135deg, #1e1e2f 0%, #2c2c3c 100%)',
    zIndex: '99999',
    display: 'none',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    padding: '2vh',
    boxSizing: 'border-box',
    flexDirection: 'column',
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
  });

  const message = document.createElement('div');
  message.textContent = '🔄 Please rotate your phone to landscape mode to continue.';
  Object.assign(message.style, {
    fontSize: '3vh',
    color: '#f0f0f0',
    backgroundColor: '#2e2e3e',
    padding: '2vh',
    borderRadius: '1.5vh',
    boxShadow: '0 1vh 2vh rgba(0, 0, 0, 0.4)',
    maxWidth: '90vh',
    lineHeight: '1.5',
    marginBottom: '2vh',
    border: '0.5vh solid #444'
  });

  overlay.appendChild(message);

  if ('orientation' in screen && screen.orientation.lock && document.documentElement.requestFullscreen) {
    const fullscreenBtn = document.createElement('button');
    fullscreenBtn.textContent = '🔳 Enter Fullscreen & Rotate';
    Object.assign(fullscreenBtn.style, {
      fontSize: '2.5vh',
      padding: '1.2vh 2.4vh',
      borderRadius: '1vh',
      border: 'none',
      backgroundColor: '#4a90e2',
      color: 'white',
      cursor: 'pointer',
      boxShadow: '0 0.5vh 1vh rgba(0, 0, 0, 0.3)'
    });

    fullscreenBtn.addEventListener('click', async () => {
      try {
        await document.documentElement.requestFullscreen();
        await screen.orientation.lock('landscape');
        sessionStorage.setItem('fullscreenMode', 'true'); // ✅ remember
        overlay.style.display = 'none';
      } catch (err) {
        alert('Could not enter fullscreen or lock orientation: ' + err.message);
      }
    });

    overlay.appendChild(fullscreenBtn);
  } else {
    const fallbackNote = document.createElement('div');
    fallbackNote.textContent = '📱 If nothing happens, please rotate manually to landscape.';
    fallbackNote.style.color = '#bbb';
    fallbackNote.style.marginTop = '2vh';
    fallbackNote.style.fontSize = '2vh';
    overlay.appendChild(fallbackNote);
  }

  document.body.appendChild(overlay);

  function checkOrientation() {
    const isPortrait = window.innerHeight > window.innerWidth;
    const isFullscreen = !!document.fullscreenElement || window.innerHeight === screen.height;

    const hasFullscreenFlag = sessionStorage.getItem('fullscreenMode') === 'true';

    if (isPortrait && !hasFullscreenFlag) {
      overlay.style.display = 'flex';
    } else {
      overlay.style.display = 'none';
    }
  }

  window.addEventListener('load', () => {
    setTimeout(checkOrientation, 50);
  });
  window.addEventListener('resize', checkOrientation);
  window.addEventListener('orientationchange', checkOrientation);
})();