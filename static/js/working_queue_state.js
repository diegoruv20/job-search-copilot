(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.WorkingQueueState = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const STORAGE_KEY = "job-search-copilot.working-queue.v1";
  const STORAGE_VERSION = 1;
  const TEXT_DEBOUNCE_MS = 150;

  function createDebouncedTask(callback, delay = TEXT_DEBOUNCE_MS, timers = globalThis) {
    let timer = null;

    return {
      schedule(...args) {
        if (timer !== null) timers.clearTimeout(timer);
        timer = timers.setTimeout(() => {
          timer = null;
          callback(...args);
        }, delay);
      },
      cancel() {
        if (timer !== null) timers.clearTimeout(timer);
        timer = null;
      },
      pending() {
        return timer !== null;
      },
    };
  }

  function createRequestSequence() {
    let sequence = 0;
    return {
      begin() {
        sequence += 1;
        return sequence;
      },
      isCurrent(requestId) {
        return requestId === sequence;
      },
    };
  }

  function validateStoredControls(controls, validators) {
    if (!controls || typeof controls !== "object" || Array.isArray(controls)) return null;
    const validated = {};
    for (const [key, value] of Object.entries(controls)) {
      if (!Object.prototype.hasOwnProperty.call(validators, key)) return null;
      if (!validators[key](value)) return null;
      validated[key] = value;
    }
    return validated;
  }

  function read(storage, validators) {
    let raw;
    try {
      raw = storage.getItem(STORAGE_KEY);
    } catch {
      return { status: "unavailable", controls: null };
    }
    if (raw === null) return { status: "absent", controls: null };

    try {
      const payload = JSON.parse(raw);
      if (
        !payload
        || typeof payload !== "object"
        || Array.isArray(payload)
        || payload.version !== STORAGE_VERSION
        || !Object.prototype.hasOwnProperty.call(payload, "controls")
      ) {
        return { status: "invalid", controls: null };
      }
      const controls = validateStoredControls(payload.controls, validators);
      return controls === null
        ? { status: "invalid", controls: null }
        : { status: "valid", controls };
    } catch {
      return { status: "invalid", controls: null };
    }
  }

  function write(storage, controls, validators) {
    const validated = validateStoredControls(controls, validators);
    if (validated === null) return false;
    try {
      storage.setItem(STORAGE_KEY, JSON.stringify({
        version: STORAGE_VERSION,
        controls: validated,
      }));
      return true;
    } catch {
      return false;
    }
  }

  function clear(storage) {
    try {
      storage.removeItem(STORAGE_KEY);
      return true;
    } catch {
      return false;
    }
  }

  return {
    STORAGE_KEY,
    STORAGE_VERSION,
    TEXT_DEBOUNCE_MS,
    clear,
    createDebouncedTask,
    createRequestSequence,
    read,
    write,
  };
});
