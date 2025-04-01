@echo off
echo Starting TTM Job Bot...
echo.

REM Проверяем, установлен ли Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python не найден. Пожалуйста, установите Python с сайта https://www.python.org/downloads/
    echo и добавьте его в переменную PATH.
    pause
    exit /b 1
)

REM Проверяем существование файла бота
if not exist ttmjobbot_0.2.0.py (
    echo Файл ttmjobbot_0.2.0.py не найден в текущей директории.
    echo Убедитесь, что батник находится в той же папке, что и файл бота.
    pause
    exit /b 1
)

REM Проверяем существование папки для изображений
if not exist images (
    echo Создаем папку для изображений по умолчанию...
    mkdir images
)

REM Проверяем наличие изображения по умолчанию
if not exist images\default_image.jpg (
    echo Внимание: Файл default_image.jpg отсутствует в папке images.
    echo Функция использования изображения по умолчанию может не работать.
    echo.
)

REM Проверяем наличие необходимых библиотек
echo Проверка необходимых библиотек...
python -c "import telegram" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Установка python-telegram-bot...
    pip install python-telegram-bot
)

echo.
echo Запуск бота...
echo Для остановки бота нажмите Ctrl+C
echo.

REM Запускаем бота
python ttmjobbot_0.2.0.py

REM Если бот завершился с ошибкой, удерживаем окно открытым
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Бот завершил работу с ошибкой (код %ERRORLEVEL%).
    pause
)

exit /b