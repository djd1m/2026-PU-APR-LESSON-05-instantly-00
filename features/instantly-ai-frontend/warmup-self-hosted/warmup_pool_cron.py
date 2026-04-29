#!/usr/bin/env python3
"""
Self-hosted warmup pool — cron script.

Sends warmup emails between seed accounts and the target account,
simulating real engagement (send → open → reply).

Usage:
    python3 warmup_pool_cron.py              # Run warmup cycle
    python3 warmup_pool_cron.py --status     # Show pool status
    python3 warmup_pool_cron.py --test       # Send one test email

Cron (every hour 9-18 MSK):
    0 6-15 * * * cd /opt/warmup && python3 warmup_pool_cron.py >> /var/log/warmup.log 2>&1
"""
import asyncio
import json
import logging
import random
import sys
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("warmup-pool")

CONFIG_FILE = Path(__file__).parent / "warmup-pool.json"
STATE_FILE = Path(__file__).parent / "warmup-state.json"

# --- Email content pool ---

SUBJECTS = [
    "Встреча в четверг — подтверждение",
    "Re: Коммерческое предложение",
    "Документы к подписанию",
    "Вопрос по срокам поставки",
    "Обновление по проекту",
    "Quick follow-up from our call",
    "Partnership opportunity — initial thoughts",
    "Q2 planning — your input needed",
    "Отчёт готов к ревью",
    "Team lunch Friday?",
    "Updated deck attached",
    "Can you review this before EOD?",
    "Рекомендация — книга по управлению",
    "Конференция в мае — идёшь?",
    "Great article — thought of you",
    "Coffee next week?",
    "Deploy scheduled for tonight",
    "Sprint retrospective notes",
    "Code review request",
    "Networking event next month",
]

BODIES = [
    "Привет!\n\nОтправляю как договаривались. Посмотри когда будет время.\n\nС уважением",
    "Hi!\n\nJust wanted to follow up on our conversation. Let me know your thoughts.\n\nBest",
    "Добрый день!\n\nПодскажите статус по нашему вопросу. Буду ждать ответа.\n\nСпасибо",
    "Hey,\n\nSharing this link I mentioned earlier. Hope you find it useful!\n\nCheers",
    "Привет!\n\nДавно не общались. Как дела с проектом? Может пересечёмся на неделе?",
    "Hello!\n\nThanks for getting back to me so quickly. I've reviewed everything and it looks good.\n\nBest regards",
    "Добрый день!\n\nСпасибо за оперативный ответ. Всё выглядит отлично, можем двигаться дальше.",
    "Hi there!\n\nI appreciate your help with this. Let me know if you need anything else from my side.",
]

REPLY_BODIES = [
    "Спасибо, получил! Посмотрю сегодня.",
    "Thanks, got it! Will review shortly.",
    "Отлично, принято. Вернусь с ответом до конца дня.",
    "Great, thanks for sending this over!",
    "Получил, спасибо! Всё выглядит хорошо.",
    "Sounds good, let's discuss tomorrow.",
    "Ок, договорились!",
    "Perfect, I'll take a look and get back to you.",
]

RANDOM_PHRASES = [
    f"Ref: {uuid.uuid4().hex[:8]}",
    f"Sent at {datetime.now().strftime('%H:%M')}",
    "Hope you're having a great day!",
    "Надеюсь, у тебя всё хорошо!",
    f"ID-{random.randint(1000, 9999)}",
]


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        logger.error("Config not found: %s", CONFIG_FILE)
        logger.error("Copy warmup-pool.json.example and fill in credentials")
        sys.exit(1)
    return json.loads(CONFIG_FILE.read_text())


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"day": 0, "total_sent": 0, "total_replied": 0, "history": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# Ramp schedule: day → emails per seed account per cycle
RAMP = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 3, 8: 3, 9: 3, 10: 4, 11: 4, 12: 5, 13: 5, 14: 5}


def get_emails_per_seed(day: int) -> int:
    return RAMP.get(day, 5)


async def send_email(
    sender: dict, to_email: str, subject: str, body: str
) -> bool:
    """Send one email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender["email"]
    msg["To"] = to_email
    msg["Message-ID"] = f"<{uuid.uuid4()}@warmup-pool>"

    # Add random phrase for uniqueness
    body_with_sig = f"{body}\n\n{random.choice(RANDOM_PHRASES)}"
    msg.attach(MIMEText(body_with_sig, "plain"))
    msg.attach(MIMEText(f"<html><body><p>{body_with_sig}</p></body></html>", "html"))

    try:
        async with aiosmtplib.SMTP(
            hostname=sender["smtp_host"],
            port=sender["smtp_port"],
            use_tls=sender["smtp_port"] == 465,
            start_tls=sender["smtp_port"] == 587,
            timeout=30,
        ) as smtp:
            await smtp.login(sender["email"], sender["password"])
            await smtp.send_message(msg)
        logger.info("SENT: %s → %s [%s]", sender["email"], to_email, subject[:40])
        return True
    except Exception as e:
        logger.error("FAIL: %s → %s: %s", sender["email"], to_email, e)
        return False


async def run_warmup_cycle(config: dict, state: dict):
    """Run one warmup cycle: each seed sends to other seeds + target."""
    seeds = config["seed_accounts"]
    target = config.get("target_account")  # Optional: the account being warmed up

    state["day"] = state.get("day", 0) + 1
    day = state["day"]
    emails_per_seed = get_emails_per_seed(day)

    logger.info("=== Warmup Day %d — %d emails per seed ===", day, emails_per_seed)

    sent = 0
    failed = 0

    for sender in seeds:
        # Pick random recipients from other seeds + target
        recipients = [s["email"] for s in seeds if s["email"] != sender["email"]]
        if target:
            recipients.append(target["email"])
        random.shuffle(recipients)
        recipients = recipients[:emails_per_seed]

        for recipient in recipients:
            subject = random.choice(SUBJECTS)
            body = random.choice(BODIES)

            # 40% chance this is a "reply" (starts with Re:)
            if random.random() < 0.4:
                subject = f"Re: {subject}"
                body = random.choice(REPLY_BODIES)

            success = await send_email(sender, recipient, subject, body)
            if success:
                sent += 1
            else:
                failed += 1

            # Random delay 2-8 seconds between sends (anti-spam)
            await asyncio.sleep(random.uniform(2, 8))

    # Update state
    state["total_sent"] = state.get("total_sent", 0) + sent
    state["total_replied"] = state.get("total_replied", 0)
    state["history"].append({
        "day": day,
        "date": datetime.now().isoformat(),
        "sent": sent,
        "failed": failed,
        "emails_per_seed": emails_per_seed,
    })

    # Keep last 30 days of history
    state["history"] = state["history"][-30:]
    save_state(state)

    logger.info(
        "=== Day %d complete: sent=%d failed=%d total=%d ===",
        day, sent, failed, state["total_sent"],
    )


def show_status(state: dict, config: dict):
    seeds = config["seed_accounts"]
    print(f"\n{'='*50}")
    print(f"  Warmup Pool Status")
    print(f"{'='*50}")
    print(f"  Seed accounts: {len(seeds)}")
    print(f"  Current day:   {state.get('day', 0)}")
    print(f"  Total sent:    {state.get('total_sent', 0)}")
    print(f"  Emails/seed:   {get_emails_per_seed(state.get('day', 0) + 1)}")
    print(f"\n  Last 5 days:")
    for h in state.get("history", [])[-5:]:
        print(f"    Day {h['day']}: sent={h['sent']} failed={h['failed']} ({h.get('date', '?')[:10]})")
    print(f"{'='*50}\n")


async def test_send(config: dict):
    """Send a single test email from first seed to second."""
    seeds = config["seed_accounts"]
    if len(seeds) < 2:
        print("Need at least 2 seed accounts for test")
        return
    success = await send_email(
        seeds[0], seeds[1]["email"], "Warmup test email", "This is a test from the warmup pool."
    )
    print(f"Test send: {'SUCCESS' if success else 'FAILED'}")


def main():
    config = load_config()
    state = load_state()

    if "--status" in sys.argv:
        show_status(state, config)
        return

    if "--test" in sys.argv:
        asyncio.run(test_send(config))
        return

    asyncio.run(run_warmup_cycle(config, state))


if __name__ == "__main__":
    main()
