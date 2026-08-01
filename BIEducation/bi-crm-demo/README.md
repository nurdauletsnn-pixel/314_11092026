# 🎓 BI Education CRM

<p align="center">
  <b>Централизованная CRM-система для управления продажами, воронками поступления и лидогенерацией</b>
  <br/>
  Школы Riviera / Quantum / BINOM · Детские сады ALDI BI · B2B-направления
</p>

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2%2B-092E20?logo=django&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-06B6D4?logo=tailwindcss&logoColor=white)
![DRF](https://img.shields.io/badge/Django%20REST%20Framework-3.14%2B-red)

---

## 📌 Что это за продукт?

**BI Education CRM** — единая платформа для команд продаж образовательного холдинга. Система оцифровывает весь путь лида от первой заявки до зачисления:

- 🏫 **B2C School** — частные школы (Riviera, Quantum STEM/TECH);
- 🧸 **B2C Kindergarten** — детские сады (ALDI BI Capital Park, GreenLine.Aqua, Flagman);
- 🏢 **B2B Partnership** — франчайзинг, строительство, доверительное управление, консалтинг;
- 🆓 **Free Schools (BINOM)** — бесплатные школы с лидогенерацией через государственные программы.

CRM решает задачи: **управление воронкой продаж, расчёт тарифов и графиков платежей, анти-дубликаты, гео-роутинг, квоты и листы ожидания, ролевой доступ и сквозная аналитика**.

---

## 🎯 Ключевой Функционал (Key Features)

| Модуль | Описание |
|--------|----------|
| 📊 **Мульти-воронки** | Раздельные конфигурации стадий и полей для B2C School, B2C Kindergarten и B2B. Тип анкеты зависит от выбранной вкладки. |
| 🎯 **Канбан-доска (Drag-and-Drop)** | Карточки сделок перетаскиваются между колонками. Оптимистичное обновление UI + `PATCH /api/deals/{id}/` с системными slug стадий (`entrance_fee`, `enrolled`, ...). Метрики **Visible deals / Closed / won / Waitlisted / Projected** пересчитываются мгновенно. |
| ⚡ **Симулятор Лидов** | Встроенный генератор тестовых сделок: **Стандартный лид**, **Кросс-филиальный** (гео-роутинг), **Переполнение и Waitlist**, **Дубликат контакта** (анти-дубль). |
| 📈 **HQ Analytics** | Прогноз выручки (Forecast Revenue), статистика по филиалам, выявление узких мест Листа ожидания (Waitlist Bottleneck). |
| 🔐 **Ролевая модель (RBAC)** | `HQ_ADMIN` — все филиалы; `BRANCH_DIRECTOR` — управление филиалом; `SALES_MANAGER` — сделки и контакты своего филиала. Защита на бэкенде (`has_object_permission` + явная проверка в PATCH). |
| 🧮 **Тарифный калькулятор** | Расчёт стоимости обучения, вступительных взносов, питания/развозки, скидки 10% на 2-го ребёнка (ALDI BI) и авто-генерация графика платежей. |
| 🔁 **Анти-дубль** | Поиск контакта по телефону/ИИН по всей БД, плашка «Контакт найден в филиале X», привязка к существующей записи. |
| 🌍 **Гео-роутинг** | Лид из другого города автоматически направляется в нужный филиал с пометкой `is_cross_branch`. |

---

## 🧰 Технологический Стек (Tech Stack)

### Backend
| Технология | Версия |
|------------|--------|
| Python | 3.9+ |
| Django | 4.2.x |
| Django REST Framework | 3.14+ |
| psycopg (PostgreSQL) | 3.x |
| django-cors-headers | 4.x |
| SQLite (dev-режим, `USE_SQLITE=True`) | встроенная |

### Frontend
| Технология | Версия |
|------------|--------|
| React | 19.x |
| TypeScript | 6.0 |
| Vite | 8.x |
| Zustand (state management) | 5.x |
| TailwindCSS | 4.x |
| lucide-react (иконки) | 1.x |
| axios | 1.x |
| react-hot-toast | 2.x |

---

## 🚀 Быстрый запуск (Quick Start Guide)

> Инструкция для macOS / Linux / Windows. Требуются: **Python 3.9+**, **Node.js 18+**, **npm**.

### Шаг 1. Клонирование репозитория

```bash
git clone <your-repo-url> bi-crm-demo
cd bi-crm-demo
```

### Шаг 2. Запуск Backend (Django)

```bash
cd backend

# 2.1 Создание и активация виртуального окружения
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate        # Windows

# 2.2 Установка зависимостей
pip install -r requirements.txt

# 2.3 Применение миграций (SQLite — без отдельной настройки PostgreSQL)
USE_SQLITE=True python manage.py migrate

# 2.4 Создание тестовых пользователей (RBAC)
USE_SQLITE=True python manage.py seed_users

# 2.5 Заполнение демо-данными (сделки, филиалы, тарифы, квоты)
USE_SQLITE=True python manage.py generate_mock_data --force

# 2.6 Запуск сервера
USE_SQLITE=True python manage.py runserver
```

ℹ️ **API будет доступен по адресу:** `http://localhost:8000/api/`

### Шаг 3. Запуск Frontend (React + Vite)

```bash
cd ../frontend

# 3.1 Установка зависимостей
npm install

# 3.2 Запуск dev-сервера
npm run dev
```

ℹ️ **Frontend откроется по адресу:** `http://localhost:5173` — уже настроен CORS, запросы к бэкенду идут на `http://localhost:8000/api/` автоматически.

### Шаг 4. 🎉 Готово

Откройте браузер на `http://localhost:5173` и войдите под учётной записью из раздела ниже.

---

## 🔑 Данные для Входа (Default Credentials)

Пароль для **всех** тестовых пользователей: **`administrator`**

| Логин | Роль | Филиал |
|-------|------|--------|
| `hq_admin` | HQ_ADMIN (все филиалы) | — (глобально) |
| `director_riviera` | BRANCH_DIRECTOR | Riviera International School |
| `manager_riviera` | SALES_MANAGER | Riviera International School |
| `director_quantum` | BRANCH_DIRECTOR | Quantum STEM School |
| `manager_quantum` | SALES_MANAGER | Quantum STEM School |
| `director_aldi` | BRANCH_DIRECTOR | ALDI BI Capital Park |
| `manager_aldi` | SALES_MANAGER | ALDI BI Capital Park |

---

## 🗂 Структура Проекта (Project Structure)

```
bi-crm-demo/
├── backend/                      # Django REST Framework backend
│   ├── manage.py                 # Точка входа Django
│   ├── requirements.txt          # Зависимости Python
│   ├── bi_crm_demo/              # Конфигурация проекта
│   │   ├── settings.py           # Настройки (SQLite/PostgreSQL, CORS, DRF)
│   │   └── urls.py               # Маршруты API
│   └── crm/                      # Основное CRM-приложение
│       ├── models.py             # Deal, Contact, Child, Partner, Branch, Stage...
│       ├── views.py              # DRF ViewSets + бизнес-эндпоинты
│       ├── serializers.py        # DRF-сериализаторы
│       ├── business_logic.py     # Расчёт тарифов и расписаний
│       ├── permissions.py        # RBAC-права
│       ├── services/             # Движок тарифов, автоматизация
│       └── management/commands/
│           ├── seed_users.py             # Тестовые пользователи
│           ├── generate_mock_data.py     # Демо-данные
│           └── check_payment_deadlines.py
│
├── frontend/                     # React + TypeScript frontend
│   ├── package.json              # Скрипты и зависимости
│   ├── vite.config.ts            # Настройки Vite (прокси/CORS)
│   └── src/
│       ├── components/           # UI-компоненты
│       │   ├── KanbanBoard.tsx   # Канбан-доска с Drag-and-Drop
│       │   ├── DealCard.tsx      # Карточка сделки (B2C/B2B)
│       │   ├── DealModal.tsx     # Анкета создания/редактирования
│       │   ├── LeadSimulatorModal.tsx  # Симулятор лидов
│       │   ├── AnalyticsWidget.tsx     # Сквозная аналитика
│       │   └── ...               # Dashboard, виджеты, логин
│       ├── store/                # Zustand state management (auth)
│       ├── services/             # API-слои (dealAdapter, accessControl, ...)
│       ├── types/                # TypeScript-интерфейсы (Deal, Branch, ...)
│       ├── lib/                  # Утилиты расчёта (pricing, totalDeal)
│       └── data/                 # Mock-данные для разработки
│
└── README.md                     # Этот документ
```

---

## ♻️ Дополнительные сценарии и эндпоинты

| Эндпоинт | Метод | Назначение |
|----------|-------|------------|
| `/api/auth/login/` | POST | Получение токена (логин, пароль) |
| `/api/deals/` | GET/POST | Список / создание сделок |
| `/api/deals/{id}/` | PATCH | Обновление стадии/статуса (Drag-and-Drop) |
| `/api/deals/simulate-lead/` | POST | Симулятор лидов (4 сценария) |
| `/api/deals/metadata/` | GET | Справочники филиалов и тарифов |
| `/api/tariffs/calculate/` | GET | Калькулятор тарифа |
| `/api/contacts/check-duplicate/` | GET | Анти-дубль по телефону/ИИН |
| `/api/payment-schedules/{id}/mark-paid/` | POST | Отметить платёж оплаченным |
| `/api/deals/{id}/select-tariff/` | POST | Выбор тарифа + генерация графика платежей |

---

## ✨ Live Demo

> Ссылка появится после деплоя (см. ниже).

- 🌐 **Frontend (Vercel):** `https://<ваш-проект>.vercel.app`
- 🔌 **Backend API (Render):** `https://<ваш-сервис>.onrender.com/api/`

---

## 🚀 Деплой (Production)

Проект — **monorepo**: `frontend/` (React + Vite) и `backend/` (Django + DRF). Рекомендуемая схема:

```
Браузер
   │
   ▼
https://<ваш-проект>.vercel.app     ← Frontend: Vercel (бесплатно)
   │  https://<ваш-сервис>.onrender.com/api/
   ▼
Django (Render.com)  →  PostgreSQL (Render.com)
```

### Frontend → Vercel

1. Залейте репозиторий на GitHub (см. раздел «Загрузка на GitHub» ниже).
2. На [vercel.com](https://vercel.com) → **Add New → Project** → выберите ваш репозиторий.
3. Настройки проекта:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite (определится автоматически)
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. **Environment Variables** (Settings → Environment Variables):
   ```
   VITE_API_URL=https://<ваш-сервис>.onrender.com/api/
   ```
   ⚠️ Без этой переменной фронтенд будет стучаться на `http://localhost:8000/api/` — в продакшене работать не будет.
5. Deploy.

Локальные `.env`-файлы (для разработки):
- `frontend/.env` — `VITE_API_URL=http://localhost:8000/api/`
- Примеры: `.env.example`, `.env.production.example` (коммитятся в git).

### Backend + PostgreSQL → Render.com

1. На [render.com](https://render.com) создайте:
   - **PostgreSQL** (бесплатный план) → скопируйте параметры подключения.
   - **Web Service** → подключите тот же GitHub-репозиторий.
2. Настройки Web Service:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:**
     ```
     python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_users && python manage.py generate_mock_data --force && gunicorn bi_crm_demo.wsgi:application
     ```
3. **Environment Variables:**
   | Переменная | Значение |
   |------------|----------|
   | `USE_SQLITE` | `False` |
   | `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | из панели Render PostgreSQL |
   | `DJANGO_SECRET_KEY` | случайная строка (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | `<ваш-сервис>.onrender.com`, `<ваш-проект>.vercel.app` |
   | `CORS_ALLOWED_ORIGINS` | `https://<ваш-проект>.vercel.app` |

   > `CORS_ALLOW_ALL_ORIGINS = True` в `settings.py` уже разрешает все источники — для демо достаточно, для продакшена замените на `CORS_ALLOWED_ORIGINS`.

4. Deploy. Готово — backend доступен на `https://<ваш-сервис>.onrender.com/api/`.

⚠️ **Бесплатный тариф Render** «засыпает» через ~15 минут без трафика — первый запрос после простоя может занять 30–60 сек (cold start). Для презентации перезайдите на сайт заранее.

### Загрузка на GitHub

```bash
cd bi-crm-demo

git init
git add README.md docker-compose.yml backend/ frontend/
git status          # убедитесь: НЕТ .venv/, node_modules/, *.sqlite3, .env
git commit -m "init: BI Education CRM demo"
git branch -M main

# Создайте репозиторий на github.com и скопируйте SSH-URL
git remote add origin git@github.com:<ваш-логин>/bi-education-crm.git
git push -u origin main
```

> `.env`-файлы (реальные секреты) не коммитятся — они в `.gitignore`. Коммитятся только примеры `.env.example` и `.env.production.example`.

---

## 🏗 Сборка и Проверка (Production Build)

### Frontend — проверка типов и production-сборка

```bash
cd frontend
npm run build        # tsc -b && vite build  → проверка TS + сборка в dist/
```

### Backend — проверка конфигурации

```bash
cd backend
USE_SQLITE=True python manage.py check
```

### Запуск тестов

```bash
cd backend
USE_SQLITE=True python manage.py test crm     # 25 тестов: модели, API, симулятор, RBAC
```

---

## 📎 Лицензия

Проект предназначен для внутреннего демо и тестирования. Требования и спецификация продукта: `BI_Education_CRM_MasterSpec (1).md`.