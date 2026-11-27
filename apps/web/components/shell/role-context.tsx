'use client';

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from 'react';
import type { UserRole } from '@/lib/navigation';

interface RoleContextValue {
  readonly role: UserRole;
  readonly setRole: (nextRole: UserRole) => void;
  readonly isOnline: boolean;
}

const RoleContext = createContext<RoleContextValue | null>(null);
const STORAGE_KEY = 'smart-catering:fs01-role-preview';
const ROLE_EVENT = 'smart-catering:role-change';

function subscribeRole(callback: () => void): () => void {
  window.addEventListener('storage', callback);
  window.addEventListener(ROLE_EVENT, callback);
  return () => {
    window.removeEventListener('storage', callback);
    window.removeEventListener(ROLE_EVENT, callback);
  };
}

function getRoleSnapshot(): UserRole {
  try {
    const saved = window.sessionStorage.getItem(STORAGE_KEY);
    if (saved === 'ADMIN' || saved === 'STAFF') {
      return saved;
    }
  } catch {
    // Ignore storage access errors in restricted browsers.
  }
  return 'ADMIN';
}

function getServerRoleSnapshot(): UserRole {
  return 'ADMIN';
}

function subscribeOnline(callback: () => void): () => void {
  window.addEventListener('online', callback);
  window.addEventListener('offline', callback);
  return () => {
    window.removeEventListener('online', callback);
    window.removeEventListener('offline', callback);
  };
}

function getOnlineSnapshot(): boolean {
  return window.navigator.onLine;
}

function getServerOnlineSnapshot(): boolean {
  return true;
}

export function RoleProvider({ children }: { readonly children: ReactNode }) {
  const role = useSyncExternalStore(subscribeRole, getRoleSnapshot, getServerRoleSnapshot);
  const isOnline = useSyncExternalStore(
    subscribeOnline,
    getOnlineSnapshot,
    getServerOnlineSnapshot,
  );

  const setRole = useCallback((nextRole: UserRole) => {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, nextRole);
    } catch {
      // Ignore storage access errors in restricted browsers.
    }
    window.dispatchEvent(new Event(ROLE_EVENT));
  }, []);

  const value = useMemo<RoleContextValue>(
    () => ({ role, setRole, isOnline }),
    [role, setRole, isOnline],
  );

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useAppRole(): RoleContextValue {
  const ctx = useContext(RoleContext);
  if (!ctx) {
    throw new Error('useAppRole must be used within RoleProvider');
  }
  return ctx;
}
