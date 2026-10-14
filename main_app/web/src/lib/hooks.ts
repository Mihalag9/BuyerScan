import { useCallback, useEffect, useState } from 'react';

/** Статус подключения к сети. */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);

  return online;
}

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

/** Установка PWA: кнопка для Android/Desktop + подсказка для iOS. */
export function usePwaInstall() {
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [iosHint, setIosHint] = useState(false);

  useEffect(() => {
    const standalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (navigator as unknown as { standalone?: boolean }).standalone === true;
    if (standalone) setInstalled(true);

    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const canAskDesktopInstall = !isIOS && !standalone;
    if (isIOS && !standalone) {
      // На iOS событие beforeinstallprompt не срабатывает — показываем инструкцию.
      setIosHint(true);
    }

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setInstallEvent(e as BeforeInstallPromptEvent);
      if (canAskDesktopInstall) setIosHint(false);
    };
    const onInstalled = () => {
      setInstalled(true);
      setInstallEvent(null);
      setIosHint(false);
    };

    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  const promptInstall = useCallback(async (): Promise<boolean> => {
    if (!installEvent) return false;
    await installEvent.prompt();
    const choice = await installEvent.userChoice;
    if (choice.outcome === 'accepted') setInstallEvent(null);
    return choice.outcome === 'accepted';
  }, [installEvent]);

  const dismissIosHint = useCallback(() => setIosHint(false), []);

  return { canInstall: installEvent !== null, promptInstall, iosHint, dismissIosHint, installed };
}
