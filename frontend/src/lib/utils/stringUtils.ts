export function safeString(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number' && isNaN(value)) return '';
  const str = String(value);
  return str === 'nan' || str === 'NaN' || str === 'undefined' || str === 'null' ? '' : str;
}

export function isEmptyOrInvalid(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === 'number' && isNaN(value)) return true;
  const str = String(value).trim().toLowerCase();
  return str === '' || str === 'nan' || str === 'undefined' || str === 'null';
}

export function cleanProductName(name: string): string {
  return safeString(name).replace(/-F$/, '');
}

export function extractAfterSeparator(text: string, separator: string): string {
  const parts = safeString(text).split(separator);
  return parts.length > 1 ? parts[1].trim() : parts[0].trim();
}

export function formatOrderMark(prefix: string, note: string | null | undefined, separator: string): string {
  const cleanNote = safeString(note);
  if (!cleanNote) return prefix;
  return `${prefix}${separator}${cleanNote}`;
}

export function extractProductMark(productCode: string): string {
  const parts = safeString(productCode).split('-');
  return parts.length >= 3 ? `-${parts[2]}` : '';
}
