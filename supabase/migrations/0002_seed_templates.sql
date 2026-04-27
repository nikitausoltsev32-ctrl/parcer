-- Built-in templates (user_id = null means system template, available to all)

insert into public.templates (user_id, name, template_id, tone, language, custom_instruction) values
    (null, 'Холодное знакомство', 'cold_intro', 'friendly', 'ru',
     'Познакомиться и предложить обсудить, как оффер может помочь получателю.'),
    (null, 'Предложение услуги', 'service_pitch', 'friendly', 'ru',
     'Кратко объясни, какую конкретную задачу ты решаешь, и предложи бесплатный первый шаг.'),
    (null, 'Follow-up', 'followup', 'friendly', 'ru',
     'Напомни о предыдущем письме мягко, не укоряй, предложи созвон на 15 минут.'),
    (null, 'Приглашение на звонок', 'call_invite', 'friendly', 'ru',
     'Попроси 15 минут на короткий созвон на этой неделе, укажи 2 слота.'),
    (null, 'Партнёрство', 'partnership', 'friendly', 'ru',
     'Предложи взаимовыгодное партнёрство по аудитории.');
