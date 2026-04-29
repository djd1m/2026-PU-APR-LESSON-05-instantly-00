# Self-Hosted Warmup Pool — Инструкция по настройке

## Концепция

Вместо платного Mailivery ($49+/мес) создаём свой мини-пул из 10 email-аккаунтов, которые обмениваются письмами друг с другом и с прогреваемым аккаунтом. Cron-скрипт автоматизирует отправку, открытие и ответы.

## Шаг 1: Создать 10 seed-аккаунтов

Создай по 3-4 аккаунта на каждом из основных провайдеров:

| # | Провайдер | Email | Пароль приложения |
|---|-----------|-------|-------------------|
| 1 | Gmail | warmup.seed.01@gmail.com | (App Password) |
| 2 | Gmail | warmup.seed.02@gmail.com | (App Password) |
| 3 | Gmail | warmup.seed.03@gmail.com | (App Password) |
| 4 | Outlook | warmup.seed.04@outlook.com | (App Password) |
| 5 | Outlook | warmup.seed.05@outlook.com | (App Password) |
| 6 | Outlook | warmup.seed.06@outlook.com | (App Password) |
| 7 | Yandex | warmup.seed.07@yandex.ru | (App Password) |
| 8 | Yandex | warmup.seed.08@yandex.ru | (App Password) |
| 9 | Mail.ru | warmup.seed.09@mail.ru | (App Password) |
| 10 | Mail.ru | warmup.seed.10@mail.ru | (App Password) |

### Настройка App Password

**Gmail:**
1. Включи 2FA на каждом аккаунте
2. Google Account → Security → App Passwords → создай пароль для "Mail"
3. SMTP: smtp.gmail.com:587, IMAP: imap.gmail.com:993

**Outlook:**
1. Включи 2FA
2. Security → App Passwords → создай
3. SMTP: smtp.office365.com:587, IMAP: outlook.office365.com:993

**Yandex:**
1. Настройки → Безопасность → Пароли приложений
2. SMTP: smtp.yandex.ru:587, IMAP: imap.yandex.ru:993

**Mail.ru:**
1. Настройки → Безопасность → Пароли приложений
2. SMTP: smtp.mail.ru:587, IMAP: imap.mail.ru:993

## Шаг 2: Создать файл конфигурации

Создай `warmup-pool.json` (НЕ коммитить в git!):

```json
{
  "seed_accounts": [
    {
      "email": "warmup.seed.01@gmail.com",
      "password": "xxxx xxxx xxxx xxxx",
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "imap_host": "imap.gmail.com",
      "imap_port": 993
    },
    {
      "email": "warmup.seed.02@gmail.com",
      "password": "xxxx xxxx xxxx xxxx",
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "imap_host": "imap.gmail.com",
      "imap_port": 993
    }
  ]
}
```

## Шаг 3: Установить скрипт

```bash
pip install aiosmtplib aioimaplib
cp warmup_pool_cron.py /opt/warmup/
cp warmup-pool.json /opt/warmup/
chmod 600 /opt/warmup/warmup-pool.json
```

## Шаг 4: Настроить cron

```bash
# Warmup: каждый час с 9 до 18 по МСК (6-15 UTC)
0 6-15 * * * cd /opt/warmup && python3 warmup_pool_cron.py >> /var/log/warmup.log 2>&1
```

## Шаг 5: Мониторинг

```bash
# Проверить логи
tail -f /var/log/warmup.log

# Проверить статус
python3 warmup_pool_cron.py --status
```

## Безопасность

- `warmup-pool.json` содержит пароли → chmod 600, не коммитить в git
- Добавь в `.gitignore`: `warmup-pool.json`
- Для production: шифруй credentials через age/sops
