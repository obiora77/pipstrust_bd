# PipsTrust backend implementation notes

## What changed

- Matured investments are settled atomically and become `completed` once they reach their end time/100% progress.
- Dashboard and investment reads also run the settlement check, so an investment cannot stay visually active just because Celery Beat is delayed.
- Investment settlement is idempotent and protected with database row locks to prevent duplicate ROI credits.
- Investment creation now locks and re-checks the wallet balance before deducting funds.
- Deposit approval updates `total_deposited`; starting an investment no longer incorrectly increases that total.
- Withdrawal requests reserve funds immediately, use row locks, validate the configured payout address, support BTC/ETH/USDT TRC-20/USDT ERC-20, and refund safely on cancel/reject.
- If withdrawal OTP delivery fails, the held amount is automatically returned.
- Withdrawal OTP can be resent.
- Admin withdrawal serialization no longer references deleted bank fields.
- Added support-ticket API for users plus admin reply/close endpoints and Django admin registration.
- Added migrations for ERC-20 USDT support and support tickets.
- Added regression tests for investment settlement, withdrawal reservation/refund, ERC-20 payout selection and support tickets.

## Deploy

1. Keep your existing production `.env` file private.
2. Install requirements: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Run Django checks/tests: `python manage.py check` and `python manage.py test`
5. Re-run `python setup_beat.py` so matured investments are checked every minute.
6. Restart Django, Celery worker and Celery Beat.

The API also settles matured investments when the user opens the dashboard or investment list, so the UI does not depend exclusively on Celery.
