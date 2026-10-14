import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react';
import { fileSize } from '../lib/format';
import { IconCamera, IconClose, IconPlus, IconUpload } from './icons';
import { useToast } from './Toast';

const MAX_BYTES = 15 * 1024 * 1024;
const ACCEPTED = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']);

interface DropzoneProps {
  file: File | null;
  onFile: (file: File | null) => void;
  disabled?: boolean;
}

/** Дропзона: drag&drop, выбор файла, камера, валидация, превью. */
export function Dropzone({ file, onFile, disabled }: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [dragover, setDragover] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const { push } = useToast();

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const validate = useCallback(
    (f: File): boolean => {
      if (!ACCEPTED.has(f.type) && !/\.(jpe?g|png|webp|heic|heif)$/i.test(f.name)) {
        push('error', 'Поддерживаются JPG, PNG, WebP и HEIC');
        return false;
      }
      if (f.size > MAX_BYTES) {
        push('error', `Файл ${fileSize(f.size)} — максимум 15 МБ`);
        return false;
      }
      if (f.size === 0) {
        push('error', 'Файл пустой');
        return false;
      }
      return true;
    },
    [push],
  );

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const f = files?.[0];
      if (!f) return;
      if (validate(f)) onFile(f);
    },
    [onFile, validate],
  );

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragover(false);
      if (disabled) return;
      handleFiles(e.dataTransfer.files);
    },
    [disabled, handleFiles],
  );

  // Вставка из буфера обмена (Ctrl+V).
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      if (disabled) return;
      const item = Array.from(e.clipboardData?.items ?? []).find((i) =>
        i.type.startsWith('image/'),
      );
      const f = item?.getAsFile();
      if (f) handleFiles([f] as unknown as FileList);
    };
    document.addEventListener('paste', onPaste);
    return () => document.removeEventListener('paste', onPaste);
  }, [disabled, handleFiles]);

  const openPicker = () => !disabled && inputRef.current?.click();
  const openCamera = () => !disabled && cameraRef.current?.click();

  return (
    <div
      className={`dropzone ${dragover ? 'dragover' : ''}`}
      onClick={openPicker}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && openPicker()}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragover(true);
      }}
      onDragLeave={() => setDragover(false)}
      onDrop={onDrop}
      role="button"
      tabIndex={0}
      aria-label="Выбрать фото товара"
      style={disabled ? { opacity: 0.6, cursor: 'default' } : undefined}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/heic"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={(e) => handleFiles(e.target.files)}
      />

      {file && previewUrl ? (
        <div className="preview" onClick={(e) => e.stopPropagation()}>
          <img src={previewUrl} alt="Превью товара" />
          <div className="preview-meta">
            <span>{file.name}</span>
            <span>·</span>
            <span>{fileSize(file.size)}</span>
          </div>
          <div className="dropzone-actions">
            <button
              className="btn btn-ghost"
              style={{ minHeight: 34, fontSize: 13 }}
              onClick={() => onFile(null)}
            >
              <IconClose size={14} />
              Удалить
            </button>
            <button
              className="btn btn-ghost"
              style={{ minHeight: 34, fontSize: 13 }}
              onClick={openPicker}
            >
              <IconPlus size={14} />
              Заменить
            </button>
            <button
              className="btn btn-ghost"
              style={{ minHeight: 34, fontSize: 13 }}
              onClick={openCamera}
            >
              <IconCamera size={14} />
              Камера
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="dropzone-icon">
            <IconUpload size={24} />
          </div>
          <strong>Перетащи фото сюда или нажми для выбора</strong>
          <small>JPG · PNG · WebP · HEIC — до 15 МБ. Можно вставить из буфера (Ctrl+V)</small>
          <div className="dropzone-actions" onClick={(e) => e.stopPropagation()}>
            <button
              className="btn btn-primary"
              style={{ minHeight: 38 }}
              onClick={openPicker}
            >
              <IconUpload size={15} />
              Выбрать файл
            </button>
            <button
              className="btn btn-ghost"
              style={{ minHeight: 38 }}
              onClick={openCamera}
            >
              <IconCamera size={15} />
              Снять на камеру
            </button>
          </div>
        </>
      )}
    </div>
  );
}
