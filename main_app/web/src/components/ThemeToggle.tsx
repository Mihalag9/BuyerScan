import { IconAuto, IconMoon, IconSun } from './icons';
import { useTheme, type ThemeChoice } from '../lib/theme';

const CHOICES: { value: ThemeChoice; title: string; icon: typeof IconSun }[] = [
  { value: 'auto', title: 'Авто (как в системе)', icon: IconAuto },
  { value: 'light', title: 'Светлая тема', icon: IconSun },
  { value: 'dark', title: 'Тёмная тема', icon: IconMoon },
];

/** Переключатель темы: auto / light / dark с сохранением выбора. */
export function ThemeToggle() {
  const { choice, setChoice } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Тема оформления"
      style={{
        display: 'flex',
        gap: 2,
        padding: 3,
        borderRadius: 999,
        background: 'var(--bg-inset)',
        border: '1px solid var(--line)',
      }}
    >
      {CHOICES.map(({ value, title, icon: Ic }) => {
        const active = choice === value;
        return (
          <button
            key={value}
            role="radio"
            aria-checked={active}
            title={title}
            aria-label={title}
            onClick={() => setChoice(value)}
            style={{
              display: 'grid',
              placeItems: 'center',
              width: 30,
              height: 28,
              border: 0,
              borderRadius: 999,
              cursor: 'pointer',
              background: active ? 'var(--bg-elev)' : 'transparent',
              color: active ? 'var(--accent)' : 'var(--ink-3)',
              boxShadow: active ? 'var(--shadow-sm)' : 'none',
              transition: 'all var(--transition)',
            }}
          >
            <Ic size={15} />
          </button>
        );
      })}
    </div>
  );
}
