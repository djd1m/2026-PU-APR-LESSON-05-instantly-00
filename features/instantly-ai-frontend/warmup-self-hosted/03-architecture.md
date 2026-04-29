# Self-Hosted Warmup Pool — Архитектура

## Схема работы

```
                    ┌─────────────────────────────────────┐
                    │        WARMUP POOL (10 seeds)        │
                    │                                      │
  Cron (hourly)     │  Gmail ──┐                           │
  9:00-18:00 MSK    │  Gmail ──┤                           │
        │           │  Gmail ──┤    ┌──────────────┐       │
        ▼           │  Outlook─┤───▸│ warmup_pool  │       │
  ┌──────────────┐  │  Outlook─┤    │  _cron.py    │       │
  │ warmup_pool  │  │  Outlook─┤    └──────┬───────┘       │
  │ _cron.py     │  │  Yandex ─┤           │               │
  └──────────────┘  │  Yandex ─┤      sends to             │
                    │  Mail.ru─┤           │               │
                    │  Mail.ru─┘           ▼               │
                    │              ┌──────────────┐        │
                    │              │ TARGET ACCT  │        │
                    │              │send@aicoding │        │
                    │              │   .space     │        │
                    │              └──────────────┘        │
                    └─────────────────────────────────────┘
```

## Цикл прогрева (1 час)

```
1. Загрузить конфиг (seed accounts + target)
2. Определить день рампа → emails_per_seed
3. Для каждого seed аккаунта:
   a. Выбрать N случайных получателей (другие seeds + target)
   b. Сгенерировать уникальную тему + текст
   c. 40% писем — "ответы" (Re: + короткий текст)
   d. Отправить через SMTP
   e. Пауза 2-8 сек между письмами
4. Записать результат в state файл
```

## Рамп-расписание

```
Day  1-3:  1 email/seed/cycle  → 10 total/cycle  → ~80/day (8 cycles)
Day  4-6:  2 emails/seed/cycle → 20 total/cycle  → ~160/day
Day  7-9:  3 emails/seed/cycle → 30 total/cycle  → ~240/day
Day 10-11: 4 emails/seed/cycle → 40 total/cycle  → ~320/day
Day 12-14: 5 emails/seed/cycle → 50 total/cycle  → ~400/day
```

## Файловая структура

```
/opt/warmup/
├── warmup_pool_cron.py        ← Основной скрипт (из этого фолдера)
├── warmup-pool.json           ← Credentials (chmod 600, НЕ в git)
├── warmup-state.json          ← Состояние (автогенерируемый)
└── warmup.log                 ← Логи (через cron redirect)
```

## Сравнение с Mailivery

| Аспект | Self-hosted pool | Mailivery API |
|--------|-----------------|---------------|
| **Стоимость** | $0 (свои аккаунты) | от $49/мо |
| **Размер пула** | 10 аккаунтов | Тысячи peer-аккаунтов |
| **Engagement** | Только отправка | Отправка + открытие + ответ + вытаскивание из спама |
| **Эффективность** | ~70% inbox rate | ~90%+ inbox rate |
| **Настройка** | 2-3 часа | 10 минут |
| **Масштаб** | 1-3 прогреваемых аккаунта | Unlimited |
| **Поддержка** | Самостоятельно | Техподдержка |

## Когда использовать

- **Self-hosted**: для демо, тестирования, бюджетных проектов
- **Mailivery**: для production, когда нужен гарантированный результат
- **Комбинация**: self-hosted для базового прогрева + Mailivery для финального boost
