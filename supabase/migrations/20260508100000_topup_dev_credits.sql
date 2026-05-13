-- Top up all existing users to 10 000 credits for dev/MVP testing.
-- New users get 10 000 by default (model default changed).
UPDATE users SET ai_credits_balance = 10000 WHERE ai_credits_balance < 100;
