import json
from tech_cards import get_categories


def start_keyboard():
    """Создает кнопки самого верхнего уровня"""
    buttons = [
        [{"action": {"type": "text", "label": "📖 Меню"}, "color": "primary"}],
        [{"action": {"type": "text", "label": "📝 Тесты"}, "color": "primary"}],
        [
            {
                "action": {"type": "text", "label": "ℹ️ Общая информация"},
                "color": "primary",
            }
        ],
    ]
    # ensure_ascii=False важен для корректного отображения кириллицы
    return json.dumps({"one_time": False, "buttons": buttons}, ensure_ascii=False)


def create_folders_keyboard(folders):
    """Клавиатура для навигации по папкам"""
    buttons = []

    # Кнопки для самих папок (каждая на новой строке для ширины)
    for folder in folders:
        buttons.append(
            [{"action": {"type": "text", "label": folder}, "color": "positive"}]
        )

    # Кнопка возврата на один уровень вверх
    buttons.append(
        [{"action": {"type": "text", "label": "⬅️ Назад"}, "color": "secondary"}]
    )

    # НОВАЯ КНОПКА: Прямой выход в самое начало
    buttons.append(
        [{"action": {"type": "text", "label": "🏠 В начало"}, "color": "secondary"}]
    )

    return json.dumps({"one_time": False, "buttons": buttons}, ensure_ascii=False)


def main_keyboard():
    # Получаем папки: Напитки, Блюда, Десерты
    categories = get_categories()
    buttons = []
    current_row = []

    for cat in categories:
        button = {
            "action": {"type": "text", "label": cat},
            "color": "positive",
        }
        current_row.append(button)
        if len(current_row) == 2:  # По 2 кнопки в ряд
            buttons.append(current_row)
            current_row = []

    if current_row:
        buttons.append(current_row)

    # Добавляем кнопку возврата в самое начало, если нужно
    buttons.append(
        [{"action": {"type": "text", "label": "Главное меню"}, "color": "secondary"}]
    )

    return json.dumps({"one_time": False, "buttons": buttons}, ensure_ascii=False)
