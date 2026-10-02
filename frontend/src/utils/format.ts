/** Format a decimal string without converting its integer part through JS Number. */
export function formatDecimalAmount(
  value: string | number | null | undefined,
  locale = 'es-CO',
): string {
  if (value == null || (typeof value === 'string' && value.trim() === '')) return '—';

  const raw = String(value).trim();
  const match = raw.match(/^([+-]?)(\d+)(?:\.(\d+))?$/);
  if (!match) {
    return typeof value === 'number' && Number.isFinite(value)
      ? new Intl.NumberFormat(locale, { maximumFractionDigits: 20 }).format(value)
      : raw;
  }

  const [, sign, integerPart, fractionPart] = match;
  const normalizedInteger = integerPart.replace(/^0+(?=\d)/, '');
  const integer = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(BigInt(normalizedInteger));
  const decimalSeparator = new Intl.NumberFormat(locale)
    .formatToParts(1.1)
    .find((part) => part.type === 'decimal')?.value ?? '.';
  const signPrefix = sign === '-' ? '-' : sign === '+' ? '+' : '';
  return fractionPart ? `${signPrefix}${integer}${decimalSeparator}${fractionPart}` : `${signPrefix}${integer}`;
}
