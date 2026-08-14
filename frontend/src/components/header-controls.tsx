"use client";

import { usePreferences } from "@/components/preferences-provider";

function SunIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      className="h-4 w-4"
    >
      <circle cx="12" cy="12" r="3.5" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      className="h-4 w-4"
    >
      <path d="M20.5 15.5A8.5 8.5 0 0 1 8.5 3.5a8.5 8.5 0 1 0 12 12Z" />
    </svg>
  );
}

export function HeaderControls() {
  const { language, theme, t, toggleLanguage, toggleTheme } = usePreferences();

  return (
    <div className="flex shrink-0 items-center gap-2">
      <button
        type="button"
        className="control-button"
        aria-label={
          language === "en"
            ? t("preferences.switchToChinese")
            : t("preferences.switchToEnglish")
        }
        onClick={toggleLanguage}
      >
        {language === "en" ? "中" : "EN"}
      </button>
      <button
        type="button"
        className="control-button"
        aria-label={
          theme === "dark"
            ? t("preferences.switchToLight")
            : t("preferences.switchToDark")
        }
        onClick={toggleTheme}
      >
        {theme === "dark" ? <SunIcon /> : <MoonIcon />}
      </button>
    </div>
  );
}
