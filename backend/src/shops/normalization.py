"""
Moduł standaryzacji danych sklepów.

Zapewnia transformację nazw sklepów i adresów do "złotego standardu":
- shop_name: lowercase, trim, bez cudzysłowów, znormalizowane białe znaki
- address: lowercase, trim, bez przecinków, znormalizowany skrót ul., bez średników
"""

import re


def normalize_shop_name(name: str) -> str:
    """
    Standaryzuje nazwę sklepu do złotego standardu.

    Transformacje:
    - lowercase (zamiana na małe litery)
    - trim (usunięcie białych znaków na początku i końcu)
    - usunięcie cudzysłowów (pojedynczych i podwójnych)
    - normalizacja białych znaków (wiele spacji → jedna spacja)

    Args:
        name: Nazwa sklepu do znormalizowania

    Returns:
        Znormalizowana nazwa sklepu (pusty string jeśli name był pusty/None)

    Examples:
        >>> normalize_shop_name("DINO POLSKA S.A.")
        'dino polska s.a.'
        >>> normalize_shop_name('"POIN" SP.Z O.O.')
        'poin sp.z o.o.'
        >>> normalize_shop_name("  ALDI  ")
        'aldi'
        >>> normalize_shop_name("ALDI Sp. z o.o.")
        'aldi sp. z o.o.'
    """
    if not name:
        return ""

    # lowercase
    normalized = name.lower()

    # trim
    normalized = normalized.strip()

    # usunięcie cudzysłowów (pojedynczych i podwójnych)
    normalized = normalized.replace('"', "").replace("'", "")

    # normalizacja białych znaków (wiele spacji/tabulacji → jedna spacja)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def normalize_shop_address(address: str | None) -> str | None:
    """
    Standaryzuje adres sklepu do złotego standardu.

    Format docelowy: ul. Ulica Numer budynku (lub bez numeru) 00-000 Poczta (lub bez poczty)

    Transformacje:
    - lowercase (zamiana na małe litery)
    - trim (usunięcie białych znaków na początku i końcu)
    - usunięcie przecinków
    - normalizacja skrótu ul. (UL., Ul., ulica, os., al., pl. → ul.)
    - usunięcie średników (wielokrotne adresy - bierzemy tylko pierwszy)
    - wymuszenie odpowiedniej kolejności: ul. Ulica Numer 00-000 Miasto
    - normalizacja białych znaków (wiele spacji → jedna spacja)

    Args:
        address: Adres sklepu do znormalizowania (może być None)

    Returns:
        Znormalizowany adres sklepu lub None jeśli address był None/pusty po normalizacji

    Examples:
        >>> normalize_shop_address("UL. Akacjowa 1, 62-023 Gądki")
        'ul. akacjowa 1 62-023 gądki'
        >>> normalize_shop_address("ul. Ostrowska 122, 63-700 Krotoszyn; ul. Starołęcka 219, 61-341 Poznań")
        'ul. ostrowska 122 63-700 krotoszyn'
        >>> normalize_shop_address("ul. Starołęcka 219, 61-341 Poznań")
        'ul. starołęcka 219 61-341 poznań'
        >>> normalize_shop_address("61-249 poznań os. stare żegrze 36")
        'ul. stare żegrze 36 61-249 poznań'
        >>> normalize_shop_address("ul. armii krajowej 101 60-370 poznań")
        'ul. armii krajowej 101 60-370 poznań'
        >>> normalize_shop_address(None)
        None
        >>> normalize_shop_address("   ")
        None
    """
    if not address:
        return None

    # lowercase
    normalized = address.lower()

    # trim
    normalized = normalized.strip()

    # Jeśli są średniki (wielokrotne adresy), weź tylko pierwszy
    if ";" in normalized:
        normalized = normalized.split(";")[0].strip()

    # Usunięcie przecinków
    normalized = normalized.replace(",", "")

    # Normalizacja białych znaków (wiele spacji/tabulacji → jedna spacja)
    normalized = re.sub(r"\s+", " ", normalized)

    # Trim końcowy
    normalized = normalized.strip()

    # Jeśli po podstawowej normalizacji adres jest pusty, zwróć None
    if not normalized:
        return None

    # Parsowanie i reorganizacja adresu do formatu: ul. Ulica Numer 00-000 Miasto
    normalized = _reorder_address_components(normalized)

    return normalized


def _reorder_address_components(address: str) -> str:
    """
    Reorganizuje komponenty adresu do standardowej kolejności.

    Format docelowy: ul. Ulica Numer budynku 00-000 Poczta

    Wyciąga i układa komponenty:
    - Skrót ulicy (ul., os., al., pl., ulica → ul.)
    - Nazwa ulicy
    - Numer budynku
    - Kod pocztowy (XX-XXX)
    - Miasto

    Args:
        address: Adres po podstawowej normalizacji (lowercase, bez przecinków)

    Returns:
        Adres w standardowej kolejności: ul. Ulica Numer 00-000 Miasto
    """
    # Wzorce do wyciągnięcia komponentów
    postal_code_pattern = r"\b(\d{2}-\d{3})\b"  # XX-XXX
    street_prefix_pattern = r"\b(ul|ul\.|ulica|os|os\.|osiedle|al|al\.|aleja|pl|pl\.|plac)\b\.?"  # Skróty ulic

    # Wyciągnij kod pocztowy
    postal_code_match = re.search(postal_code_pattern, address)
    postal_code = postal_code_match.group(1) if postal_code_match else None

    # Wyciągnij skrót ulicy
    street_prefix_match = re.search(street_prefix_pattern, address, re.IGNORECASE)
    street_prefix = None
    if street_prefix_match:
        prefix = street_prefix_match.group(1).lower()
        # Normalizacja wszystkich skrótów do "ul."
        if prefix in ["ul", "ul.", "ulica"]:
            street_prefix = "ul."
        elif prefix in ["os", "os.", "osiedle"]:
            street_prefix = "ul."  # osiedle → ul.
        elif prefix in ["al", "al.", "aleja"]:
            street_prefix = "ul."  # aleja → ul.
        elif prefix in ["pl", "pl.", "plac"]:
            street_prefix = "ul."  # plac → ul.

    # Wyciągnij miasto (słowo przed lub po kodzie pocztowym)
    city = None
    if postal_code:
        # Miasto może być przed lub po kodzie pocztowym
        parts = address.split(postal_code)

        # Sprawdź część po kodzie pocztowym (częstszy przypadek)
        if len(parts) > 1 and parts[1].strip():
            after_postal = parts[1].strip()
            # Pierwsze słowo/słowa po kodzie pocztowym to zazwyczaj miasto
            # Ale może być też skrót ulicy, więc szukamy pierwszego słowa które nie jest skrótem
            words_after = after_postal.split()
            for word in words_after:
                # Jeśli słowo nie jest skrótem ulicy i nie jest liczbą, to może być miasto
                if not re.match(
                    street_prefix_pattern, word, re.IGNORECASE
                ) and not re.match(r"^\d+[a-z]?$", word):
                    # To może być miasto - weź to słowo i ewentualnie następne (dla wielowyrazowych nazw miast)
                    city_start_idx = words_after.index(word)
                    # Miasto może być wielowyrazowe, ale zwykle to 1-2 słowa
                    city_words = []
                    for i in range(
                        city_start_idx, min(city_start_idx + 2, len(words_after))
                    ):
                        if not re.match(r"^\d+[a-z]?$", words_after[i]):
                            city_words.append(words_after[i])
                        else:
                            break
                    if city_words:
                        city = " ".join(city_words)
                        break

        # Sprawdź część przed kodem pocztowym (jeśli nie znaleziono wcześniej)
        if not city and len(parts) > 0 and parts[0].strip():
            before_postal = parts[0].strip()
            words_before = before_postal.split()
            if words_before:
                # Ostatnie słowo przed kodem pocztowym może być miastem
                potential_city = words_before[-1]
                if not re.match(r"^\d+[a-z]?$", potential_city) and not re.match(
                    street_prefix_pattern, potential_city, re.IGNORECASE
                ):
                    city = potential_city

    # Usuń kod pocztowy, skrót ulicy i miasto z adresu, aby wyodrębnić resztę
    temp_address = address

    if postal_code:
        temp_address = re.sub(postal_code_pattern, "", temp_address)

    if street_prefix_match:
        # Usuń skrót ulicy (z kropką lub bez)
        temp_address = re.sub(
            street_prefix_pattern, "", temp_address, flags=re.IGNORECASE
        )

    if city:
        # Usuń miasto z temp_address
        temp_address = re.sub(
            r"\b" + re.escape(city) + r"\b", "", temp_address, flags=re.IGNORECASE
        )

    # Normalizacja białych znaków po usunięciu komponentów
    temp_address = re.sub(r"\s+", " ", temp_address).strip()

    # Jeśli nie znaleziono miasta i nie ma kodu pocztowego, spróbuj znaleźć jako ostatnie słowo
    if not city and temp_address:
        words = temp_address.split()
        # Ostatnie słowo może być miastem (jeśli nie jest liczbą i nie jest skrótem ulicy)
        if words:
            potential_city = words[-1]
            if not re.match(r"^\d+[a-z]?$", potential_city) and not re.match(
                street_prefix_pattern, potential_city, re.IGNORECASE
            ):
                # Jeśli jest mało słów, ostatnie może być miastem
                if len(words) <= 3:
                    city = potential_city
                    temp_address = " ".join(words[:-1]).strip()

    # temp_address zawiera teraz: nazwa ulicy + numer budynku (lub odwrotnie)
    # Wyciągnij numer budynku (ostatnia liczba w temp_address)
    street_name = temp_address
    building_number = None

    # Wzorzec: numer może być na końcu lub po nazwie ulicy
    number_match = re.search(r"\b(\d+[a-z]?)\s*$", temp_address)
    if number_match:
        building_number = number_match.group(1)
        # Usuń numer z nazwy ulicy
        street_name = re.sub(
            r"\s*" + re.escape(building_number) + r"\s*$", "", temp_address
        ).strip()

    # Jeśli nie znaleziono numeru na końcu, spróbuj znaleźć po nazwie ulicy
    if not building_number and street_name:
        # Wzorzec: nazwa ulicy, potem numer
        name_number_match = re.match(r"^(.+?)\s+(\d+[a-z]?)\s*$", street_name)
        if name_number_match:
            street_name = name_number_match.group(1).strip()
            building_number = name_number_match.group(2)

    # Buduj adres w standardowej kolejności
    parts = []

    # 1. Skrót ulicy (domyślnie "ul." jeśli nie znaleziono, ale jest nazwa ulicy)
    if street_prefix:
        parts.append(street_prefix)
    elif street_name:
        parts.append("ul.")  # Domyślny skrót jeśli nie znaleziono

    # 2. Nazwa ulicy
    if street_name:
        parts.append(street_name)

    # 3. Numer budynku
    if building_number:
        parts.append(building_number)

    # 4. Kod pocztowy
    if postal_code:
        parts.append(postal_code)

    # 5. Miasto
    if city:
        parts.append(city)

    # Jeśli nie udało się wyodrębnić komponentów, zwróć oryginalny adres z normalizacją skrótu ul.
    if not parts or (len(parts) == 1 and parts[0] == "ul."):
        # Fallback: podstawowa normalizacja skrótu ul.
        normalized = re.sub(
            r"\b(ul|ul\.|ulica|os|os\.|osiedle|al|al\.|aleja|pl|pl\.|plac)\b\.?",
            "ul.",
            address,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    result = " ".join(parts)

    # Finalna normalizacja białych znaków
    result = re.sub(r"\s+", " ", result).strip()

    return result
