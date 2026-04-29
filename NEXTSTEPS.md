# Next Steps — План развития Instantly.ai Clone

## Приоритет 1: Быстрые победы (1-2 часа каждая)

### 1.1 Реальный Resend API Key
- Заменить тестовый `re_test_key` на настоящий ключ
- Верифицировать домен в [Resend Dashboard](https://resend.com/domains)
- Проверить доставку end-to-end (отправка → inbox → reply)
- **Рекомендация:** использовать `onboarding@resend.dev` для первых тестов

### 1.2 CSV File Upload для лидов
- Сейчас bulk import через paste текста в textarea
- Добавить drag & drop загрузку .csv файлов
- Автоматический парсинг заголовков (email, first_name, last_name, company)
- Preview таблицы перед импортом
- **Рекомендация:** использовать `FileReader` API + `papaparse` для парсинга CSV

### 1.3 Редактирование лидов и аккаунтов
- Backend уже поддерживает `PUT /leads/{id}` и `PUT /accounts/{id}`
- Frontend не имеет кнопки Edit — только Add и Delete
- Добавить inline edit или модальное окно редактирования
- **Рекомендация:** модальное окно с предзаполненными полями (проще, чем inline)

### 1.4 Pagination
- Backend поддерживает `skip` и `limit` параметры
- Frontend всегда загружает первую страницу без навигации
- При 100+ лидах или 50+ кампаниях данные обрезаются
- **Рекомендация:** "Load More" кнопка (проще infinite scroll), показывать total count

---

## Приоритет 2: Ключевые фичи (4-8 часов каждая)

### 2.1 Unified Inbox (Unibox) ⭐ РЕКОМЕНДУЕТСЯ ПЕРВЫМ
- Агрегация ответов со всех кампаний в одном окне
- Показать: от кого, тема, preview текста, кампания, дата
- Фильтры: по кампании, по дате, прочитано/непрочитано
- **Почему важно:** killer feature для cold outreach — без неё пользователь теряет ответы
- **Реализация:**
  - Новая страница `/inbox`
  - IMAP polling каждые 2-5 мин (background worker)
  - Или webhook от Resend для real-time
  - Маппинг ответов к лидам по `message_id` / `In-Reply-To` header

### 2.2 Scheduling — Расписание отправки
- Настройка окна отправки: 9:00-18:00 по timezone получателя
- Рабочие дни (Mon-Fri) vs все дни
- Рандомные задержки между письмами (anti-spam)
- **Реализация:**
  - Добавить `send_schedule` JSON поле в Campaign model
  - Background scheduler (cron или APScheduler)
  - Timezone detection по домену лида (опционально)

### 2.3 A/B тестирование
- Два варианта subject/body на кампании
- Автоматический split 50/50 или configurable
- Автовыбор победителя после N отправок (по open rate)
- **Реализация:**
  - Добавить `subject_variant_b` и `body_variant_b` в Campaign
  - Random assignment при отправке
  - Отдельная вкладка в Analytics с A/B сравнением

### 2.4 IMAP мониторинг
- Автоматическое определение ответов через IMAP polling
- Bounce detection (анализ bounce-писем)
- Out-of-office detection (перенос на +3 дня)
- **Реализация:**
  - `aioimaplib` для async IMAP
  - Background worker каждые 2 мин
  - Парсинг `In-Reply-To` и `References` headers для маппинга к lead

### 2.5 Dark Theme
- Instantly.ai использует тёмную тему (`#0f1014` фон, `#2563eb` accent)
- Toggle light/dark в Settings
- **Реализация:**
  - Tailwind `dark:` classes
  - `prefers-color-scheme` media query
  - Zustand store для theme preference

---

## Приоритет 3: Стратегические фичи (1-3 дня каждая)

### 3.1 CRM интеграция
- Автоматический перенос replied-лидов в CRM
- AmoCRM / Bitrix24 для российского рынка
- HubSpot / Pipedrive для международного
- **Реализация:** webhook при смене статуса lead → API call к CRM

### 3.2 Multi-user / Teams
- Несколько пользователей в одном workspace
- Роли: owner (полный доступ) / member (только свои кампании)
- Shared email accounts между участниками
- **Реализация:**
  - Новая модель `Team` + `TeamMember`
  - `team_id` FK на Campaign, EmailAccount
  - Invite flow по email

### 3.3 Lead Database
- Встроенная база контактов с поиском по компании/должности/индустрии
- Импорт из LinkedIn (через расширение)
- Email enrichment (поиск email по имени + компании)
- **Реализация:** отдельный модуль с Apollo.io-подобным интерфейсом

### 3.4 AI Reply Automation
- GPT-4 анализирует входящий ответ
- Классифицирует: interested / not interested / question / out-of-office
- Автоматически генерирует follow-up для "interested" и "question"
- Human approval перед отправкой (HITL)
- **Реализация:**
  - Зависит от Unified Inbox (#2.1)
  - Classification prompt + generation prompt
  - Queue с approve/reject UI

### 3.5 Compliance Checker
- Проверка писем на спам-слова перед отправкой
- Обязательная кнопка unsubscribe в каждом письме
- ФЗ-38 (закон о рекламе) — проверка для российского рынка
- GDPR-compliant unsubscribe flow
- **Реализация:**
  - Словарь спам-слов + regex patterns
  - Pre-send validation hook
  - Auto-inject unsubscribe link

---

## Рекомендуемый порядок реализации

```
Неделя 1:  1.1 (Resend key) → 1.3 (Edit UI) → 1.2 (CSV upload)
Неделя 2:  2.1 (Unified Inbox) ← ЭТО ГЛАВНОЕ
Неделя 3:  2.2 (Scheduling) → 2.4 (IMAP)
Неделя 4:  2.3 (A/B tests) → 2.5 (Dark theme)
Неделя 5+: 3.x (стратегические фичи по приоритету бизнеса)
```

---

## Технический долг

| Задача | Приоритет | Описание |
|--------|-----------|----------|
| Mobile responsive | Средний | Sidebar не коллапсирует, таблицы overflow |
| Token refresh | Средний | Сейчас 24h JWT без refresh — добавить refresh token |
| Rate limiting | Средний | Нет rate limit на login/register (brute force risk) |
| SMTP password encryption | Высокий | Пароли в БД plaintext — нужно AES-256 |
| E2E тесты | Низкий | Только unit тесты, нет Playwright/Cypress |
| Error boundaries | Низкий | React error boundaries для graceful crash handling |
