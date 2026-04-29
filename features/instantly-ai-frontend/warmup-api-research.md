# Email Warmup API — Исследование провайдеров

**Дата:** 2026-04-29
**Контекст:** Выбор warmup-сервиса для интеграции в Instantly.ai clone

---

## Зачем нужен warmup

Email warmup — это процесс постепенного наращивания отправки с нового email-аккаунта через **peer network** (пул аккаунтов, которые обмениваются письмами, открывают их, отвечают, вытаскивают из спама). Это создаёт положительные сигналы для Gmail/Yandex/Outlook и повышает inbox placement rate.

Без warmup: новый аккаунт отправляет 50 cold emails → большинство уходит в спам → reputation damage.
С warmup: 14-21 день рампа 5→50 emails/day → inbox rate 85%+ → можно запускать кампании.

---

## Сравнение провайдеров

### 1. Mailivery (РЕКОМЕНДАЦИЯ)

| Параметр | Значение |
|----------|----------|
| **Модель ценообразования** | Пул объёма (shared volume), unlimited mailboxes |
| **Цены** | Starter $49/мо (200 warmup/день), Business $199/мо (2500/день) |
| **API** | REST, `https://app.mailivery.io/api/v1`, Bearer token auth |
| **Rate limit** | 240 req/min |
| **Провайдеры** | SMTP, Gmail, Microsoft 365, SendGrid |
| **Документация** | https://mailivery.readme.io/reference/mailivery-api-introduction |

**API Endpoints:**
- `POST` Connect Mailbox (SMTP / Google / Microsoft / SendGrid)
- `PATCH /startwarmup` — Start warmup
- `PATCH /pausewarmup` — Pause warmup
- `PATCH /resumewarmup` — Resume warmup
- `PATCH /updateemailperday` — Update daily volume
- `PATCH /enablerampup` / `PATCH /disablerampup` — Ramp-up control
- `PATCH /getmetrics` — Get warmup metrics
- `PATCH /gethealthscore` — Get health score
- `PATCH /getactivitylog` — Get activity logs
- `GET /allcampaigns` — List all mailboxes
- `GET /fetchcampaign` — Get mailbox details
- `GET /getaccountlimits` — Account limits

**Плюсы:**
- Flat price за пул, не за inbox — экономично при 5+ аккаунтах
- Хорошо документированный API
- Поддержка webhooks (connect/disconnect, warmup events)
- Ramp-up scheduling из коробки

**Минусы:**
- API доступ требует связаться с sales
- Нет публичных code examples

---

### 2. Warmup Inbox

| Параметр | Значение |
|----------|----------|
| **Модель** | Per inbox |
| **Цены** | Basic $19/мо, Pro $59/мо, Max $99/мо ($79 annual) — **за каждый ящик** |
| **API** | Только на Max плане ($79+/мо за inbox) |
| **Документация** | https://api.warmupinbox.com/api-doc (Swagger) |

**Плюсы:**
- Простой интерфейс
- До 1000 warmup messages/day на Max

**Минусы:**
- Дорого при масштабировании: 10 ящиков = $790/мо
- API только на самом дорогом плане
- Per-inbox модель не подходит для платформы

---

### 3. EmailWarmup.com

| Параметр | Значение |
|----------|----------|
| **Модель** | Flat price, unlimited mailboxes |
| **API** | REST, API key auth |
| **Провайдеры** | Google Workspace, M365, Zoho, SendGrid, Mailgun, SES, custom SMTP |

**Плюсы:**
- Unlimited mailboxes за flat price
- Поддержка Zapier/Make + Webhooks
- Множество ESP

**Минусы:**
- Цены не публичны (нужно связаться)
- Документация доступна только после регистрации

---

### 4. Instantly.ai (оригинал)

| Параметр | Значение |
|----------|----------|
| **Модель** | Per account |
| **Цены** | Growth $30-47/мо (unlimited accounts + warmup included) |
| **API** | Included on Growth plan |

**Плюсы:**
- Warmup включён в стоимость подписки
- Огромный peer network (200K+ аккаунтов)
- API доступен

**Минусы:**
- Это конкурент, а не сервис для интеграции
- Нет отдельного warmup API для сторонних платформ

---

## Архитектура интеграции

### Текущее состояние нашего проекта

```
EmailAccount
├── warmup_enabled (bool)
├── warmup_status (new → warming → ready → paused)
├── warmup_score (0-100)
├── warmup_day (int)
├── warmup_daily_target (5→50 progressive)
├── warmup_sent_today (int)
└── warmup_max_per_day (int)

WarmupLog
├── day_number, emails_sent, bounces
├── inbox_rate, score_after
└── status

API Endpoints (уже реализованы):
├── POST /accounts/:id/warmup/start
├── POST /accounts/:id/warmup/pause
├── POST /accounts/:id/warmup/advance (demo)
└── GET  /accounts/:id/warmup/status

Frontend:
└── Warmup panel на карточке аккаунта (status badge, day/score bars, start/pause/advance buttons)
```

### План интеграции с Mailivery

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  Frontend   │───▸│  Our Backend │───▸│  Mailivery  │
│  (React)    │◂───│  (FastAPI)   │◂───│  API        │
└─────────────┘    └──────────────┘    └─────────────┘

Flow:
1. User adds email account → POST /accounts (наш API)
2. Backend → POST Mailivery API (connect mailbox with SMTP credentials)
3. User clicks "Start Warmup" → POST /accounts/:id/warmup/start
4. Backend → PATCH /startwarmup (Mailivery API)
5. Cron/worker polls PATCH /getmetrics + /gethealthscore
6. Backend updates warmup_score, warmup_day, warmup_status
7. Frontend shows real-time warmup progress
```

### Необходимые изменения для интеграции

| Компонент | Изменение |
|-----------|-----------|
| `config.py` | Добавить `MAILIVERY_API_KEY` env var |
| `services/warmup.py` | Добавить `MailiveryClient` class для API calls |
| `services/warmup.py` | `start_warmup()` → вызывает Mailivery `/startwarmup` |
| `services/warmup.py` | `pause_warmup()` → вызывает Mailivery `/pausewarmup` |
| `services/warmup.py` | Новый метод `sync_metrics()` → pulls metrics from Mailivery |
| `EmailAccount` model | Добавить `mailivery_campaign_id` для маппинга |
| Background worker | Cron job каждые 30 мин: sync metrics для всех warming аккаунтов |
| Frontend | Без изменений — текущий UI уже показывает score/day/status |

### Fallback стратегия

Если `MAILIVERY_API_KEY` не задан → warmup работает в "demo mode" (текущая реализация: локальный state machine без реальной peer network). Это позволяет демонстрировать функционал без подписки.

---

## Рекомендация

**Mailivery** — лучший выбор для интеграции:
1. **Экономика**: $49/мо за 200 warmup/день с unlimited mailboxes (vs $79/inbox у Warmup Inbox)
2. **API**: Хорошо документирован, REST, Bearer auth
3. **Модель**: Shared volume pool идеально подходит для платформы
4. **Интеграция**: ~1 день разработки (добавить HTTP client + sync worker)

Для MVP/демо — текущая локальная реализация достаточна.
Для production — подключить Mailivery API.

---

## Источники

- [Mailivery API Documentation](https://mailivery.readme.io/reference/mailivery-api-introduction)
- [Warmup Inbox API Docs](https://api.warmupinbox.com/api-doc)
- [EmailWarmup.com API](https://emailwarmup.com/email-warmup-api)
- [Best Email Warm-Up APIs in 2026 (Pricing Compared)](https://prospeo.io/s/email-warm-up-api)
- [Warmup Inbox Pricing 2026](https://coldemailkit.com/tools/warmup-inbox)
- [ColdMail.ru Warmup Architecture](https://github.com/djd1m/2026-PU-APR-LESSON-05-instanly-01/tree/main/docs)
