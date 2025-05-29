document.addEventListener('DOMContentLoaded', () => {
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
      zIndex: '9999',
      display: 'none',  // initially hidden
      justifyContent: 'center',
      alignItems: 'center',
      textAlign: 'center',
      padding: '2vh',
      boxSizing: 'border-box',
      flexDirection: 'column',
      fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
    });
  
    // Create message box
    const message = document.createElement('div');
    message.textContent = '🔄 Please rotate your phone to landscape mode to continue.';
    Object.assign(message.style, {
      fontSize: '3.2vh',
      color: '#f0f0f0',
      backgroundColor: '#2e2e3e',
      padding: '2rem 2.5rem',
      borderRadius: '1.5rem',
      boxShadow: '0 12px 24px rgba(0, 0, 0, 0.4)',
      maxWidth: '90vw',
      lineHeight: '1.5',
      transition: 'all 0.3s ease',
      border: '1px solid #444'
    });
  
    overlay.appendChild(message);
    document.body.appendChild(overlay);
  
    // Orientation check
    function checkOrientation() {
      // console.log('Checking orientation:', window.innerWidth, window.innerHeight);
      if (window.innerHeight > window.innerWidth) {
        overlay.style.display = 'flex';
        // console.log('Showing overlay (portrait mode)');
      } else {
        overlay.style.display = 'none';
        // console.log('Hiding overlay (landscape mode)');
      }
    }
  
    window.addEventListener('load', checkOrientation);
    window.addEventListener('resize', checkOrientation);
    window.addEventListener('orientationchange', checkOrientation);
  });
  