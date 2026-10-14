// Account-private persistence adapter. Central handler/storage wiring is owner02/03.
export function createIntakeHistory({store, entryModel, authorize, sourceAllowed, clock}) {
  if (typeof store?.transaction !== 'function' || typeof entryModel?.createIntakeEntry !== 'function' ||
      typeof entryModel?.partitionIntakeEntries !== 'function' || typeof authorize !== 'function' ||
      typeof sourceAllowed !== 'function' || typeof clock !== 'function') throw Error('Intake dependencies required');
  function id(value) {
    if (typeof value !== 'string' || !value.trim() || value.length > 200) throw Error('Invalid intake scope ID');
    return value;
  }
  async function access(session, accountId, action, consentId, memberId) {
    const result = await authorize({session, accountId, action, consentId, memberId});
    if (result?.allowed !== true || result.accountId !== accountId) throw Error('Intake access denied');
    if (action !== 'revoke' && consentId &&
        (result.consent?.id !== consentId || result.consent?.purpose !== 'intake-recording' || result.consent?.granted !== true)) {
      throw Error('Current intake consent required');
    }
    return result;
  }
  async function sources(entry, auth) {
    const refs = [entry.food, ...(entry.kind === 'substitution' ? [entry.substitution.planned, entry.substitution.actual] : [])];
    for (const ref of refs) {
      if (await sourceAllowed(structuredClone(ref), structuredClone(auth)) !== true) return false;
    }
    return true;
  }
  function state(value) {
    const result = value == null ? {version: 1, entries: [], revokedConsentIds: []} : structuredClone(value);
    if (result.version !== 1 || !Array.isArray(result.entries) || result.entries.length > 1000 ||
        !Array.isArray(result.revokedConsentIds) || result.revokedConsentIds.length > 1000) throw Error('Invalid intake store');
    result.revokedConsentIds.forEach(id);
    return result;
  }
  return {
    async append({session, accountId, input}) {
      id(accountId);
      // Capture request before awaits; account/consent are resolved by trusted auth.
      const draft = structuredClone(input);
      if (draft.accountId !== accountId) throw Error('Intake account mismatch');
      id(draft.consent?.id);
      return store.transaction(accountId, async current => {
        const next = state(current);
        const auth = await access(session, accountId, 'append', draft.consent.id, draft.memberId);
        if (next.revokedConsentIds.includes(draft.consent.id)) throw Error('Intake consent revoked');
        const entry = entryModel.createIntakeEntry({...draft, accountId, consent: auth.consent}, {accountId, clock});
        if (!await sources(entry, auth)) throw Error('Intake source permission required');
        if (next.entries.some(e => e.id === entry.id)) throw Error('Duplicate intake event');
        if (next.entries.length >= 1000) throw Error('Intake history full');
        next.entries.push(entry);
        return {state: next, result: structuredClone(entry)};
      });
    },
    async read({session, accountId}) {
      id(accountId);
      return store.transaction(accountId, async current => {
        await access(session, accountId, 'read');
        const next = state(current), visible = [];
        // Validate all records before selecting; never silently drop foreign data.
        if (next.entries.some(e => e.accountId !== accountId)) throw Error('Foreign intake record in account store');
        entryModel.partitionIntakeEntries(next.entries, {accountId});
        for (const entry of next.entries) {
          if (next.revokedConsentIds.includes(entry.consent.id)) continue;
          const auth = await access(session, accountId, 'read', entry.consent.id, entry.memberId);
          if (await sources(entry, auth)) visible.push(entry);
        }
        return {state: next, result: entryModel.partitionIntakeEntries(visible, {accountId})};
      });
    },
    async revoke({session, accountId, consentId}) {
      id(accountId); id(consentId);
      return store.transaction(accountId, async current => {
        await access(session, accountId, 'revoke', consentId);
        const next = state(current);
        if (!next.revokedConsentIds.includes(consentId)) {
          if (next.revokedConsentIds.length >= 1000) throw Error('Revocation ledger full');
          next.revokedConsentIds.push(consentId);
        }
        const oldLength = next.entries.length;
        next.entries = next.entries.filter(e => e.consent.id !== consentId);
        return {state: next, result: {removed: oldLength - next.entries.length}};
      });
    },
  };
}
