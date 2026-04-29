# Warmup Email Templates — Темы и тексты

## Принцип

Warmup-письма должны выглядеть как **реальная деловая переписка**, а не шаблонные рассылки. Почтовые провайдеры анализируют контент — однообразные письма получают низкий score.

## Пул тем (50 тем, ротируются случайно)

### Бизнес

1. "Встреча в четверг — подтверждение"
2. "Re: Коммерческое предложение"
3. "Документы к подписанию"
4. "Вопрос по срокам поставки"
5. "Обновление по проекту — неделя 12"
6. "Счёт №{random_num} — просьба подтвердить"
7. "Agenda for tomorrow's sync"
8. "Quick follow-up from our call"
9. "Partnership opportunity — initial thoughts"
10. "Q2 planning — your input needed"

### Рабочие

11. "Отчёт за {month} — готов к ревью"
12. "Новый сотрудник в команде"
13. "Изменение в расписании"
14. "Re: Отпуск на следующей неделе"
15. "Доступы к новому сервису"
16. "Team lunch Friday?"
17. "Updated deck attached"
18. "Can you review this before EOD?"
19. "Office policy update"
20. "Parking pass renewal"

### Нейтральные

21. "Рекомендация — книга по управлению"
22. "Конференция в мае — идёшь?"
23. "Ссылка которую обещал"
24. "Фото с мероприятия"
25. "Happy birthday!"
26. "Great article — thought of you"
27. "Coffee next week?"
28. "Travel plans for the summit"
29. "Recipe you asked about"
30. "Weekend plans?"

### Tech

31. "Deploy scheduled for tonight"
32. "Bug fix merged — please verify"
33. "New API keys generated"
34. "Server migration update"
35. "Sprint retrospective notes"
36. "Code review request"
37. "CI/CD pipeline fixed"
38. "Database backup completed"
39. "SSL cert renewal reminder"
40. "New staging environment ready"

### Misc

41. "Re: Контакт дизайнера"
42. "Бронь ресторана на пятницу"
43. "Результаты опроса"
44. "Приглашение на вебинар"
45. "Новости индустрии — дайджест"
46. "Networking event next month"
47. "Subscription renewal notice"
48. "Feedback on the presentation"
49. "Holiday schedule"
50. "Moving to new office — details"

## Пул текстов (шаблоны с вариативностью)

Каждый текст содержит `{name}` и `{random_phrase}` для уникальности:

```python
BODY_TEMPLATES = [
    "Привет!\n\nОтправляю как договаривались. Посмотри когда будет время.\n\nС уважением",
    "Hi {name},\n\nJust wanted to follow up on our conversation. Let me know your thoughts.\n\nBest",
    "Добрый день!\n\nПодскажите, пожалуйста, статус по нашему вопросу. Буду ждать ответа.\n\nСпасибо",
    "Hey,\n\nSharing this link I mentioned earlier. Hope you find it useful!\n\nCheers",
    "{name}, привет!\n\nДавно не общались. Как дела с проектом? Может пересечёмся на неделе?\n\nВсего доброго",
]
```

## Правила ротации

1. Каждое письмо использует случайную тему из пула
2. Тело письма выбирается случайно + добавляется случайная фраза
3. Один seed-аккаунт не отправляет одну и ту же тему дважды за день
4. Соотношение EN/RU тем соответствует целевому рынку
