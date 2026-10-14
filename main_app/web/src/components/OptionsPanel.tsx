interface OptionsPanelProps {
  useBrowser: boolean;
  onUseBrowser: (v: boolean) => void;
  doCutout: boolean;
  onDoCutout: (v: boolean) => void;
  purchasePrice: number;
  onPurchasePrice: (v: number) => void;
  variantCount: number;
  onVariantCount: (v: number) => void;
}

export function OptionsPanel({
  useBrowser,
  onUseBrowser,
  doCutout,
  onDoCutout,
  purchasePrice,
  onPurchasePrice,
  variantCount,
  onVariantCount,
}: OptionsPanelProps) {
  return (
    <div className="options" role="group" aria-label="Параметры анализа">
      <label className="switch">
        <input
          type="checkbox"
          checked={useBrowser}
          onChange={(e) => onUseBrowser(e.target.checked)}
        />
        <span className="switch-track" />
        WB через браузер
      </label>

      <label className="switch">
        <input
          type="checkbox"
          checked={doCutout}
          onChange={(e) => onDoCutout(e.target.checked)}
        />
        <span className="switch-track" />
        Вырезать фон
      </label>

      <label className="field-inline">
        Закупка, ₽
        <input
          className="input input-number"
          type="number"
          min={0}
          step={10}
          value={purchasePrice || ''}
          placeholder="0"
          onChange={(e) => onPurchasePrice(Math.max(0, parseFloat(e.target.value) || 0))}
        />
      </label>

      <label className="field-inline">
        Вариантов
        <select
          className="select"
          value={variantCount}
          onChange={(e) => onVariantCount(parseInt(e.target.value, 10))}
        >
          {[4, 6, 8, 12, 16].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
