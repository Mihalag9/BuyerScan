import { IconWifiOff } from './icons';

/** Баннер «нет соединения» поверх шапки, когда браузер офлайн. */
export function OfflineBanner() {
  return (
    <div className="banner banner-offline" role="alert">
      <IconWifiOff size={15} />
      <span>Нет подключения к интернету. Загрузка фото станет доступна после восстановления связи.</span>
    </div>
  );
}
