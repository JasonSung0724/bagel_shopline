export function formatDateToYYYYMMDD(orderTime: string | Date | null | undefined): string {
  if (!orderTime) return 'INVALID_DATE';

  try {
    let date: Date;

    if (orderTime instanceof Date) {
      date = orderTime;
    } else if (typeof orderTime === 'string') {
      const cleanedTime = orderTime.trim();

      if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(cleanedTime)) {
        date = new Date(cleanedTime.replace(' ', 'T'));
      } else if (/^\d{4}-\d{2}-\d{2}$/.test(cleanedTime)) {
        date = new Date(cleanedTime + 'T00:00:00');
      } else if (/^\d{4}\/\d{2}\/\d{2}$/.test(cleanedTime)) {
        date = new Date(cleanedTime.replace(/\//g, '-') + 'T00:00:00');
      } else {
        date = new Date(cleanedTime);
      }
    } else {
      return 'INVALID_DATE';
    }

    if (isNaN(date.getTime())) {
      return 'INVALID_DATE';
    }

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    return `${year}${month}${day}`;
  } catch {
    return 'INVALID_DATE';
  }
}

export function getCurrentDateYYYYMMDD(): string {
  return formatDateToYYYYMMDD(new Date());
}

export function isValidDateString(dateStr: string): boolean {
  return dateStr !== 'INVALID_DATE' && dateStr.length === 8;
}
