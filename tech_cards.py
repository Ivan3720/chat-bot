import os
import subprocess
import tempfile
import pandas as pd


FOOD_TOP_LEVEL_FOLDERS = {"десерты", "блюда"}
DIRECT_CARD_FOLDERS = {"десерты"}


def _norm(value):
    """Нормализует текст для поиска: регистр, пробелы и знаки препинания."""
    text = str(value).strip().lower()
    for char in ".:,;":
        text = text.replace(char, " ")
    return " ".join(text.split())


def _relative_parts(path, base_path="cards"):
    """Возвращает части пути внутри cards: ['Блюда', 'Супы'] и т.п."""
    rel_path = os.path.relpath(path, base_path)
    if rel_path == ".":
        return []
    return [part for part in rel_path.split(os.sep) if part]


def get_subfolders(path="cards"):
    """Возвращает список подпапок для навигации.

    Раздел "Блюда" НЕ исключаем: в нём должны показываться подпапки
    "Горячие блюда", "Супы", "Завтраки", "Салаты" и т.п.
    Раздел "десерты" оставляем прямым списком техкарт, как было раньше.
    """
    current_folder_name = os.path.basename(path).lower()

    if current_folder_name in DIRECT_CARD_FOLDERS:
        return []

    if not os.path.exists(path):
        return []

    return sorted(
        name
        for name in os.listdir(path)
        if os.path.isdir(os.path.join(path, name)) and name != "__MACOSX"
    )


def get_categories():
    """Возвращает список всех папок внутри директории cards."""
    folder_path = "cards"
    categories = []
    if not os.path.exists(folder_path):
        return categories
    for name in os.listdir(folder_path):
        full_path = os.path.join(folder_path, name)
        if os.path.isdir(full_path) and name != "__MACOSX":
            categories.append(name)
    return categories


def _read_card_file(file_path, filename):
    """Читает csv/xlsx/xls в DataFrame.

    Для старых .xls сначала пробуем pandas + xlrd. Если xlrd не установлен,
    пробуем конвертацию через LibreOffice, если он есть в системе.
    """
    if filename.endswith(".csv"):
        return pd.read_csv(file_path, sep=None, engine="python", header=None)

    try:
        return pd.read_excel(file_path, header=None)
    except ImportError as exc:
        if not filename.endswith(".xls"):
            raise

        # Fallback для старых .xls без установленного xlrd.
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                subprocess.run(
                    [
                        "libreoffice",
                        "--headless",
                        "--convert-to",
                        "xlsx",
                        "--outdir",
                        tmp_dir,
                        file_path,
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                raise ImportError(
                    "Для чтения .xls установите пакет xlrd: pip install xlrd"
                ) from exc

            converted_name = os.path.splitext(os.path.basename(filename))[0] + ".xlsx"
            converted_path = os.path.join(tmp_dir, converted_name)
            if not os.path.exists(converted_path):
                raise ImportError(
                    "Не удалось прочитать .xls. Установите xlrd: pip install xlrd"
                ) from exc

            return pd.read_excel(converted_path, header=None)


def load_all_cards():
    """Сканирует папку cards и формирует базу техкарт."""
    database = {}
    folder_path = "cards"

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return database

    for root, dirs, files in os.walk(folder_path):
        # Не сканируем служебные папки macOS.
        dirs[:] = [d for d in dirs if d != "__MACOSX"]

        rel_parts = _relative_parts(root, folder_path)
        if not rel_parts:
            continue

        top_category = rel_parts[0]
        category = rel_parts[-1]
        top_category_lower = top_category.lower()
        category_path = " / ".join(rel_parts)
        category_path_lower = category_path.lower()

        for filename in files:
            if filename.startswith("._") or filename == ".DS_Store":
                continue

            file_path = os.path.join(root, filename)

            if filename.endswith((".csv", ".xlsx", ".xls")):
                try:
                    df = _read_card_file(file_path, filename)

                    # Имя по умолчанию из названия файла.
                    card_name = filename.rsplit(".", 1)[0].replace("-", " ")
                    start_row = 0
                    col_idx_name = 0
                    col_idx_unit = 1
                    col_idx_netto = 2

                    # 1. Поиск заголовков и названия внутри файла.
                    for i, row in df.iterrows():
                        row_vals_clean = [_norm(val) for val in row.values]

                        # В разных файлах может быть "Наименование:" или "Наименование".
                        for idx, val in enumerate(row_vals_clean):
                            if val == "наименование" and idx + 1 < len(row.values):
                                possible_name = str(row.values[idx + 1]).strip()
                                possible_name_norm = _norm(possible_name)
                                if possible_name and possible_name.lower() not in {"nan", "none"}:
                                    # Не берем заголовок таблицы вместо названия блюда.
                                    if possible_name_norm not in {"ед изм", "нетто", "брутто", "№"}:
                                        card_name = possible_name

                        # Поиск начала таблицы: Наименование + Ед изм.
                        if "наименование" in row_vals_clean and "ед изм" in row_vals_clean:
                            start_row = i + 1
                            for idx, val in enumerate(row_vals_clean):
                                if val == "наименование":
                                    col_idx_name = idx
                                if val == "ед изм":
                                    col_idx_unit = idx
                                if "нетто" in val:
                                    col_idx_netto = idx
                            break

                    # 2. Сборка текста техкарты.
                    content = f"📖 {card_name.upper()}\n"
                    content += f"📁 Категория: {category}\n"
                    content += f"📂 Раздел: {category_path}\n"
                    content += f"🔎 Разделы для поиска: {top_category} | {category} | {category_path}\n"
                    content += "\n🛒 СОСТАВ:\n"

                    for i in range(start_row, len(df)):
                        row = df.iloc[i]
                        product_raw = (
                            str(row[col_idx_name]).strip()
                            if col_idx_name < len(row) and pd.notna(row[col_idx_name])
                            else ""
                        )

                        if not product_raw or product_raw.lower() in [
                            "nan",
                            "наименование",
                            "none",
                        ]:
                            continue

                        # Обработка выхода продукта.
                        if "выход" in product_raw.lower():
                            amount_out = (
                                str(row[col_idx_netto]).strip()
                                if col_idx_netto < len(row) and pd.notna(row[col_idx_netto])
                                else "?"
                            )
                            content += f"\n⚖️ Итоговый выход: {amount_out}"
                            break

                        product_clean = " ".join(product_raw.replace("-", "").split())

                        # Для еды показываем только компоненты без граммовок.
                        if top_category_lower in FOOD_TOP_LEVEL_FOLDERS:
                            content += f"• {product_clean}\n"
                        else:
                            unit = (
                                str(row[col_idx_unit]).strip()
                                if col_idx_unit < len(row) and pd.notna(row[col_idx_unit])
                                else ""
                            )
                            amount = (
                                str(row[col_idx_netto]).strip()
                                if col_idx_netto < len(row) and pd.notna(row[col_idx_netto])
                                else ""
                            )
                            content += f"• {product_clean} — {amount} {unit}\n"

                    key = card_name.strip().lower()
                    # Если названия случайно повторяются в разных разделах, не затираем старую техкарту.
                    if key in database:
                        key = f"{key} ({category_path_lower})"
                    database[key] = content

                except Exception as e:
                    print(f"Ошибка в файле {filename}: {e}")

    print(f"✅ Загружено техкарт: {len(database)}")
    return database
