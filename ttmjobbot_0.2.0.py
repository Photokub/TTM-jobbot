import logging
import time
import os
import io
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

# Включаем детальное логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Состояния для разговора
CHOOSING_MEDIA_TYPE = 1
WAITING_FOR_MEDIA = 2
WAITING_FOR_CAPTION = 3
PREVIEW_POST = 4
EDIT_POST = 5
WAITING_FOR_NEW_CAPTION = 6
WAITING_FOR_URL = 7

# Константы для типов медиа
PHOTO = 'photo'
VIDEO = 'video'
DOCUMENT = 'doc'

# Путь к изображению по умолчанию
DEFAULT_IMAGE_PATH = os.path.join('images', 'default_image.jpg')
DEFAULT_IMAGE_FILE_ID = None  # Сюда будет сохранен file_id изображения по умолчанию

# ID канала (замените на ваш)
CHANNEL_ID = "-1002309808938"  # наш тестовый канал
# CHANNEL_ID = "-1002481490079"  # чистовой канал

# Хранилище для данных постов
posts_data = {}
reactions = {}

def get_post_buttons(post_id, include_edit=False):
    logger.debug(f"Creating buttons for post_id: {post_id}, include_edit: {include_edit}")
    
    # Получаем данные поста
    post_data = None
    for user_data in posts_data.values():
        if user_data.get('post_id') == post_id:
            post_data = user_data
            break
    
    hh_url = "https://hh.ru/"  # URL по умолчанию
    if post_data and 'hh_url' in post_data:
        hh_url = post_data['hh_url']
    
    # Кнопки для взаимодействия с прямым URL для чата с рекрутером
    recruiter_username = "Liia4"
    chat_url = f"https://t.me/{recruiter_username}"
    
    buttons = [[
        InlineKeyboardButton("💬 Чат с рекрутером", url=chat_url),
        InlineKeyboardButton("🔍 Откликнуться на hh", url=hh_url)
    ]]
    
    if include_edit:
        edit_buttons = [
            InlineKeyboardButton("✏️ Редактировать", callback_data=f'edit_{post_id}'),
            InlineKeyboardButton("✅ Опубликовать", callback_data=f'publish_{post_id}')
        ]
        buttons.append(edit_buttons)
        logger.debug(f"Added edit buttons: {edit_buttons}")
    
    return InlineKeyboardMarkup(buttons)

async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started new post creation")
    
    keyboard = [
        [
            InlineKeyboardButton("📷 Фото", callback_data='type_photo'),
            InlineKeyboardButton("🎥 Видео", callback_data='type_video'),
            InlineKeyboardButton("📄 Документ", callback_data='type_doc')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Очищаем предыдущие данные пользователя
    if user_id in posts_data:
        del posts_data[user_id]
    
    await update.message.reply_text(
        "Выберите тип медиафайла для публикации:",
        reply_markup=reply_markup
    )
    return CHOOSING_MEDIA_TYPE

async def media_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    media_type = query.data.split('_')[1]
    context.user_data['media_type'] = media_type
    logger.info(f"User {user_id} selected media type: {media_type}")
    
    media_messages = {
        'photo': "Выберите источник фото:",
        'video': "Отправьте видео",
        'doc': "Отправьте документ"
    }
    
    if media_type == 'photo':
        if DEFAULT_IMAGE_FILE_ID:
            keyboard = [
                [InlineKeyboardButton("Использовать фото по умолчанию", callback_data='use_default_image')],
                [InlineKeyboardButton("Загрузить свое фото", callback_data='upload_own_image')],
                [InlineKeyboardButton("Вернуться к выбору типа медиа", callback_data='back_to_media_type')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(media_messages[media_type], reply_markup=reply_markup)
            return CHOOSING_MEDIA_TYPE
        else:
            await query.message.edit_text("Отправьте фото")
            return WAITING_FOR_MEDIA
    else:
        await query.message.edit_text(media_messages[media_type])
        return WAITING_FOR_MEDIA

async def handle_default_image_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    choice = query.data
    
    if choice == 'use_default_image':
        # Пользователь выбрал изображение по умолчанию
        logger.info(f"User {user_id} chose to use default image")
        
        # Создаем пост с изображением по умолчанию
        post_id = f"post_{user_id}_{int(time.time())}"
        posts_data[user_id] = {
            'media_type': PHOTO,
            'file_id': DEFAULT_IMAGE_FILE_ID,
            'post_id': post_id
        }
        
        await query.message.edit_text("Отправьте подпись к публикации или используйте /skip для публикации без подписи")
        return WAITING_FOR_CAPTION
    
    elif choice == 'upload_own_image':
        # Пользователь выбрал загрузить свое изображение
        logger.info(f"User {user_id} chose to upload own image")
        await query.message.edit_text("Отправьте фото")
        return WAITING_FOR_MEDIA
    
    return CHOOSING_MEDIA_TYPE

async def load_default_image(context):
    global DEFAULT_IMAGE_FILE_ID
    
    try:
        # Проверяем, существует ли файл
        if not os.path.exists(DEFAULT_IMAGE_PATH):
            logger.error(f"Default image not found at path: {DEFAULT_IMAGE_PATH}")
            return
            
        # Открываем и читаем изображение
        with open(DEFAULT_IMAGE_PATH, 'rb') as img_file:
            img_bytes = img_file.read()
        
        # Отправляем изображение через API и получаем file_id
        message = await context.bot.send_photo(
            chat_id=context.bot.id,  # Отправляем боту
            photo=io.BytesIO(img_bytes)
        )
        
        DEFAULT_IMAGE_FILE_ID = message.photo[-1].file_id
        logger.info(f"Default image loaded with file_id: {DEFAULT_IMAGE_FILE_ID}")
    except Exception as e:
        logger.error(f"Failed to load default image: {str(e)}") 

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    media_type = context.user_data.get('media_type')
    logger.info(f"Handling media from user {user_id}, type: {media_type}")
    
    try:
        if media_type == PHOTO and update.message.photo:
            file_id = update.message.photo[-1].file_id
        elif media_type == VIDEO and update.message.video:
            file_id = update.message.video.file_id
        elif media_type == DOCUMENT and update.message.document:
            file_id = update.message.document.file_id
        else:
            await update.message.reply_text("Неверный тип медиафайла. Попробуйте снова с /post")
            return ConversationHandler.END

        post_id = f"post_{user_id}_{int(time.time())}"
        posts_data[user_id] = {
            'media_type': media_type,
            'file_id': file_id,
            'post_id': post_id,
            'message_id': update.message.message_id
        }
        logger.debug(f"Stored post data: {posts_data[user_id]}")
        
        await update.message.reply_text(
            "Отправьте подпись к публикации или используйте /skip для публикации без подписи"
        )
        return WAITING_FOR_CAPTION
        
    except Exception as e:
        logger.error(f"Error handling media: {str(e)}")
        await update.message.reply_text("Произошла ошибка при обработке медиафайла. Попробуйте снова.")
        return ConversationHandler.END

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Handling caption from user {user_id}")
    
    if user_id not in posts_data:
        logger.error(f"User {user_id} not found in posts_data")
        await update.message.reply_text("Произошла ошибка. Начните сначала с /post")
        return ConversationHandler.END
    
    posts_data[user_id]['caption'] = update.message.text
    logger.debug(f"Added caption to post: {posts_data[user_id]}")
    
    # Запрашиваем URL для кнопки
    await update.message.reply_text(
        "Отправьте URL вакансии на hh.ru для кнопки 'Откликнуться на hh' или используйте /skip для стандартной ссылки"
    )
    return WAITING_FOR_URL

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Handling URL from user {user_id}")
    
    if user_id not in posts_data:
        logger.error(f"User {user_id} not found in posts_data")
        await update.message.reply_text("Произошла ошибка. Начните сначала с /post")
        return ConversationHandler.END
    
    url = update.message.text.strip()
    # Базовая проверка URL
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    
    posts_data[user_id]['hh_url'] = url
    logger.debug(f"Added URL to post: {posts_data[user_id]}")
    return await preview_post(update, context)

async def skip_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} skipped URL")
    posts_data[user_id]['hh_url'] = 'https://hh.ru/'
    return await preview_post(update, context)

async def skip_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} skipped caption")
    posts_data[user_id]['caption'] = ''
    
    # Запрашиваем URL для кнопки
    await update.message.reply_text(
        "Отправьте URL вакансии на hh.ru для кнопки 'Откликнуться на hh' или используйте /skip для стандартной ссылки"
    )
    return WAITING_FOR_URL

async def preview_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Generating preview for user {user_id}")
    logger.info(f"Current posts_data: {posts_data}")
    
    if user_id not in posts_data:
        logger.error("User data not found")
        await update.effective_message.reply_text("Ошибка: данные поста не найдены")
        return ConversationHandler.END
    
    try:
        post_data = posts_data[user_id]
        logger.debug(f"Preview post data: {post_data}")
        
        if post_data['media_type'] == PHOTO:
            sent_message = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=post_data['file_id'],
                caption=post_data.get('caption', ''),
                reply_markup=get_post_buttons(post_data['post_id'], include_edit=True)
            )
        elif post_data['media_type'] == VIDEO:
            sent_message = await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=post_data['file_id'],
                caption=post_data.get('caption', ''),
                reply_markup=get_post_buttons(post_data['post_id'], include_edit=True)
            )
        else:
            sent_message = await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=post_data['file_id'],
                caption=post_data.get('caption', ''),
                reply_markup=get_post_buttons(post_data['post_id'], include_edit=True)
            )
        
        # Сохраняем ID сообщения предпросмотра
        posts_data[user_id]['preview_message_id'] = sent_message.message_id
        
        await update.effective_message.reply_text(
            "👆 Так будет выглядеть ваш пост. Вы можете отредактировать подпись или опубликовать пост."
        )
        return PREVIEW_POST
        
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        await update.effective_message.reply_text(f"Ошибка при создании предпросмотра: {str(e)}")
        return ConversationHandler.END

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    logger.info(f"Button callback from user {user_id}: {query.data}")
    
    try:
        # Добавляем проверку на тип кнопки
        if query.data.startswith('type_'):
            # Обработка выбора типа медиа
            return await media_type_callback(update, context)
            
        # Безопасное разделение данных
        data_parts = query.data.split('_')
        if len(data_parts) < 2:
            logger.error(f"Invalid callback data format: {query.data}")
            await query.answer("Ошибка: неверный формат данных")
            return ConversationHandler.END
            
        action = data_parts[0]
        post_id = '_'.join(data_parts[1:])  # Собираем оставшиеся части обратно в post_id
        
        logger.debug(f"Action: {action}, Post ID: {post_id}")
        
        if action == 'edit':
            context.user_data['editing_post_id'] = post_id
            await query.message.reply_text("Отправьте новую подпись для поста:")
            await query.answer()
            return EDIT_POST
        
        elif action == 'publish':
            logger.info(f"Publishing attempt - User ID: {user_id}, Post ID: {post_id}")
            if user_id not in posts_data:
                logger.error(f"User {user_id} not found in posts_data during publish")
                await query.message.reply_text("Произошла ошибка. Начните сначала с /post")
                return ConversationHandler.END
            
            post_data = posts_data[user_id]
            logger.info(f"Channel ID: {CHANNEL_ID}")
            logger.info(f"Attempting to publish with data: {post_data}")
            
            try:
                # Проверяем права бота в канале
                bot_member = await context.bot.get_chat_member(CHANNEL_ID, context.bot.id)
                logger.info(f"Bot status in channel: {bot_member.status}")
                
                if post_data['media_type'] == PHOTO:
                    await context.bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=post_data['file_id'],
                        caption=post_data.get('caption', ''),
                        reply_markup=get_post_buttons(post_data['post_id'])
                    )
                elif post_data['media_type'] == VIDEO:
                    await context.bot.send_video(
                        chat_id=CHANNEL_ID,
                        video=post_data['file_id'],
                        caption=post_data.get('caption', ''),
                        reply_markup=get_post_buttons(post_data['post_id'])
                    )
                else:
                    await context.bot.send_document(
                        chat_id=CHANNEL_ID,
                        document=post_data['file_id'],
                        caption=post_data.get('caption', ''),
                        reply_markup=get_post_buttons(post_data['post_id'])
                    )
                
                await query.message.reply_text("✅ Пост успешно опубликован в канале!")
                del posts_data[user_id]
                await query.answer()
                return ConversationHandler.END
                
            except Exception as e:
                logger.error(f"Error publishing post: {str(e)}")
                await query.message.reply_text(f"❌ Ошибка при публикации: {str(e)}")
                await query.answer()
                return ConversationHandler.END
        
        # Обработка других типов callback-данных, если необходимо
        # Поскольку кнопка "Чат с рекрутером" теперь использует URL-параметр, 
        # то нам не нужно обрабатывать её тут - Telegram сам откроет URL
        await query.answer()
        
    except Exception as e:
        logger.error(f"Error in button callback: {str(e)}")
        await query.answer("Произошла ошибка")
        return ConversationHandler.END

async def handle_new_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Handling new caption from user {user_id}")
    
    if user_id not in posts_data:
        logger.error(f"User {user_id} not found in posts_data during caption edit")
        await update.message.reply_text("Произошла ошибка. Начните сначала с /post")
        return ConversationHandler.END
    
    posts_data[user_id]['caption'] = update.message.text
    logger.debug(f"Updated post caption: {posts_data[user_id]}")
    return await preview_post(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} cancelled the operation")
    
    if user_id in posts_data:
        del posts_data[user_id]
    
    await update.message.reply_text("Публикация отменена")
    return ConversationHandler.END

def main():
    try:
        # Создаём приложение и передаём токен бота
        application = Application.builder().token("7652918855:AAF8ywxV7GPrd-Ng4Cdsmhv25StkLvxGx2E").build()
        
        # Добавляем задачу загрузки изображения по умолчанию при запуске
        async def start_load_default_image(app):
            await load_default_image(app)
        
        application.post_init = start_load_default_image
        
        # Создаем обработчик разговора с обновленными обработчиками
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('post', start_post)],
            states={
                CHOOSING_MEDIA_TYPE: [
                    CallbackQueryHandler(media_type_callback, pattern='^type_'),
                    CallbackQueryHandler(handle_default_image_choice, pattern='^use_default_image$|^upload_own_image$'),
                    CallbackQueryHandler(start_post, pattern='^back_to_media_type$')  # Добавьте эту строку
                ],
                WAITING_FOR_MEDIA: [
                    MessageHandler(filters.PHOTO, handle_media),
                    MessageHandler(filters.VIDEO, handle_media),
                    MessageHandler(filters.Document.ALL, handle_media)
                ],
                WAITING_FOR_CAPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption),
                    CommandHandler('skip', skip_caption)
                ],
                WAITING_FOR_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url),
                    CommandHandler('skip', skip_url)
                ],
                PREVIEW_POST: [
                    CallbackQueryHandler(button_callback)
                ],
                EDIT_POST: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_caption)
                ],
                WAITING_FOR_NEW_CAPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_caption)
                ]
            },
            fallbacks=[
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(button_callback)
            ]
        )

        # Добавляем обработчик разговора в приложение
        application.add_handler(conv_handler)

        # Добавляем обработчик кнопок для постов в канале
        application.add_handler(CallbackQueryHandler(button_callback))

        # Запускаем бота
        logger.info("Bot started")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        raise e

if __name__ == '__main__':
    main()