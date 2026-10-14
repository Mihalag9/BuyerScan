import { useCallback, useState } from 'react';

export type ThemeChoice = 'auto' | 'light' | 'dark';

const STORAGE_KEY = 'tm-theme';

function readChoice(): ThemeChoice {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'light' || v === 'dark' || v === 'auto') return v;
  } catch {
    /* приватный режим — используем значение по умолчанию */
  }
  return 'auto';
}

function resolvedTheme(choice: ThemeChoice): 'light' | 'dark' {
  if (choice !== 'auto') return choice;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyChoice(choice: ThemeChoice) {
  document.documentElement.dataset.theme = resolvedTheme(choice);
  try {
    if (choice === 'auto') localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    /* игнорируем недоступное хранилище */
  }
}

/** Тема: auto следует за системой, light/dark сохраняются между сессиями. */
export function useTheme() {
  const [choice, setChoiceState] = useState<ThemeChoice>(readChoice);

  const setChoice = useCallback((next: ThemeChoice) => {
    setChoiceState(next);
    applyChoice(next);
  }, []);

  // В режиме auto реагируем на смену системной темы.
  useState(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', () => {
      if (readChoice() === 'auto') applyChoice('auto');
    });
  });

  return { choice, setChoice, resolved: resolvedTheme(choice) };
}
