from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

AI_CREDIT_COSTS: dict[str, int] = {
    'light_ai_analysis': 1,
    'deep_ai_analysis': 5,
    'premium_ai_analysis': 15,
    'outreach_generation': 3,
    'outreach_regeneration': 3,
    'monitoring_signal': 2,
}


class InsufficientCreditsError(Exception):
    pass


async def check_and_deduct(db: AsyncSession, user_id: str, operation: str) -> int:
    cost = AI_CREDIT_COSTS[operation]
    result = await db.execute(
        text(
            'UPDATE users SET ai_credits_balance = ai_credits_balance - :cost '
            'WHERE id = :uid AND ai_credits_balance >= :cost '
            'RETURNING ai_credits_balance'
        ),
        {'cost': cost, 'uid': str(user_id)},
    )
    row = result.fetchone()
    if row is None:
        raise InsufficientCreditsError(f'Not enough credits for {operation} (cost={cost})')
    return row[0]


async def get_balance(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        text('SELECT ai_credits_balance FROM users WHERE id = :uid'),
        {'uid': str(user_id)},
    )
    row = result.fetchone()
    return row[0] if row else 0
