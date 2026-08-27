"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";

import {
  type Language,
  translate,
  type TranslationKey,
} from "@/lib/i18n";

export type Theme = "dark" | "light";

const LANGUAGE_STORAGE_KEY = "aew-language";
const THEME_STORAGE_KEY = "aew-theme";
const SIDEBAR_STORAGE_KEY = "aew-sidebar-collapsed";

type Preferences = {
  language: Language;
  theme: Theme;
  sidebarCollapsed: boolean;
};

type PreferencesContextValue = Preferences & {
  setLanguage: (language: Language) => void;
  toggleLanguage: () => void;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  t: (key: TranslationKey) => string;
};

const defaultPreferences: Preferences = {
  language: "en",
  theme: "dark",
  sidebarCollapsed: false,
};

let preferences = defaultPreferences;
let initialized = false;
const listeners = new Set<() => void>();

function readLanguage(): Language {
  const storedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return storedLanguage === "zh" || storedLanguage === "en"
    ? storedLanguage
    : "en";
}

function readTheme(): Theme {
  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (storedTheme === "dark" || storedTheme === "light") {
    return storedTheme;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function readSidebarCollapsed(): boolean {
  return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
}

function applyDocumentPreferences(nextPreferences: Preferences): void {
  document.documentElement.dataset.theme = nextPreferences.theme;
  document.documentElement.lang = nextPreferences.language;
}

function initializePreferences(): void {
  if (initialized || typeof window === "undefined") {
    return;
  }

  initialized = true;
  try {
    preferences = {
      language: readLanguage(),
      theme: readTheme(),
      sidebarCollapsed: readSidebarCollapsed(),
    };
  } catch {
    preferences = {
      language: "en",
      theme: window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light",
      sidebarCollapsed: false,
    };
  }
  applyDocumentPreferences(preferences);
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  initializePreferences();
  return () => listeners.delete(listener);
}

function getSnapshot(): Preferences {
  return preferences;
}

function getServerSnapshot(): Preferences {
  return defaultPreferences;
}

function updatePreferences(nextPreferences: Preferences): void {
  preferences = nextPreferences;
  applyDocumentPreferences(preferences);
  try {
    window.localStorage.setItem(
      LANGUAGE_STORAGE_KEY,
      preferences.language,
    );
    window.localStorage.setItem(THEME_STORAGE_KEY, preferences.theme);
    window.localStorage.setItem(
      SIDEBAR_STORAGE_KEY,
      String(preferences.sidebarCollapsed),
    );
  } catch {
    // Preferences remain active for this session when storage is unavailable.
  }
  listeners.forEach((listener) => listener());
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const current = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  );

  const setLanguage = useCallback((language: Language) => {
    updatePreferences({ ...preferences, language });
  }, []);
  const toggleLanguage = useCallback(() => {
    updatePreferences({
      ...preferences,
      language: preferences.language === "en" ? "zh" : "en",
    });
  }, []);
  const setTheme = useCallback((theme: Theme) => {
    updatePreferences({ ...preferences, theme });
  }, []);
  const toggleTheme = useCallback(() => {
    updatePreferences({
      ...preferences,
      theme: preferences.theme === "dark" ? "light" : "dark",
    });
  }, []);
  const toggleSidebar = useCallback(() => {
    updatePreferences({
      ...preferences,
      sidebarCollapsed: !preferences.sidebarCollapsed,
    });
  }, []);
  const t = useCallback(
    (key: TranslationKey) => translate(current.language, key),
    [current.language],
  );

  const value = useMemo(
    () => ({
      ...current,
      setLanguage,
      toggleLanguage,
      setTheme,
      toggleTheme,
      toggleSidebar,
      t,
    }),
    [
      current,
      setLanguage,
      setTheme,
      t,
      toggleLanguage,
      toggleSidebar,
      toggleTheme,
    ],
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): PreferencesContextValue {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error("usePreferences must be used within PreferencesProvider");
  }
  return context;
}
