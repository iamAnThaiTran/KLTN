const KEY = 'shoeFinderSearchState';

export const saveSearchState = (state) => {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(state));
  } catch (e) {
    console.warn('[SessionStorage] Failed to save search state:', e);
  }
};

export const restoreSearchState = () => {
  try {
    const saved = sessionStorage.getItem(KEY);
    return saved ? JSON.parse(saved) : null;
  } catch (e) {
    console.warn('[SessionStorage] Failed to restore search state:', e);
    return null;
  }
};

export const clearSearchState = () => {
  try {
    sessionStorage.removeItem(KEY);
  } catch (e) {
    console.warn('[SessionStorage] Failed to clear search state:', e);
  }
};

/**
 * Merge extracted attributes (from backend parsing) with user-selected filter chips.
 * extracted : { brand: ["Nike"], color: ["Đen"] }
 * selected  : { "size:40": true }
 * returns   : { brand: ["Nike"], color: ["Đen"], size: ["40"] }
 */
export const mergeFilters = (extracted = {}, selected = {}) => {
  const merged = { ...extracted };
  Object.entries(selected).forEach(([key, _]) => {
    // selected keys are "attr:value" strings
    if (key.includes(':')) {
      const [attr, value] = key.split(':');
      if (!merged[attr]) merged[attr] = [];
      if (!merged[attr].includes(value)) merged[attr].push(value);
    }
  });
  return merged;
};