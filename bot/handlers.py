import asyncio
import logging
from pathlib import Path

import aiofiles
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.keyboards import get_cancel_keyboard, get_download_keyboard, get_help_keyboard, get_main_keyboard
from bot.utils import FileManager, format_file_size, validate_excel_file
from config import Config
from processors.async_processor import ExcelProcessor, ProcessingProgress

router = Router()

# Store active processing tasks
active_tasks: dict[int, asyncio.Task] = {}


class ProcessingStates(StatesGroup):
    waiting_for_file = State()
    processing = State()


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    welcome_text = (
        "🤖 Добро пожаловать в бот проверки ККТ!\n\n"
        "Я помогу вам проверить валидность ККТ устройств в реестре ФНС.\n\n"
        "Выберите действие:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    welcome_text = (
        "🤖 Добро пожаловать в бот проверки ККТ!\n\n"
        "Я помогу вам проверить валидность ККТ устройств в реестре ФНС.\n\n"
        "Выберите действие:"
    )
    await callback.message.edit_text(welcome_text, reply_markup=get_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery) -> None:
    help_text = (
        "📋 Инструкция по использованию:\n\n"
        "1️⃣ Подготовьте Excel файл (.xlsx) с листом 'ККТ'\n"
        "2️⃣ Убедитесь, что файл содержит колонки:\n"
        "   • Наименование\n"
        "   • Модель ККТ\n"
        "   • Заводской Номер ККТ\n"
        "   • Статус Проверки\n\n"
        "3️⃣ Загрузите файл через бота\n"
        "4️⃣ Дождитесь окончания обработки\n"
        "5️⃣ Скачайте файл с результатами\n\n"
        "📊 Результаты проверки:\n"
        "🟢 УСПЕШНО - ККТ валидна\n"
        "🔴 НЕУСПЕШНО - ККТ не прошла проверку\n"
        "🟡 ОШИБКА - проблема при проверке\n\n"
    )
    await callback.message.edit_text(help_text, reply_markup=get_help_keyboard())
    await callback.answer()


@router.callback_query(F.data == "upload_file")
async def upload_file_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProcessingStates.waiting_for_file)

    upload_text = (
        "📎 Загрузите Excel файл для обработки\n\n"
        "Требования к файлу:\n"
        "• Формат: .xlsx или .xls\n"
        "• Размер: до 10 MB\n"
        "• Лист с названием 'ККТ'\n"
        "• Обязательные колонки: Наименование, Модель ККТ, Заводской Номер ККТ, Статус Проверки"
    )
    await callback.message.edit_text(upload_text)
    await callback.answer()


@router.message(ProcessingStates.waiting_for_file, F.document)
async def handle_document(message: Message, state: FSMContext, config: Config, file_manager: FileManager) -> None:
    document = message.document

    if not validate_excel_file(document, config):
        error_text = (
            "❌ Неподходящий файл!\n\n"
            "Требования:\n"
            "• Формат: .xlsx или .xls\n"
            f"• Размер: до {config.max_file_size_mb} MB\n"
            f"• Ваш файл: {document.file_name or 'без имени'} "
            f"({format_file_size(document.file_size or 0)})"
        )
        await message.reply(error_text)
        return

    try:
        # Download file
        file_info = await message.bot.get_file(document.file_id)
        file_content = await message.bot.download_file(file_info.file_path)

        # Save file
        file_id, file_path = await file_manager.save_document(document, file_content.read())

        # Validate file structure
        processor = ExcelProcessor(config)
        if not await processor.validate_file(file_path):
            await file_manager.cleanup_file(file_id)
            error_text = (
                "❌ Структура файла не соответствует требованиям!\n\n"
                "Убедитесь, что:\n"
                "• Есть лист с названием 'ККТ'\n"
                "• Присутствуют все обязательные колонки:\n"
                "  - Наименование\n"
                "  - Модель ККТ\n"
                "  - Заводской Номер ККТ\n"
                "  - Статус Проверки"
            )
            await message.reply(error_text)
            return

        await state.set_state(ProcessingStates.processing)
        await state.update_data(input_file_id=file_id)

        # Start processing
        progress_message = await message.reply("🔄 Начинаем обработку файла...", reply_markup=get_cancel_keyboard())

        # Create output file
        output_file_id, output_path = await file_manager.create_output_file(file_id)

        # Create and start processing task
        task = asyncio.create_task(
            process_file_task(
                processor,
                file_path,
                output_path,
                progress_message,
                message.from_user.id,
                output_file_id,
                file_manager,
                state,
            )
        )
        active_tasks[message.from_user.id] = task

    except Exception as e:
        logging.error(f"Error handling document: {e}")
        await message.reply("❌ Произошла ошибка при обработке файла. Попробуйте еще раз.")


async def process_file_task(
    processor: ExcelProcessor,
    input_path: Path,
    output_path: Path,
    progress_message: Message,
    user_id: int,
    output_file_id: str,
    file_manager: FileManager,
    state: FSMContext,
) -> None:
    try:
        last_update_time = 0
        update_interval = 2  # Update progress every 2 seconds

        async def update_progress(progress: ProcessingProgress) -> None:
            nonlocal last_update_time
            import time

            current_time = time.time()

            if current_time - last_update_time >= update_interval or progress.current == progress.total:
                last_update_time = current_time
                progress_text = (
                    f"🔄 Обработка файла...\n\n"
                    f"Прогресс: {progress.current}/{progress.total} ({progress.percentage:.1f}%)\n"
                    f"Текущий элемент: {progress.current_item}\n"
                )
                try:
                    await progress_message.edit_text(progress_text, reply_markup=get_cancel_keyboard())
                except Exception:
                    pass  # Message might be the same, ignore edit errors

        # Process the file
        await processor.process_file(input_path, output_path, update_progress)

        # File processing completed successfully
        success_text = "✅ Обработка завершена успешно!\n\nФайл готов к скачиванию."
        await progress_message.edit_text(success_text, reply_markup=get_download_keyboard(output_file_id))

    except asyncio.CancelledError:
        await progress_message.edit_text("❌ Обработка отменена пользователем.")
        
        # Send main menu after cancellation
        welcome_text = (
            "🤖 Добро пожаловать в бот проверки ККТ!\n\n"
            "Я помогу вам проверить валидность ККТ устройств в реестре ФНС.\n\n"
            "Выберите действие:"
        )
        await progress_message.answer(welcome_text, reply_markup=get_main_keyboard())

    except Exception as e:
        logging.error(f"Error during file processing: {e}")
        error_text = f"❌ Произошла ошибка при обработке:\n{str(e)}"
        await progress_message.edit_text(error_text)

    finally:
        # Clean up task
        active_tasks.pop(user_id, None)
        await state.clear()


@router.callback_query(F.data == "cancel_processing")
async def cancel_processing_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    task = active_tasks.get(user_id)

    if task and not task.done():
        task.cancel()
        await callback.message.edit_text("⏹️ Отменяем обработку...")
        await callback.answer("Обработка отменяется...")
    else:
        await callback.answer("Нет активной обработки для отмены")


@router.callback_query(F.data.startswith("download_"))
async def download_handler(callback: CallbackQuery, file_manager: FileManager) -> None:
    file_id = callback.data.replace("download_", "")
    file_path = file_manager.get_file_path(file_id)

    if not file_path or not file_path.exists():
        await callback.answer("❌ Файл не найден или был удален")
        return

    try:
        async with aiofiles.open(file_path, "rb") as file:
            file_content = await file.read()

        document = BufferedInputFile(file_content, filename=f"{file_id}.xlsx")

        await callback.message.reply_document(document, caption="📋 Результат обработки ККТ файла")

        # Edit the original message to remove the "обработать новый файл" button
        await callback.message.edit_text(
            "✅ Обработка завершена успешно!",
            reply_markup=None
        )

        # Cleanup file after sending
        await file_manager.cleanup_file(file_id)
        await callback.answer("✅ Файл отправлен!")

        # Send main menu as a new message after successful download
        welcome_text = (
            "🤖 Добро пожаловать в бот проверки ККТ!\n\n"
            "Я помогу вам проверить валидность ККТ устройств в реестре ФНС.\n\n"
            "Выберите действие:"
        )
        await callback.message.answer(welcome_text, reply_markup=get_main_keyboard())

    except Exception as e:
        logging.error(f"Error sending file: {e}")
        await callback.answer("❌ Ошибка при отправке файла")


@router.message(ProcessingStates.waiting_for_file)
async def handle_invalid_file(message: Message) -> None:
    await message.reply(
        "❌ Пожалуйста, отправьте Excel файл (.xlsx или .xls)\n\nИли нажмите /start для возврата в главное меню."
    )
