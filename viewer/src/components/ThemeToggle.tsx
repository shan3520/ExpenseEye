import { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';
import { cn } from '@/lib/utils';

type Theme = 'light' | 'dark';

/** Read the theme the FOUC-prevention script already applied in index.html. */
function currentTheme(): Theme {
  if (typeof document !== 'undefined' && document.documentElement.classList.contains('light')) {
    return 'light';
  }
  return 'dark';
}

/**
 * Light/dark switch. The active theme is a `.light` class on <html>; an inline
 * script in index.html applies it before paint (saved choice → system pref).
 * This component keeps it in sync and persists the user's choice.
 */
export function ThemeToggle({ withLabel = false, className }: { withLabel?: boolean; className?: string }) {
  const [theme, setTheme] = useState<Theme>(currentTheme);

  useEffect(() => {
    const isLight = theme === 'light';
    document.documentElement.classList.toggle('light', isLight);
    try {
      localStorage.setItem('theme', theme);
    } catch {
      /* storage unavailable — theme still applies for the session */
    }
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', isLight ? '#f1f4f9' : '#05080e');
  }, [theme]);

  const toggle = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'));
  const Icon = theme === 'light' ? Moon : Sun;
  const next = theme === 'light' ? 'dark' : 'light';
  const label = `Switch to ${next} mode`;

  if (withLabel) {
    return (
      <button
        type="button"
        onClick={toggle}
        className={cn(
          'flex min-h-11 w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-txt-muted transition-colors hover:bg-tint-2 hover:text-txt cursor-pointer',
          className
        )}
      >
        <Icon className="h-4 w-4" />
        <span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      className={cn(
        'flex h-9 w-9 items-center justify-center rounded-md text-txt-faint transition-colors hover:bg-tint-2 hover:text-txt cursor-pointer',
        className
      )}
    >
      <Icon className="h-[18px] w-[18px]" />
    </button>
  );
}
