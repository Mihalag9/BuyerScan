import { IconDownload } from './icons';
import { usePwaInstall } from '../lib/hooks';
import { useToast } from './Toast';

/**
 * Кнопка установки PWA (Android/Desktop) + подсказка для iOS.
 * iOS: поделиться → «На экран «Домой»».
 */
export function InstallButton() {
  const { canInstall, promptInstall, iosHint, dismissIosHint, installed } = usePwaInstall();
  const { push } = useToast();

  if (installed) return null;

  if (canInstall) {
    return (
      <button
        className="btn btn-ghost"
        style={{ minHeight: 34, padding: '0 12px', fontSize: 13 }}
        onClick={async () => {
          const accepted = await promptInstall();
          if (accepted) push('success', 'Приложение установлено');
        }}
      >
        <IconDownload size={15} />
        Установить
      </button>
    );
  }

  if (iosHint) {
    return (
      <>
        <button
          className="btn btn-ghost"
          style={{ minHeight: 34, padding: '0 12px', fontSize: 13 }}
          onClick={() =>
            push(
              'info',
              'Нажмите Поделиться → «На экран «Домой»» — BuyerScan установится как приложение',
              { label: 'Понятно', onClick: dismissIosHint },
            )
          }
        >
          <IconDownload size={15} />
          iOS-установка
        </button>
      </>
    );
  }

  return null;
}
