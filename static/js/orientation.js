(function () {
  // Create overlay
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
    display: 'none', // this stays hidden unless portrait
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    padding: '2vh',
    boxSizing: 'border-box',
    flexDirection: 'column',
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    overflow: "none"
  });

  // Create message box
  const message = document.createElement('div');
  message.textContent = '🔄 Please rotate your phone to landscape mode to continue.';
  Object.assign(message.style, {
    fontSize: '3.2vh',
    color: '#f0f0f0',
    backgroundColor: '#2e2e3e',
    padding: '2vh 2.5vh',
    borderRadius: '1.5vh',
    boxShadow: '0 1.2vh 2.4vh rgba(0, 0, 0, 0.4)',
    maxWidth: '90vh',
    lineHeight: '1.5',
    transition: 'all 0.3s ease',
    border: '1vh solid #444',
    overflow: "none"

  });

  overlay.appendChild(message);
  document.body.appendChild(overlay);

  // Check orientation
  function checkOrientation() {
    if (window.innerHeight > window.innerWidth) {
      overlay.style.display = 'flex';
    } else {
      overlay.style.display = 'none';
    }
  }

  // Wait a tiny bit to ensure DOM is ready (optional safeguard)
  window.addEventListener('load', () => {
    setTimeout(checkOrientation, 50);
  });
  window.addEventListener('resize', checkOrientation);
  window.addEventListener('orientationchange', checkOrientation);
})();
