@echo off
chcp 1251 > nul
title TTM Job Bot - Запуск

color 0A
cls
echo ===================================================
echo              Запуск TTM Job Bot...
echo ===================================================
echo.

REM Проверяем, установлен ли Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo Python не найден. Пожалуйста, установите Python с сайта
    echo https://www.python.org/downloads/
    echo и добавьте его в переменную PATH.
    pause
    exit /b 1
)

REM Проверяем версию Python
echo Проверка версии Python:
python --version
echo.

REM Проверяем существование файла бота
if not exist ttmjobbot_0.2.0.py (
    color 0C
    echo Файл ttmjobbot_0.2.0.py не найден в текущей директории.
    echo Убедитесь, что батник находится в той же папке, что и файл бота.
    pause
    exit /b 1
)

REM Проверяем существование папки для изображений
if not exist images (
    echo Создаем папку для изображений по умолчанию...
    mkdir images
    echo Папка images создана.
)

REM Проверяем наличие изображения по умолчанию
if not exist images\default_image.jpg (
    color 0E
    echo Внимание: Файл default_image.jpg отсутствует в папке images.
    echo Функция использования изображения по умолчанию может не работать.
    color 0A
    echo.
)

REM Более надежная проверка и установка библиотеки python-telegram-bot
echo Проверка библиотеки python-telegram-bot...
python -c "import telegram" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Библиотека telegram не установлена.
    echo Установка python-telegram-bot версии 13.13 (для совместимости)...
    
    REM Обновляем pip для надежности
    python -m pip install --upgrade pip
    
    REM Установка конкретной версии библиотеки
    python -m pip install python-telegram-bot==13.13
    
    if %ERRORLEVEL% NEQ 0 (
        color 0C
        echo Ошибка при установке библиотеки. Проверьте подключение к интернету и права доступа.
        pause
        exit /b 1
    ) else (
        echo Библиотека успешно установлена.
    )
) else (
    echo Библиотека telegram уже установлена.
)

REM Проверяем, что нет других экземпляров бота
echo Проверка запущенных процессов бота...
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /i "python.exe" >nul
if %ERRORLEVEL% EQU 0 (
    color 0E
    echo.
    echo ВНИМАНИЕ: Возможно, уже запущен экземпляр бота.
    echo Если бот не запустится с ошибкой конфликта, закройте все окна Python
    echo и попробуйте снова.
    color 0A
    echo.
    timeout /t 3 >nul
)

echo.
echo ===================================================
echo                Запуск бота...
echo ===================================================
echo.
echo Бот запущен в отдельном окне.
echo.
echo Это окно можно закрыть. Бот продолжит работу в фоне.
echo Для просмотра логов бота смотрите новое окно консоли.
echo.

REM Создаем вспомогательный файл запуска
echo @echo off > run_bot_helper.bat
echo chcp 1251 ^> nul >> run_bot_helper.bat
echo title TTM Job Bot - Работающий бот >> run_bot_helper.bat
echo color 0A >> run_bot_helper.bat
echo cls >> run_bot_helper.bat
echo echo ================================================= >> run_bot_helper.bat
echo echo              TTM Job Bot запущен >> run_bot_helper.bat
echo echo ================================================= >> run_bot_helper.bat
echo echo. >> run_bot_helper.bat
echo echo Для остановки бота нажмите Ctrl+C в этом окне >> run_bot_helper.bat
echo echo. >> run_bot_helper.bat
echo python ttmjobbot_0.2.0.py >> run_bot_helper.bat
echo echo. >> run_bot_helper.bat
echo echo Бот был остановлен. >> run_bot_helper.bat
echo echo Нажмите любую клавишу для выхода... >> run_bot_helper.bat
echo pause ^>nul >> run_bot_helper.bat
echo del run_bot_helper.bat >> run_bot_helper.bat

REM Запускаем вспомогательный файл в новом окне
start run_bot_helper.bat

echo Нажмите любую клавишу для закрытия этого окна...
pause >nul
exit /b