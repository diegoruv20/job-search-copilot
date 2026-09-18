"use strict";

const assert = require("node:assert/strict");
const queueState = require("../../static/js/working_queue_state.js");

function storageWith(value = null) {
  return {
    value,
    getItem() { return this.value; },
    setItem(_key, next) { this.value = next; },
    removeItem() { this.value = null; },
  };
}

const validators = {
  workflow: value => ["focus", "all"].includes(value),
  text: value => typeof value === "string" && value.length <= 240,
  status: value => ["", "Applied"].includes(value),
  tier: value => ["", "Apply Next"].includes(value),
  archive: value => ["active", "archived", "all"].includes(value),
  sort: value => ["priority", "newest"].includes(value),
  advancedOpen: value => typeof value === "boolean",
  page: value => Number.isInteger(value) && value >= 1,
};

{
  const storage = storageWith();
  assert.deepEqual(queueState.read(storage, validators), {
    status: "absent",
    controls: null,
  });
}

{
  const storage = storageWith("{not json");
  assert.deepEqual(queueState.read(storage, validators), {
    status: "invalid",
    controls: null,
  });
}

{
  const storage = storageWith(JSON.stringify({
    version: queueState.STORAGE_VERSION - 1,
    controls: { text: "old" },
  }));
  assert.deepEqual(queueState.read(storage, validators), {
    status: "invalid",
    controls: null,
  });
}

{
  const storage = storageWith(JSON.stringify({
    version: queueState.STORAGE_VERSION,
    controls: { text: "platform", page: 0 },
  }));
  assert.equal(queueState.read(storage, validators).status, "invalid");
}

{
  const storage = storageWith(JSON.stringify({
    version: queueState.STORAGE_VERSION,
    controls: { text: "platform", notes: "must never be stored" },
  }));
  assert.equal(queueState.read(storage, validators).status, "invalid");
}

{
  const controls = {
    workflow: "focus",
    text: "platform",
    status: "Applied",
    tier: "Apply Next",
    archive: "active",
    sort: "priority",
    advancedOpen: true,
    page: 2,
  };
  const storage = storageWith();
  assert.equal(queueState.write(storage, controls, validators), true);
  assert.deepEqual(queueState.read(storage, validators), {
    status: "valid",
    controls,
  });
  assert.equal(JSON.parse(storage.value).jobs, undefined);
  assert.equal(JSON.parse(storage.value).notes, undefined);
}

{
  const unavailable = {
    getItem() { throw new Error("blocked"); },
    setItem() { throw new Error("blocked"); },
    removeItem() { throw new Error("blocked"); },
  };
  assert.equal(queueState.read(unavailable, validators).status, "unavailable");
  assert.equal(queueState.write(unavailable, { text: "" }, validators), false);
  assert.equal(queueState.clear(unavailable), false);
}

{
  let nextTimer = 0;
  const scheduled = new Map();
  const timers = {
    setTimeout(callback, delay) {
      nextTimer += 1;
      scheduled.set(nextTimer, { callback, delay });
      return nextTimer;
    },
    clearTimeout(timer) {
      scheduled.delete(timer);
    },
  };
  const calls = [];
  const debounce = queueState.createDebouncedTask(value => calls.push(value), undefined, timers);
  debounce.schedule("first");
  debounce.schedule("latest");
  assert.equal(scheduled.size, 1);
  const [timerId, pending] = [...scheduled.entries()][0];
  assert.equal(pending.delay, 150);
  scheduled.delete(timerId);
  pending.callback();
  assert.deepEqual(calls, ["latest"]);
  assert.equal(debounce.pending(), false);
  debounce.schedule("cancelled");
  debounce.cancel();
  assert.equal(scheduled.size, 0);
}

{
  const sequence = queueState.createRequestSequence();
  const stale = sequence.begin();
  const latest = sequence.begin();
  assert.equal(sequence.isCurrent(stale), false);
  assert.equal(sequence.isCurrent(latest), true);
}

console.log("Working Queue JavaScript tests passed.");
