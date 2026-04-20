Отлично! Адаптирую systemd-конфигурацию под ваш проект **MarketPulse**.

---

# 🤖 Автозапуск MarketPulse через systemd

Полное руководство по настройке автоматического запуска Telegram-бота MarketPulse на базе Aiogram 3.x.

```
📦 Проект: MarketPulse
🐍 Python: 3.8+
🤖 Framework: aiogram 3.x
⚙️ Конфиг: environs + dataclasses
🗄️ БД: SQLite
```

---

## 📋 Содержание
1. [Создание systemd-сервиса](#создание-systemd-сервиса)
2. [Управление сервисом](#управление-сервисом)
3. [Просмотр логов](#просмотр-логов)
4. [Скрипт обновления](#автоматическое-обновление-бота)
5. [Настройка sudo без пароля](#настройка-sudo-без-пароля)
6. [Проблемы и решения](#возможные-проблемы-и-решения)

---

## 🔧 Создание systemd-сервиса

### Шаг 1: Создайте файл сервиса
```bash
sudo nano /etc/systemd/system/marketpulse.service
```

### Шаг 2: Конфигурация для MarketPulse
```ini
[Unit]
Description=MarketPulse — Telegram Trend Tracker Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/MarketPulse
EnvironmentFile=/home/YOUR_USERNAME/MarketPulse/.env
ExecStart=/home/YOUR_USERNAME/MarketPulse/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=marketpulse

# Защита (опционально, для продакшена)
#NoNewPrivileges=true
#PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

> ⚠️ **Замените**:
> - `YOUR_USERNAME` → ваш логин в Linux (`echo $USER`)
> - Пути → актуальные пути к вашему проекту

### 📊 Параметры конфигурации

| Параметр | Описание | Пример для MarketPulse |
|----------|----------|----------------------|
| `Description` | Описание сервиса | `MarketPulse — Trend Tracker` |
| `User` | Пользователь для запуска | `vitali_lukhverchyk` |
| `WorkingDirectory` | Путь к проекту | `/home/user/MarketPulse` |
| `EnvironmentFile` | Файл с переменными | `/home/user/MarketPulse/.env` |
| `ExecStart` | Команда запуска | `python main.py` |
| `Restart` | Политика перезапуска | `always` |
| `RestartSec` | Задержка перед рестартом | `10` |

---

## 🎮 Управление сервисом

### Активация и запуск
```bash
# Перезагрузить конфигурацию systemd
sudo systemctl daemon-reload

# Включить автозапуск при загрузке
sudo systemctl enable marketpulse.service

# Запустить сервис
sudo systemctl start marketpulse.service
```

### Основные команды
```bash
# Проверить статус
sudo systemctl status marketpulse.service

# Остановить
sudo systemctl stop marketpulse.service

# Перезапустить (после обновления кода)
sudo systemctl restart marketpulse.service

# Просмотреть логи в реальном времени
journalctl -u marketpulse.service -f

# Отключить автозапуск
sudo systemctl disable marketpulse.service
```

### 📈 Статусы сервиса
| Статус | Значение |
|--------|----------|
| `active (running)` | ✅ Бот работает |
| `inactive (dead)` | ⏸️ Бот остановлен |
| `failed` | ❌ Ошибка при запуске |
| `activating` | 🔄 Бот запускается |

---

## 📜 Просмотр логов

### Базовые команды
```bash
# Логи в реальном времени
journalctl -u marketpulse.service -f

# Последние 100 строк
journalctl -u marketpulse.service -n 100

# Логи за сегодня
journalctl -u marketpulse.service --since today

# Логи за последний час
journalctl -u marketpulse.service --since "1 hour ago"

# Экспорт логов в файл
journalctl -u marketpulse.service --no-pager > marketpulse.log
```

### 🔍 Фильтрация
```bash
# Только ошибки
journalctl -u marketpulse.service -p err

# Поиск по ключевому слову (например, "YouTube")
journalctl -u marketpulse.service | grep -i "youtube"

# Поиск по уровню логирования
journalctl -u marketpulse.service -p warning..err
```

### 🧹 Очистка старых логов
```bash
# Оставить последние 500 МБ
sudo journalctl --vacuum-size=500M

# Удалить логи старше 7 дней
sudo journalctl --vacuum-time=7d
```

---

## 🔄 Автоматическое обновление бота

### Создайте скрипт обновления
```bash
nano ~/update_marketpulse.sh
```

### Содержимое скрипта
```bash
#!/bin/bash
# Скрипт обновления MarketPulse из Git

set -e  # Выход при ошибке

PROJECT_DIR="$HOME/MarketPulse"
SERVICE_NAME="marketpulse"

echo "=== 🔄 Обновление MarketPulse ==="
echo "🕐 Время: $(date)"
echo "📁 Директория: $PROJECT_DIR"
echo ""

# Переход в директорию проекта
cd "$PROJECT_DIR" || { echo "❌ Директория не найдена"; exit 1; }

# Git pull
echo "📥 Выполняется git pull..."
git pull origin main  # или master, в зависимости от вашей ветки

# Установка зависимостей (если изменился requirements.txt)
echo "📦 Проверка зависимостей..."
if [ -f "requirements.txt" ]; then
    # Для uv:
    uv sync
    # Или для pip + venv:
    # source venv/bin/activate && pip install -r requirements.txt
fi

# Перезапуск сервиса
echo "🔄 Перезапуск сервиса $SERVICE_NAME..."
sudo systemctl restart "$SERVICE_NAME"

# Проверка статуса
echo ""
echo "✅ Статус сервиса:"
sudo systemctl status "$SERVICE_NAME" --no-pager -l

echo ""
echo "=== 🎉 Обновление завершено ==="
```

### Сделайте скрипт исполняемым
```bash
chmod +x ~/update_marketpulse.sh
```

### Использование
```bash
# Обновить бот одной командой
./update_marketpulse.sh
```

---

## 🔐 Настройка sudo без пароля

Чтобы скрипт обновления работал без запроса пароля:

### 1. Откройте sudoers через visudo
```bash
sudo visudo
```

### 2. Добавьте строку в конец файла
```bash
# Замените YOUR_USERNAME на ваш логин
YOUR_USERNAME ALL=(ALL) NOPASSWD: /bin/systemctl restart marketpulse.service, /bin/systemctl status marketpulse.service
```

> ⚠️ **Важно**: Всегда используйте `visudo`, а не прямой редактор — он проверяет синтаксис!

### 3. Проверка
```bash
# Эта команда теперь выполнится без пароля
sudo systemctl restart marketpulse.service
```

---

## 🚨 Возможные проблемы и решения

### ❌ `Permission denied` при чтении `.env`
```
Failed to start marketpulse.service: Permission denied
```
**Решение**:
```bash
# Проверьте права на .env
ls -la ~/MarketPulse/.env

# Установите безопасные права (только владелец)
chmod 600 ~/MarketPulse/.env

# Убедитесь, что пользователь совпадает с директивой User= в сервисе
```

### ❌ `WorkingDirectory doesn't exist`
**Решение**:
```bash
# Проверьте путь
ls -ld /home/YOUR_USERNAME/MarketPulse

# Исправьте WorkingDirectory в файле сервиса, если нужно
sudo nano /etc/systemd/system/marketpulse.service
sudo systemctl daemon-reload
```

### ❌ `ModuleNotFoundError: No module named 'aiogram'`
**Решение**:
```bash
# Убедитесь, что ExecStart использует правильное окружение

# Для uv:
ExecStart=/home/YOUR_USERNAME/.local/bin/uv run python main.py

# Для virtualenv:
ExecStart=/home/YOUR_USERNAME/MarketPulse/venv/bin/python main.py

# Проверьте, что зависимости установлены:
cd ~/MarketPulse
uv sync  # или: source venv/bin/activate && pip install -r requirements.txt
```

### ❌ Бот запускается, но не отвечает на команды
**Возможные причины**:
1. Неверный `BOT_TOKEN` в `.env` → проверьте через `cat .env | grep BOT_TOKEN`
2. Бот не зарегистрирован у @BotFather → создайте нового
3. Ошибка в `main.py` → смотрите логи: `journalctl -u marketpulse.service -n 50`

### ❌ Бот не перезапускается после сбоя
**Решение**: Проверьте параметр `Restart` в сервисе:
```ini
Restart=always          # ✅ Перезапускать всегда (рекомендуется)
Restart=on-failure      # ⚠️ Только при ненулевом коде выхода
Restart=no              # ❌ Не перезапускать
```

---

## 📁 Структура файлов проекта

```
/etc/systemd/system/
└── marketpulse.service          # Файл сервиса systemd

$HOME/
├── MarketPulse/                 # Директория проекта
│   ├── .env                     # Переменные окружения (не в git!)
│   ├── .gitignore
│   ├── requirements.txt
│   ├── config.py
│   ├── main.py                  # Точка входа
│   ├── menu.py
│   ├── db.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── youtube.py
│   └── scheduler.py
│
├── update_marketpulse.sh        # Скрипт обновления (опционально)
└── marketpulse.log              # Экспортированные логи (опционально)
```

---

## 🧰 Дополнительные команды

```bash
# Показать зависимости сервиса
systemctl list-dependencies marketpulse.service

# Временно заблокировать запуск сервиса
sudo systemctl mask marketpulse.service

# Разблокировать
sudo systemctl unmask marketpulse.service

# Список всех запущенных сервисов с "bot" в имени
systemctl list-units --type=service --state=running | grep -i bot

# Протестировать конфигурацию сервиса без запуска
systemd-analyze verify /etc/systemd/system/marketpulse.service
```

---

## 🚀 Чеклист перед первым запуском

- [ ] Создан файл `/etc/systemd/system/marketpulse.service`
- [ ] Заменены `YOUR_USERNAME` и пути на актуальные
- [ ] Файл `.env` существует и содержит `BOT_TOKEN`
- [ ] Зависимости установлены (`uv sync` или `pip install -r requirements.txt`)
- [ ] Права на `.env`: `chmod 600 .env`
- [ ] Выполнено `sudo systemctl daemon-reload`
- [ ] Сервис запущен: `sudo systemctl start marketpulse.service`
- [ ] Статус: `sudo systemctl status marketpulse.service` → `active (running)`

---


