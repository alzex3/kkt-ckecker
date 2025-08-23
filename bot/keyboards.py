from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Инструкция", callback_data="help")],
            [InlineKeyboardButton(text="📊 Загрузить файл Excel", callback_data="upload_file")],
        ]
    )
    return keyboard


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить обработку", callback_data="cancel_processing")],
        ]
    )
    return keyboard


def get_download_keyboard(file_id: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 Скачать результат", callback_data=f"download_{file_id}")],
            [InlineKeyboardButton(text="📊 Обработать новый файл", callback_data="upload_file")],
        ]
    )
    return keyboard


def get_help_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")],
        ]
    )
    return keyboard
