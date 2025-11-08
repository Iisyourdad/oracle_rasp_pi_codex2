(function () {
  function focusableSelector() {
    return '.virtual-keyboard-target';
  }

  function isInteractiveInput(element) {
    return element && (element.matches?.(focusableSelector()));
  }

  function setCaret(input, position) {
    if (typeof input.setSelectionRange === 'function') {
      input.setSelectionRange(position, position);
    }
  }

  function updateValue(input, start, end, text) {
    const value = input.value || '';
    const before = value.slice(0, start);
    const after = value.slice(end);
    input.value = `${before}${text}${after}`;
    const newPos = start + text.length;
    setCaret(input, newPos);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }

  document.addEventListener('DOMContentLoaded', function () {
    const keyboard = document.getElementById('onscreen-keyboard');
    if (!keyboard) {
      return;
    }

    const alphabetPanel = keyboard.querySelector('#alphabet-panel');
    const symbolsPanel = keyboard.querySelector('#symbols-panel');
    const toggleSymbolsBtn = keyboard.querySelector('#toggle-symbols-btn');
    const toggleAlphabetBtn = keyboard.querySelector('#toggle-alphabet-btn');
    const shiftBtn = keyboard.querySelector('.shift-btn');
    const alphabetKeys = Array.from(keyboard.querySelectorAll('#alphabet-panel .key'));

    alphabetKeys.forEach((key) => {
      if (!key.dataset.original) {
        key.dataset.original = key.textContent;
      }
    });

    let activeInput = null;
    let isShiftActive = false;

    document.addEventListener('focusin', function (event) {
      if (isInteractiveInput(event.target)) {
        activeInput = event.target;
        keyboard.style.display = 'block';
      }
    });

    keyboard.addEventListener('mousedown', function (event) {
      if (event.target.classList.contains('key')) {
        event.preventDefault();
      }
    });

    function ensureActiveInput() {
      if (!activeInput || !document.body.contains(activeInput)) {
        activeInput = null;
      }
      return activeInput;
    }

    function getSelectionRange(input) {
      const start = input.selectionStart ?? input.value.length;
      const end = input.selectionEnd ?? start;
      return { start, end };
    }

    function hideKeyboard() {
      keyboard.style.display = 'none';
    }

    function applyShiftState(enabled) {
      isShiftActive = enabled;
      if (shiftBtn) {
        shiftBtn.classList.toggle('shift-active', enabled);
      }
      alphabetKeys.forEach((key) => {
        if (key === shiftBtn || key.dataset.original === undefined) {
          return;
        }
        const original = key.dataset.original;
        key.textContent = enabled ? original.toUpperCase() : original.toLowerCase();
      });
    }

    function insertText(text) {
      const input = ensureActiveInput();
      if (!input) {
        return;
      }
      const { start, end } = getSelectionRange(input);
      updateValue(input, start, end, text);
      input.focus({ preventScroll: true });
    }

    function handleBackspace() {
      const input = ensureActiveInput();
      if (!input) {
        return;
      }
      const { start, end } = getSelectionRange(input);
      if (start === end && start > 0) {
        updateValue(input, start - 1, end, '');
      } else if (start !== end) {
        updateValue(input, start, end, '');
      }
      input.focus({ preventScroll: true });
    }

    function handleKeyPress(keyElement) {
      const key = keyElement.dataset.key || keyElement.textContent;
      const normalized = key.toLowerCase();

      if (normalized === 'hide keyboard') {
        hideKeyboard();
        return;
      }
      if (normalized === 'backspace') {
        handleBackspace();
        return;
      }
      if (normalized === 'space') {
        insertText(' ');
        return;
      }
      if (keyElement === shiftBtn) {
        applyShiftState(!isShiftActive);
        return;
      }
      insertText(key);
      if (isShiftActive) {
        applyShiftState(false);
      }
    }

    alphabetKeys.forEach((keyElement) => {
      keyElement.addEventListener('click', function () {
        if (this.id === 'toggle-symbols-btn') {
          return;
        }
        handleKeyPress(this);
      });
    });

    keyboard.querySelectorAll('#symbols-panel .key').forEach((keyElement) => {
      keyElement.addEventListener('click', function () {
        if (this.id === 'toggle-alphabet-btn') {
          return;
        }
        handleKeyPress(this);
      });
    });

    if (toggleSymbolsBtn && alphabetPanel && symbolsPanel) {
      toggleSymbolsBtn.addEventListener('click', function () {
        alphabetPanel.style.display = 'none';
        symbolsPanel.style.display = 'block';
      });
    }

    if (toggleAlphabetBtn && alphabetPanel && symbolsPanel) {
      toggleAlphabetBtn.addEventListener('click', function () {
        symbolsPanel.style.display = 'none';
        alphabetPanel.style.display = 'block';
      });
    }

    (function enableDrag() {
      let dragging = false;
      let startX = 0;
      let startY = 0;
      let originX = 0;
      let originY = 0;

      keyboard.addEventListener('mousedown', function (event) {
        if (event.target.classList.contains('key')) {
          return;
        }
        dragging = true;
        startX = event.clientX;
        startY = event.clientY;
        originX = keyboard.offsetLeft;
        originY = keyboard.offsetTop;
        event.preventDefault();
      });

      document.addEventListener('mousemove', function (event) {
        if (!dragging) {
          return;
        }
        const deltaX = event.clientX - startX;
        const deltaY = event.clientY - startY;
        keyboard.style.left = `${originX + deltaX}px`;
        keyboard.style.top = `${originY + deltaY}px`;
        keyboard.style.bottom = 'auto';
        keyboard.style.transform = 'none';
      });

      document.addEventListener('mouseup', function () {
        dragging = false;
      });
    })();
  });
})();
