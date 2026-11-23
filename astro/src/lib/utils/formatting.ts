/**
 * Formatuje kwotę jako walutę
 * @param amount - Kwota do sformatowania
 * @param currency - Kod waluty (domyślnie "PLN")
 * @returns Sformatowana kwota (np. "124.50 PLN")
 */
export function formatCurrency(
  amount: number | null | undefined,
  currency: string = 'PLN'
): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return `0.00 ${currency}`;
  }

  // Formatuj z 2 miejscami po przecinku
  const formatted = amount.toFixed(2);
  return `${formatted} ${currency}`;
}

/** Local calendar day for a date input. The UTC prefix can be the previous day. */
export function calendarDateInput(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

/** Noon in the local zone, so storing the value does not cross into another day. */
export function calendarDateToStored(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) {
    return value;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  return new Date(year, month - 1, day, 12, 0, 0, 0).toISOString();
}

/**
 * Formatuje datę do wyświetlenia
 * @param date - Data jako string ISO 8601 lub obiekt Date
 * @returns Sformatowana data (np. "15.01.2024")
 */

export function formatDate(date: string | Date): string {
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;

    if (isNaN(dateObj.getTime())) {
      // Jeśli data jest nieprawidłowa, zwróć pusty string lub fallback
      return '';
    }

    // Formatuj jako DD.MM.YYYY
    const day = dateObj.getDate().toString().padStart(2, '0');
    const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
    const year = dateObj.getFullYear();

    return `${day}.${month}.${year}`;
  } catch (error) {
    console.error('Error formatting date:', error);
    return '';
  }
}

/**
 * Oblicza trend (procentową zmianę) między dwiema wartościami
 * @param current - Bieżąca wartość
 * @param previous - Poprzednia wartość
 * @returns Dane trendu lub null jeśli nie można obliczyć (np. dzielenie przez zero)
 */
export function calculateTrend(
  current: number,
  previous: number
): { value: number; isPositive: boolean } | null {
  // Jeśli poprzednia wartość to 0, nie można obliczyć trendu
  if (previous === 0) {
    return null;
  }

  // Oblicz procentową zmianę
  const change = ((current - previous) / previous) * 100;
  const isPositive = change >= 0;

  return {
    value: Math.abs(change),
    isPositive,
  };
}

/**
 * Oblicza poprzedni miesiąc w formacie YYYY-MM
 * @param currentMonth - Bieżący miesiąc w formacie YYYY-MM (opcjonalnie)
 * @returns Poprzedni miesiąc w formacie YYYY-MM
 */
export function getPreviousMonth(currentMonth?: string): string {
  const now = currentMonth ? new Date(`${currentMonth}-01`) : new Date();
  const previousMonth = new Date(now);
  previousMonth.setMonth(previousMonth.getMonth() - 1);

  const year = previousMonth.getFullYear();
  const month = (previousMonth.getMonth() + 1).toString().padStart(2, '0');

  return `${year}-${month}`;
}

/**
 * Pobiera bieżący miesiąc w formacie YYYY-MM
 * @returns Bieżący miesiąc w formacie YYYY-MM
 */
export function getCurrentMonth(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = (now.getMonth() + 1).toString().padStart(2, '0');

  return `${year}-${month}`;
}

/**
 * Konwertuje kwotę (string/number) na number
 * @param amount - Kwota jako string lub number
 * @returns Liczba (number)
 */
export function parseAmount(amount: number | string | null | undefined): number {
  if (amount === null || amount === undefined) return 0;
  if (typeof amount === 'string') {
    const parsed = parseFloat(amount);
    return isNaN(parsed) ? 0 : parsed;
  }
  return amount;
}

/**
 * Formatuje nazwę sklepu, aby każdy wyraz rozpoczynał się od wielkiej litery
 * @param shopName - Nazwa sklepu do sformatowania
 * @returns Sformatowana nazwa sklepu (np. "Biedronka", "Dino Polska S.A.")
 */
export function formatShopName(shopName: string | null | undefined): string {
  if (!shopName) {
    return 'Nieznany sklep';
  }

  // Podziel na słowa i sformatuj każde słowo
  return shopName
    .split(/\s+/)
    .map((word) => {
      if (!word) return '';
      
      const trimmedWord = word.trim();
      const lowerWord = trimmedWord.toLowerCase();
      
      // Obsługa skrótów firmowych - pisane wielkimi literami
      if (lowerWord === 's.a.' || lowerWord === 'sa') {
        return 'S.A.';
      }
      if (lowerWord === 'sp.' || lowerWord === 'sp') {
        return 'Sp.';
      }
      if (lowerWord === 'z') {
        return 'Z';
      }
      if (lowerWord === 'o.' || lowerWord === 'o.o.' || lowerWord === 'oo') {
        return 'O.O.';
      }
      
      // Dla innych słów - pierwsza litera wielka, reszta mała
      return trimmedWord.charAt(0).toUpperCase() + trimmedWord.slice(1).toLowerCase();
    })
    .join(' ');
}
