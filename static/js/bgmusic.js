function initBackgroundMusic() {
    const bodyBgmAttr = document.body.getAttribute('data-bgm');
    let bgMusicSrc = '/static/sfx/default.mp3';
    let bgMusic = document.getElementById('bg-music'); // check if exists
    let volumeSlider = document.getElementById('volume');
    let sfxVolumeSlider = document.getElementById('sfx-volume');
    let isBgmMuted = false;
    let previousBgmVolume = 50;  // Default volume 50%
    let sfxVolume = 1;
    let isSfxMuted = false;

    // Load saved settings
    const savedBgmVolume = localStorage.getItem('bgmVolume');
    const savedBgmMute = localStorage.getItem('bgmMuted');
    const savedSfxVolume = localStorage.getItem('sfxVolume');
    const savedSfxMute = localStorage.getItem('sfxMuted');

    if (savedBgmVolume !== null) {
        previousBgmVolume = parseInt(savedBgmVolume, 10);
        if (!isNaN(previousBgmVolume) && volumeSlider) {
            volumeSlider.value = previousBgmVolume;
        }
    }
    if (savedBgmMute === 'true') {
        isBgmMuted = true;
    }
    if (savedSfxVolume !== null) {
        sfxVolume = parseFloat(savedSfxVolume);
        if (!isNaN(sfxVolume) && sfxVolumeSlider) {
            sfxVolumeSlider.value = sfxVolume * 100;
        }
    }
    if (savedSfxMute === 'true') {
        isSfxMuted = true;
    }

    // Determine bgMusicSrc based on attribute or URL param
    if (bodyBgmAttr === 'dynamic') {
        const urlParams = new URLSearchParams(window.location.search);
        const selectedMap = urlParams.get('map') || 'multiplication';
        const mapMusicSources = {
            multiplication: '/static/bgm/multiplication.mp3',
            addition: '/static/bgm/addition.mp3',
            subtraction: '/static/bgm/subtraction.mp3',
            division: '/static/bgm/division.mp3',
            counting: '/static/bgm/counting.mp3',
            comparison: '/static/bgm/comparison.mp3',
            numerals: '/static/bgm/numerals.mp3',
            placevalue: '/static/bgm/placevalue.mp3'
        };
        bgMusicSrc = mapMusicSources[selectedMap] || '/static/sfx/default.mp3';
    } else if (bodyBgmAttr) {
        bgMusicSrc = bodyBgmAttr;
    }

    // Create bgMusic element if missing
    if (!bgMusic) {
        bgMusic = document.createElement('audio');
        bgMusic.id = 'bg-music';
        bgMusic.loop = true;
        bgMusic.autoplay = false;
        document.body.appendChild(bgMusic);
    }

    // Update source and volume
    if (bgMusic.src !== bgMusicSrc) {
        bgMusic.src = bgMusicSrc;
    }
    bgMusic.volume = isBgmMuted ? 0 : previousBgmVolume / 100;

    // Setup volume sliders listeners only once
    if (!initBackgroundMusic.volumeListenersAdded) {
        if (volumeSlider) {
            volumeSlider.addEventListener('input', () => {
                if (isBgmMuted) return;
                const value = volumeSlider.value;
                const volume = value / 100;
                bgMusic.volume = volume;
                localStorage.setItem('bgmVolume', value);
            });
        }
        if (sfxVolumeSlider) {
            sfxVolumeSlider.addEventListener('input', () => {
                if (isSfxMuted) return;
                sfxVolume = sfxVolumeSlider.value / 100;
                localStorage.setItem('sfxVolume', sfxVolume);
            });
        }
        initBackgroundMusic.volumeListenersAdded = true;
    }

    // New: Play background music only after first user interaction
    function playBackgroundMusicOnInteraction() {
        function playMusic() {
            bgMusic.play().catch(err => {
                console.warn('Autoplay blocked even after interaction:', err);
            });
            window.removeEventListener('click', playMusic);
            window.removeEventListener('keydown', playMusic);
            window.removeEventListener('touchstart', playMusic);
        }
        window.addEventListener('click', playMusic);
        window.addEventListener('keydown', playMusic);
        window.addEventListener('touchstart', playMusic);
    }

    if (bgMusic.paused) {
        playBackgroundMusicOnInteraction();
    }

    // Setup mute checkbox listeners only once
    if (!initBackgroundMusic.muteListenersAdded) {
        const muteCheckbox = document.getElementById("muteCheckbox");
        if (muteCheckbox) {
            muteCheckbox.checked = isBgmMuted;
            muteCheckbox.addEventListener('change', function (e) {
                if (e.target.checked) {
                    bgMusic.volume = 0;
                    isBgmMuted = true;
                } else {
                    bgMusic.volume = volumeSlider.value / 100;
                    isBgmMuted = false;
                }
                localStorage.setItem('bgmMuted', isBgmMuted);
            });
        }

        const sfxMuteCheckbox = document.getElementById("sfxMuteCheckbox");
        if (sfxMuteCheckbox) {
            sfxMuteCheckbox.checked = isSfxMuted;
            sfxMuteCheckbox.addEventListener('change', function (e) {
                isSfxMuted = e.target.checked;
                localStorage.setItem('sfxMuted', isSfxMuted);
            });
        }
        initBackgroundMusic.muteListenersAdded = true;
    }
}

// Initialize on page load
window.addEventListener('load', initBackgroundMusic);

// Handle page show from bfcache (e.g. back button)
window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        const bgMusic = document.getElementById('bg-music');
        if (bgMusic && bgMusic.paused) {
            bgMusic.play().catch(err => console.warn('Autoplay blocked:', err));
        }
    }
});

// Global sound functions (can keep or adapt as needed)
window.playSound = function (src, delay = 0) {
    const sfxVolumeSlider = document.getElementById('sfx-volume');
    let isSfxMuted = false;
    if (sfxVolumeSlider) {
        isSfxMuted = sfxVolumeSlider.disabled || sfxVolumeSlider.value === 0;
    }
    if (isSfxMuted) return;
    setTimeout(() => {
        const sound = new Audio(src);
        sound.volume = sfxVolumeSlider ? sfxVolumeSlider.value / 100 : 1;
        sound.play();
    }, delay);
};

window.muteBgMusic = function () {
    const bgMusic = document.getElementById('bg-music');
    if (bgMusic) bgMusic.muted = true;
};

window.unmuteBgMusic = function () {
    const bgMusic = document.getElementById('bg-music');
    if (bgMusic) bgMusic.muted = false;
};

window.toggleBgMusic = function () {
    const bgMusic = document.getElementById('bg-music');
    if (bgMusic) bgMusic.muted = !bgMusic.muted;
};

window.toggleSfxMute = function () {
    // Implement your SFX mute toggle here if needed
};
